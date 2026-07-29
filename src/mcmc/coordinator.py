"""
Multi-Node MCMC Coordinator (ST-3)
====================================
Spawns N independent MCMC chains in parallel, collects results, runs
convergence diagnostics, and optionally re-runs with extended steps
until R̂ converges.

Supports:
    - Local multiprocessing (ProcessPoolExecutor)
    - Over-dispersed initialization (Gelman recommendation)
    - GCS-backed chain checkpointing via EvolutionCheckpoint
    - Iterative convergence: extends chains if R̂ ≥ threshold
    - Budget guardrail: hard USD ceiling with graceful shutdown (Phase 4)
"""

import json
import logging
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np

from .sampler import (
    MCMCChain, MCMCConfig, MetropolisHastingsSampler,
    PARAM_NAMES, N_PARAMS, candidate_to_theta,
)
from .diagnostics import ConvergenceDiagnostics, run_all_diagnostics

try:
    from core.budget_guard import BudgetGuard, BudgetConfig
except ImportError:
    BudgetGuard = None
    BudgetConfig = None

logger = logging.getLogger(__name__)


@dataclass
class CoordinatorConfig:
    """Configuration for the multi-chain MCMC coordinator."""
    n_chains: int = 4
    n_steps_per_chain: int = 5000
    burn_in: int = 500
    thin_factor: int = 5
    max_iterations: int = 5         # Max convergence re-runs
    convergence_threshold: float = 1.05
    n_workers: int = 0              # 0 = auto (os.cpu_count())
    checkpoint_dir: str = "outputs/mcmc/chains"
    gcs_checkpoint_prefix: str = "mcmc_chains"


@dataclass
class MCMCResult:
    """Aggregated result from a multi-chain MCMC run."""
    chains: List[MCMCChain]
    diagnostics: ConvergenceDiagnostics
    merged_samples: np.ndarray       # All chains concatenated (n_total, n_params)
    merged_log_likelihoods: np.ndarray
    candidate_id: str
    n_iterations: int                # How many convergence iterations were needed
    budget_status: Optional[dict] = None  # Budget guardrail status at completion


def _run_single_chain(args: Tuple) -> MCMCChain:
    """
    Worker function for parallel chain execution.
    Must be a top-level function for pickling compatibility with ProcessPoolExecutor.

    Args:
        args: Tuple of (chain_id, log_l_fn, base_candidate, config, seed)
    """
    chain_id, log_l_fn, base_candidate, config, seed = args

    chain_config = MCMCConfig(
        n_steps=config.n_steps_per_chain,
        burn_in=config.burn_in,
        thin_factor=config.thin_factor,
        seed=seed,
    )

    sampler = MetropolisHastingsSampler(
        log_likelihood_fn=log_l_fn,
        base_candidate=base_candidate,
        config=chain_config,
    )
    return sampler.run(chain_id=chain_id)


