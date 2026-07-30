"""
Parallel Tempering Sampler for K3×T² MCMC (IMP-02)
====================================================
Extends the base MH sampler with parallel tempering (PT) to escape
flat likelihood plateaus caused by the broad complex-structure posterior.

Algorithm:
    - Run N_temps replicas at inverse temperatures β_t ∈ (0, 1]
    - Cold chain (β=1.0) samples the true posterior
    - Hot chains (β<1.0) explore freely, flattening the likelihood
    - Periodic swap proposals exchange states between adjacent chains
      with Metropolis-Hastings acceptance: log α = (β_j - β_i)(log L_i - log L_j)

Reference:
    Geyer, C.J. (1991). Markov chain Monte Carlo maximum likelihood.
    Earl & Deem (2005). Parallel tempering: Theory, applications, pitfalls.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import numpy as np

from .sampler import (
    MCMCChain, MCMCConfig, MetropolisHastingsSampler,
    PARAM_NAMES, PARAM_BOUNDS, N_PARAMS, candidate_to_theta
)

logger = logging.getLogger(__name__)


@dataclass
class PTConfig:
    """Configuration for the Parallel Tempering sampler."""
    # Temperature ladder — β=1 is cold (target posterior), β<1 is hot (flattened)
    inverse_temps: List[float] = field(
        default_factory=lambda: [1.0, 0.5, 0.2, 0.1]
    )
    n_steps: int = 5000
    burn_in: int = 500
    thin_factor: int = 5
    swap_interval: int = 10       # Attempt a swap every N steps
    adapt_start: int = 100
    adapt_interval: int = 50
    seed: Optional[int] = None


@dataclass
class PTResult:
    """Output of a parallel tempering run — cold chain only."""
    cold_chain: MCMCChain          # β=1 chain (publication-quality)
    all_chains: List[MCMCChain]    # All temperature levels
    swap_acceptance_rates: List[float]  # Per adjacent-pair swap rate
    n_temps: int


class ParallelTemperingSampler:
    """
    Parallel Tempering MH sampler for K3×T² moduli space.

    Maintains N_temps replicas at different temperatures and
    periodically swaps states between adjacent replicas to
    allow the cold chain to escape local modes.

    Usage:
        pt = ParallelTemperingSampler(
            log_likelihood_fn=...,
            base_candidate=...,
            config=PTConfig(n_steps=8000),
        )
        result = pt.run(chain_id=0)
    """

    def __init__(
        self,
        log_likelihood_fn: Callable[[dict], float],
        base_candidate: dict,
        config: PTConfig = PTConfig(),
    ):
        self.log_likelihood_fn = log_likelihood_fn
        self.base_candidate = base_candidate
        self.config = config
        self.n_temps = len(config.inverse_temps)
        self.rng = np.random.default_rng(config.seed)

    def _log_prior(self, theta: np.ndarray) -> float:
        """Flat prior on bounded parameter space."""
        for i in range(N_PARAMS):
            if theta[i] < PARAM_BOUNDS[i, 0] or theta[i] > PARAM_BOUNDS[i, 1]:
                return -np.inf
        return 0.0

    def _log_likelihood(self, theta: np.ndarray) -> float:
        """Evaluate log-likelihood at θ."""
        from .sampler import theta_to_candidate
        candidate = theta_to_candidate(theta, self.base_candidate)
        try:
            return self.log_likelihood_fn(candidate)
        except Exception:
            return -np.inf

    def _initialize_states(self) -> np.ndarray:
        """
        Initialize all temperature replicas with over-dispersed starts.
        Returns array of shape (n_temps, N_PARAMS).
        """
        states = np.zeros((self.n_temps, N_PARAMS))
        for t in range(self.n_temps):
            for i in range(N_PARAMS):
                lo, hi = PARAM_BOUNDS[i]
                states[t, i] = self.rng.uniform(lo, hi)
        return states

    def _initial_proposals(self) -> List[np.ndarray]:
        """Initial diagonal proposal covariances per temperature."""
        covs = []
        base_step = np.array([p[3] for p in
                               [("t2_modulus_tau", 0.01, 1.50, 0.02),
                                ("cs_r",           0.01, 5.20, 0.05),
                                ("cs_theta",       0.00, 3.14, 0.05),
                                ("cs_phi",        -3.14, 3.14, 0.05),
                                ("picard_offset", -3.00, 3.00, 0.10)]])
        for t, beta in enumerate(self.config.inverse_temps):
            # Hot chains get wider proposals to explore faster
            temp_scale = (2.4 / math.sqrt(N_PARAMS)) * (1.0 / max(beta, 0.1)) ** 0.5
            covs.append(np.diag((temp_scale * base_step) ** 2))
        return covs

    def run(self, chain_id: int = 0) -> PTResult:
        """
        Execute parallel tempering.

        Returns:
            PTResult with cold chain (β=1) as the primary output.
        """
        cfg = self.config
        betas = np.array(cfg.inverse_temps)

        logger.info(
            f"PT Chain {chain_id}: {self.n_temps} temps = {list(betas)}, "
            f"{cfg.n_steps} steps"
        )

        # Initialize
        states = self._initialize_states()           # (n_temps, N_PARAMS)
        log_likes = np.array([
            self._log_likelihood(states[t]) for t in range(self.n_temps)
        ])
        log_priors = np.array([
            self._log_prior(states[t]) for t in range(self.n_temps)
        ])

        # Adaptive proposal covariances per temperature
        proposal_covs = self._initial_proposals()

        # Storage: full chains (pre-thinning) for all temps
        all_full = [np.zeros((cfg.n_steps, N_PARAMS)) for _ in range(self.n_temps)]
        all_ll_full = [np.zeros(cfg.n_steps) for _ in range(self.n_temps)]
        n_accepted = np.zeros(self.n_temps, dtype=int)
        swap_attempts = np.zeros(self.n_temps - 1, dtype=int)
        swap_accepted = np.zeros(self.n_temps - 1, dtype=int)

        # Welford running stats for each temp
        means = np.zeros((self.n_temps, N_PARAMS))
        cov_accs = np.zeros((self.n_temps, N_PARAMS, N_PARAMS))
        n_stats = np.zeros(self.n_temps, dtype=int)

        for step in range(cfg.n_steps):
            # ── MH step for each replica ──────────────────────────────
            for t in range(self.n_temps):
                beta = betas[t]
                theta_c = states[t]
                ll_c = log_likes[t]
                lp_c = log_priors[t]

                # Propose
                try:
                    theta_p = self.rng.multivariate_normal(theta_c, proposal_covs[t])
                except (np.linalg.LinAlgError, ValueError):
                    theta_p = theta_c + self.rng.normal(
                        0, np.sqrt(np.diag(proposal_covs[t]))
                    )

                lp_p = self._log_prior(theta_p)
                if np.isfinite(lp_p):
                    ll_p = self._log_likelihood(theta_p)
                else:
                    ll_p = -np.inf

                # Tempered acceptance: log α = β·(log L_p − log L_c) + log π_p − log π_c
                log_alpha = beta * (ll_p - ll_c) + (lp_p - lp_c)
                if np.isfinite(log_alpha) and math.log(self.rng.random()) < log_alpha:
                    states[t] = theta_p
                    log_likes[t] = ll_p
                    log_priors[t] = lp_p
                    n_accepted[t] += 1

                all_full[t][step] = states[t]
                all_ll_full[t][step] = log_likes[t]

                # Welford update for adaptive proposal
                if step >= cfg.adapt_start:
                    n_stats[t] += 1
                    delta = states[t] - means[t]
                    means[t] += delta / n_stats[t]
                    cov_accs[t] += np.outer(delta, states[t] - means[t])
                    if (step - cfg.adapt_start) % cfg.adapt_interval == 0 and n_stats[t] > 2 * N_PARAMS:
                        emp_cov = cov_accs[t] / (n_stats[t] - 1)
                        scale = (2.4 ** 2) / N_PARAMS / max(betas[t], 0.05)
                        proposal_covs[t] = scale * emp_cov + 1e-6 * np.eye(N_PARAMS)
                        try:
                            np.linalg.cholesky(proposal_covs[t])
                        except np.linalg.LinAlgError:
                            proposal_covs[t] = scale * np.diag(np.diag(emp_cov)) + 1e-6 * np.eye(N_PARAMS)

            # ── Swap step (every swap_interval steps) ─────────────────
            if step % cfg.swap_interval == 0:
                # Randomly choose an adjacent pair to attempt a swap
                t_lo = self.rng.integers(0, self.n_temps - 1)
                t_hi = t_lo + 1
                swap_attempts[t_lo] += 1

                # Swap acceptance: log α = (β_lo - β_hi)·(log L_hi - log L_lo)
                log_alpha_swap = (betas[t_lo] - betas[t_hi]) * (
                    log_likes[t_hi] - log_likes[t_lo]
                )
                if np.isfinite(log_alpha_swap) and math.log(self.rng.random()) < log_alpha_swap:
                    # Swap states, likelihoods, priors
                    states[t_lo], states[t_hi] = states[t_hi].copy(), states[t_lo].copy()
                    log_likes[t_lo], log_likes[t_hi] = log_likes[t_hi], log_likes[t_lo]
                    log_priors[t_lo], log_priors[t_hi] = log_priors[t_hi], log_priors[t_lo]
                    swap_accepted[t_lo] += 1

            # Progress log for cold chain
            if (step + 1) % max(1, cfg.n_steps // 5) == 0:
                cold_acc = n_accepted[0] / (step + 1)
                logger.info(
                    f"PT Chain {chain_id}: Step {step + 1}/{cfg.n_steps} "
                    f"| cold_acc={cold_acc:.3f} "
                    f"| cold_log_l={log_likes[0]:.4f} "
                    f"| swap_acc={swap_accepted.sum()}/{swap_attempts.sum()}"
                )

        # ── Post-process all chains ────────────────────────────────────
        mcmc_chains = []
        for t in range(self.n_temps):
            post_burn = all_full[t][cfg.burn_in:]
            post_burn_ll = all_ll_full[t][cfg.burn_in:]
            thinned = post_burn[::cfg.thin_factor]
            thinned_ll = post_burn_ll[::cfg.thin_factor]
            acc = n_accepted[t] / cfg.n_steps

            mcmc_chains.append(MCMCChain(
                chain_id=t,
                samples=thinned,
                log_likelihoods=thinned_ll,
                acceptance_rate=acc,
                n_steps_total=cfg.n_steps,
                n_steps_burn_in=cfg.burn_in,
            ))

        swap_rates = [
            swap_accepted[i] / max(1, swap_attempts[i])
            for i in range(self.n_temps - 1)
        ]

        logger.info(
            f"PT Chain {chain_id}: Complete. "
            f"Cold acc={n_accepted[0]/cfg.n_steps:.3f}, "
            f"Swap rates={[f'{r:.2f}' for r in swap_rates]}"
        )

        return PTResult(
            cold_chain=mcmc_chains[0],
            all_chains=mcmc_chains,
            swap_acceptance_rates=swap_rates,
            n_temps=self.n_temps,
        )
