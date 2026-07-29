"""
Adaptive Metropolis-Hastings MCMC Sampler (ST-2)
=================================================
Single-chain sampler operating on 5D K3×T² moduli space:
    θ = (τ, cs₁, cs₂, cs₃, picard_offset)

Features:
    - Adaptive proposal covariance (Haario et al. 2001)
    - Configurable burn-in and thinning
    - Flat priors on physically allowed ranges
    - Full chain storage with log-likelihoods
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Parameter Space Definition
# ---------------------------------------------------------------------------

# Each parameter: (name, min, max, default_step_size)
PARAM_SPEC = [
    ("t2_modulus_tau",  0.01,  1.50,  0.02),
    ("cs_1",          -3.00,  3.00,  0.05),
    ("cs_2",          -3.00,  3.00,  0.05),
    ("cs_3",          -3.00,  3.00,  0.05),
    ("picard_offset", -3.00,  3.00,  0.10),  # Continuous relaxation of integer Picard
]

PARAM_NAMES = [p[0] for p in PARAM_SPEC]
PARAM_BOUNDS = np.array([(p[1], p[2]) for p in PARAM_SPEC])
N_PARAMS = len(PARAM_SPEC)


@dataclass
class MCMCConfig:
    """Configuration for a single MCMC chain."""
    n_steps: int = 5000          # Total steps (including burn-in)
    burn_in: int = 500           # Steps to discard
    thin_factor: int = 5         # Keep every Nth sample
    adapt_start: int = 100       # Start adapting proposal after this many steps
    adapt_interval: int = 50     # Re-adapt proposal every N steps
    target_acceptance: float = 0.234  # Optimal for MH in ≥5D (Roberts et al. 1997)
    proposal_scale: float = 2.4       # Scale factor for adaptive proposal (2.4/√d)
    seed: Optional[int] = None


@dataclass
class MCMCChain:
    """Output of a single MCMC chain run."""
    chain_id: int
    samples: np.ndarray          # Shape (n_kept, N_PARAMS)
    log_likelihoods: np.ndarray  # Shape (n_kept,)
    acceptance_rate: float
    n_steps_total: int
    n_steps_burn_in: int
    param_names: List[str] = field(default_factory=lambda: list(PARAM_NAMES))


def theta_to_candidate(theta: np.ndarray, base_candidate: dict) -> dict:
    """
    Convert a 5D parameter vector θ back into a candidate dict
    compatible with the phenotype mapper.
    """
    candidate = dict(base_candidate)
    candidate["t2_modulus_tau"] = float(theta[0])
    candidate["complex_structure"] = [float(theta[1]), float(theta[2]), float(theta[3])]

    # Picard number: round the continuous offset to nearest integer, clamp to [1, 20]
    base_picard = base_candidate.get("picard_number", 19)
    candidate["picard_number"] = int(np.clip(
        base_picard + round(theta[4]), 1, 20
    ))
    return candidate


def candidate_to_theta(candidate: dict) -> np.ndarray:
    """Extract the 5D parameter vector from a candidate dict."""
    tau = candidate.get("t2_modulus_tau", 0.5)
    cs = candidate.get("complex_structure", [1.0, 1.0, 1.0])
    # picard_offset is 0 at initialization
    return np.array([tau, cs[0], cs[1], cs[2], 0.0])


class MetropolisHastingsSampler:
    """
    Adaptive Metropolis-Hastings sampler for K3×T² moduli space.

    The proposal distribution is a multivariate Gaussian whose covariance
    is adapted during the run to achieve optimal acceptance rate.

    Usage:
        sampler = MetropolisHastingsSampler(
            log_likelihood_fn=engine.log_likelihood,
            base_candidate={"picard_number": 19, ...},
            config=MCMCConfig(n_steps=5000),
        )
        chain = sampler.run(chain_id=0)
    """

    def __init__(
        self,
        log_likelihood_fn: Callable[[Dict[str, float]], float],
        base_candidate: dict,
        config: MCMCConfig = MCMCConfig(),
    ):
        self.log_likelihood_fn = log_likelihood_fn
        self.base_candidate = base_candidate
        self.config = config

        # Initialize RNG
        self.rng = np.random.default_rng(config.seed)

        # Initial proposal covariance: diagonal with default step sizes
        step_sizes = np.array([p[3] for p in PARAM_SPEC])
        scale = config.proposal_scale / math.sqrt(N_PARAMS)
        self.proposal_cov = np.diag((scale * step_sizes) ** 2)

        # Running statistics for adaptive covariance (Welford online algorithm)
        self._mean_acc = np.zeros(N_PARAMS)
        self._cov_acc = np.zeros((N_PARAMS, N_PARAMS))
        self._n_acc = 0

    def _log_prior(self, theta: np.ndarray) -> float:
        """Flat (uniform) prior on the bounded parameter space."""
        for i in range(N_PARAMS):
            if theta[i] < PARAM_BOUNDS[i, 0] or theta[i] > PARAM_BOUNDS[i, 1]:
                return -np.inf
        return 0.0

    def _evaluate(self, theta: np.ndarray) -> float:
        """Compute log-posterior = log-prior + log-likelihood."""
        lp = self._log_prior(theta)
        if not np.isfinite(lp):
            return -np.inf

        candidate = theta_to_candidate(theta, self.base_candidate)

        # The log_likelihood_fn should accept candidate dict and return log_l
        try:
            log_l = self.log_likelihood_fn(candidate)
        except Exception as e:
            logger.debug(f"Likelihood evaluation failed: {e}")
            return -np.inf

        return lp + log_l

    def _propose(self, theta_current: np.ndarray) -> np.ndarray:
        """Draw a proposal from the multivariate Gaussian centered at θ_current."""
        try:
            proposal = self.rng.multivariate_normal(theta_current, self.proposal_cov)
        except (np.linalg.LinAlgError, ValueError):
            # Fallback to diagonal perturbation if covariance is degenerate
            perturbation = self.rng.normal(0, np.sqrt(np.diag(self.proposal_cov)))
            proposal = theta_current + perturbation
        return proposal

    def _update_running_stats(self, theta: np.ndarray) -> None:
        """Welford's online algorithm for running mean and covariance."""
        self._n_acc += 1
        n = self._n_acc
        delta = theta - self._mean_acc
        self._mean_acc += delta / n
        delta2 = theta - self._mean_acc
        self._cov_acc += np.outer(delta, delta2)

    def _adapt_proposal(self) -> None:
        """Update proposal covariance from running statistics."""
        if self._n_acc < 2 * N_PARAMS:
            return  # Not enough samples to estimate covariance reliably

        empirical_cov = self._cov_acc / (self._n_acc - 1)
        scale = (self.config.proposal_scale ** 2) / N_PARAMS

        # Blend: 95% empirical + 5% identity (regularization)
        regularization = 0.05 * np.diag(np.diag(self.proposal_cov))
        self.proposal_cov = scale * empirical_cov + regularization

        # Ensure positive definiteness
        try:
            np.linalg.cholesky(self.proposal_cov)
        except np.linalg.LinAlgError:
            # Reset to diagonal of empirical variances
            self.proposal_cov = scale * np.diag(np.diag(empirical_cov)) + regularization

    def initialize_theta(self) -> np.ndarray:
        """
        Draw an initial θ from the prior (over-dispersed for multi-chain R̂).
        """
        theta = np.zeros(N_PARAMS)
        for i in range(N_PARAMS):
            lo, hi = PARAM_BOUNDS[i]
            theta[i] = self.rng.uniform(lo, hi)
        return theta

    def run(self, chain_id: int = 0, theta_init: Optional[np.ndarray] = None) -> MCMCChain:
        """
        Execute the MCMC chain.

        Args:
            chain_id: Integer identifier for this chain.
            theta_init: Optional starting point. If None, drawn from prior.

        Returns:
            MCMCChain with post-burn-in, thinned samples.
        """
        cfg = self.config

        # Initialize
        if theta_init is not None:
            theta_current = theta_init.copy()
        else:
            theta_current = self.initialize_theta()

        log_post_current = self._evaluate(theta_current)

        # Storage for full chain (pre-thinning)
        all_samples = np.zeros((cfg.n_steps, N_PARAMS))
        all_log_l = np.zeros(cfg.n_steps)
        n_accepted = 0

        logger.info(
            f"Chain {chain_id}: Starting {cfg.n_steps} steps "
            f"(burn-in={cfg.burn_in}, thin={cfg.thin_factor})"
        )

        for step in range(cfg.n_steps):
            # Propose
            theta_proposal = self._propose(theta_current)
            log_post_proposal = self._evaluate(theta_proposal)

            # Metropolis-Hastings acceptance criterion
            log_alpha = log_post_proposal - log_post_current
            if np.isfinite(log_alpha) and math.log(self.rng.random()) < log_alpha:
                theta_current = theta_proposal
                log_post_current = log_post_proposal
                n_accepted += 1

            all_samples[step] = theta_current
            all_log_l[step] = log_post_current

            # Update running statistics for adaptation
            if step >= cfg.adapt_start:
                self._update_running_stats(theta_current)
                if (step - cfg.adapt_start) % cfg.adapt_interval == 0:
                    self._adapt_proposal()

            # Progress logging
            if (step + 1) % max(1, cfg.n_steps // 10) == 0:
                acc_rate = n_accepted / (step + 1)
                logger.info(
                    f"Chain {chain_id}: Step {step + 1}/{cfg.n_steps} "
                    f"| acceptance={acc_rate:.3f} | log_post={log_post_current:.4f}"
                )

        # Post-process: remove burn-in and thin
        post_burn = all_samples[cfg.burn_in:]
        post_burn_ll = all_log_l[cfg.burn_in:]

        thinned_samples = post_burn[::cfg.thin_factor]
        thinned_ll = post_burn_ll[::cfg.thin_factor]

        acceptance_rate = n_accepted / cfg.n_steps

        logger.info(
            f"Chain {chain_id}: Complete. "
            f"Acceptance={acceptance_rate:.3f}, "
            f"Kept {len(thinned_samples)} samples"
        )

        return MCMCChain(
            chain_id=chain_id,
            samples=thinned_samples,
            log_likelihoods=thinned_ll,
            acceptance_rate=acceptance_rate,
            n_steps_total=cfg.n_steps,
            n_steps_burn_in=cfg.burn_in,
        )