class MCMCCoordinator:
    """
    Coordinates multiple MCMC chains with convergence control.

    Usage:
        coordinator = MCMCCoordinator(
            log_likelihood_fn=lambda cand: engine.log_likelihood(
                phenotype_mapper.map_k3_to_cosmology(cand)
            ).log_likelihood,
            base_candidate=pareto_best,
            config=CoordinatorConfig(n_chains=4),
        )
        result = coordinator.run()
    """

    def __init__(
        self,
        log_likelihood_fn: Callable[[dict], float],
        base_candidate: dict,
        config: CoordinatorConfig = CoordinatorConfig(),
        budget_guard: Optional["BudgetGuard"] = None,
    ):
        self.log_likelihood_fn = log_likelihood_fn
        self.base_candidate = base_candidate
        self.config = config
        self.candidate_id = base_candidate.get("candidate_id", "unknown")

        # Budget guardrail integration
        self.budget_guard = budget_guard

        # Determine worker count
        if config.n_workers <= 0:
            self.n_workers = min(config.n_chains, os.cpu_count() or 1)
        else:
            self.n_workers = config.n_workers

        # Ensure checkpoint directory exists
        Path(config.checkpoint_dir).mkdir(parents=True, exist_ok=True)

    def _generate_seeds(self, iteration: int) -> List[int]:
        """Generate reproducible but distinct seeds for each chain."""
        base = hash(self.candidate_id) % (2**31)
        return [base + iteration * 1000 + i for i in range(self.config.n_chains)]

    def _spawn_chains_sequential(
        self, seeds: List[int]
    ) -> List[MCMCChain]:
        """
        Run chains sequentially (fallback for single-process or debug mode).
        """
        chains = []
        for chain_id, seed in enumerate(seeds):
            chain_config = MCMCConfig(
                n_steps=self.config.n_steps_per_chain,
                burn_in=self.config.burn_in,
                thin_factor=self.config.thin_factor,
                seed=seed,
            )
            sampler = MetropolisHastingsSampler(
                log_likelihood_fn=self.log_likelihood_fn,
                base_candidate=self.base_candidate,
                config=chain_config,
            )
            chains.append(sampler.run(chain_id=chain_id))
        return chains

    def _spawn_chains_parallel(
        self, seeds: List[int]
    ) -> List[MCMCChain]:
        """
        Spawn chains in parallel using ProcessPoolExecutor.

        Note: The log_likelihood_fn must be picklable. For complex closures,
        fall back to sequential mode.
        """
        try:
            args_list = [
                (i, self.log_likelihood_fn, self.base_candidate, self.config, seed)
                for i, seed in enumerate(seeds)
            ]
            chains = []
            with ProcessPoolExecutor(max_workers=self.n_workers) as executor:
                futures = {
                    executor.submit(_run_single_chain, args): args[0]
                    for args in args_list
                }
                for future in as_completed(futures):
                    chain_id = futures[future]
                    try:
                        chain = future.result()
                        chains.append(chain)
                        logger.info(
                            f"Chain {chain_id} completed: "
                            f"acceptance={chain.acceptance_rate:.3f}, "
                            f"samples={len(chain.samples)}"
                        )
                    except Exception as e:
                        logger.error(f"Chain {chain_id} failed: {e}")

            # Sort by chain_id to ensure deterministic ordering
            chains.sort(key=lambda c: c.chain_id)
            return chains

        except Exception as e:
            logger.warning(f"Parallel execution failed ({e}), falling back to sequential.")
            return self._spawn_chains_sequential(seeds)

    def _save_chain_checkpoint(
        self, chains: List[MCMCChain], iteration: int
    ) -> None:
        """Save chain states to local disk."""
        ckpt_path = Path(self.config.checkpoint_dir)
        for chain in chains:
            filename = (
                f"{self.candidate_id}_iter{iteration:02d}_chain{chain.chain_id:02d}.npz"
            )
            filepath = ckpt_path / filename
            np.savez_compressed(
                str(filepath),
                samples=chain.samples,
                log_likelihoods=chain.log_likelihoods,
                acceptance_rate=np.array([chain.acceptance_rate]),
            )
        logger.info(
            f"Saved {len(chains)} chain checkpoints to {ckpt_path} (iteration {iteration})"
        )

    def run(self) -> MCMCResult:
        """
        Execute the multi-chain MCMC with iterative convergence control.

        Returns:
            MCMCResult with merged chains and diagnostics.
        """
        cfg = self.config

        logger.info(
            f"═══════════════════════════════════════════════════════\n"
            f"  Multi-Node MCMC Coordinator\n"
            f"  Candidate:    {self.candidate_id}\n"
            f"  Chains:       {cfg.n_chains}\n"
            f"  Steps/chain:  {cfg.n_steps_per_chain}\n"
            f"  Burn-in:      {cfg.burn_in}\n"
            f"  Thin factor:  {cfg.thin_factor}\n"
            f"  R̂ threshold:  {cfg.convergence_threshold}\n"
            f"  Workers:      {self.n_workers}\n"
            f"═══════════════════════════════════════════════════════"
        )

        for iteration in range(1, cfg.max_iterations + 1):
            logger.info(f"━━━ Convergence Iteration {iteration}/{cfg.max_iterations} ━━━")

            # ── Budget Guardrail Check ──────────────────────────────
            if self.budget_guard is not None:
                budget_status = self.budget_guard.check()
                logger.info(self.budget_guard.format_status_line())
                if budget_status["action"] == "STOP":
                    logger.warning(
                        f"🛑 BUDGET CEILING REACHED at iteration {iteration}. "
                        f"Saving checkpoint and terminating gracefully."
                    )
                    if iteration > 1:
                        self._save_chain_checkpoint(chains, iteration)
                        return self._build_result(chains, diagnostics, iteration)
                    else:
                        raise RuntimeError(
                            f"Budget exhausted before first iteration: "
                            f"${budget_status['estimated_spend_usd']:.2f} / "
                            f"${self.budget_guard.config.budget_ceiling_usd:.2f}"
                        )

            seeds = self._generate_seeds(iteration)

            # Spawn chains (parallel or sequential)
            if self.n_workers > 1:
                chains = self._spawn_chains_parallel(seeds)
            else:
                chains = self._spawn_chains_sequential(seeds)

            if len(chains) < 2:
                logger.error(
                    f"Only {len(chains)} chains completed. "
                    f"Need ≥ 2 for R̂. Aborting."
                )
                raise RuntimeError("Insufficient chains for convergence diagnostics.")

            # Save checkpoint
            self._save_chain_checkpoint(chains, iteration)

            # Run convergence diagnostics
            sample_arrays = [c.samples for c in chains]
            diagnostics = run_all_diagnostics(
                sample_arrays,
                PARAM_NAMES,
                convergence_threshold=cfg.convergence_threshold,
            )

            logger.info(diagnostics.summary())

            if diagnostics.all_converged:
                logger.info(
                    f"✅ Convergence achieved at iteration {iteration}. "
                    f"Finalizing results."
                )
                return self._build_result(chains, diagnostics, iteration)

            # Not converged: increase steps for next iteration
            logger.warning(
                f"❌ R̂ not converged at iteration {iteration}. "
                f"Extending chain length by 50%."
            )
            cfg.n_steps_per_chain = int(cfg.n_steps_per_chain * 1.5)
            cfg.burn_in = int(cfg.burn_in * 1.5)

        # Exhausted iterations — return best result with warning
        logger.warning(
            f"⚠️ Max iterations ({cfg.max_iterations}) reached without full convergence. "
            f"Returning last result."
        )
        return self._build_result(chains, diagnostics, cfg.max_iterations)

    def _build_result(
        self,
        chains: List[MCMCChain],
        diagnostics: ConvergenceDiagnostics,
        n_iterations: int,
    ) -> MCMCResult:
        """Merge chains and build final result."""
        merged_samples = np.vstack([c.samples for c in chains])
        merged_ll = np.concatenate([c.log_likelihoods for c in chains])

        # Capture budget status at completion
        budget_status = None
        if self.budget_guard is not None:
            budget_status = self.budget_guard.check()

        return MCMCResult(
            chains=chains,
            diagnostics=diagnostics,
            merged_samples=merged_samples,
            merged_log_likelihoods=merged_ll,
            candidate_id=self.candidate_id,
            n_iterations=n_iterations,
            budget_status=budget_status,
        )
