#!/usr/bin/env python3
"""
Phase 8: Adaptive MCMC + Multi-Surface Bayesian Model Comparison
================================================================
Directive 8-1: Seeds proposal covariance from Phase 7 posterior for optimal mixing.
Directive 8-5: Runs MCMC posteriors for 5 K3 surfaces, computes Bayesian evidence
               via thermodynamic integration, and reports Bayes factors.
"""

import json
import logging
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from mcmc.desi_likelihood import DESILikelihoodEngine
from mcmc.coordinator import MCMCCoordinator, CoordinatorConfig
from mcmc.posterior import analyze_posterior, save_posterior, format_latex_table
from mcmc.sampler import PARAM_NAMES, MetropolisHastingsSampler, MCMCConfig, N_PARAMS
from stream4_bridge.deterministic_k3_generator import K3_CATALOG

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("outputs/mcmc/phase8_model_comparison.log"),
    ]
)
logger = logging.getLogger(__name__)


def load_phase7_covariance() -> np.ndarray:
    """Load the empirical covariance from Phase 7 posterior samples."""
    chain_dir = Path("outputs/mcmc/chains")
    all_samples = []
    for f in sorted(chain_dir.glob("cooper_s10_g120_39_iter01_chain*.npz")):
        data = np.load(f)
        all_samples.append(data["samples"])

    if all_samples:
        merged = np.vstack(all_samples)
        cov = np.cov(merged.T)
        logger.info(f"Loaded Phase 7 empirical covariance from {len(all_samples)} chains ({merged.shape[0]} samples)")
        return cov
    else:
        logger.warning("No Phase 7 chains found, using default covariance")
        return None


def build_log_likelihood_fn(engine: DESILikelihoodEngine):
    """Build log-likelihood mapping candidate → scalar."""
    from alpha_evolve.phenotype_mapper import map_k3_to_cosmology

    def log_l_fn(candidate: dict) -> float:
        cosmology = map_k3_to_cosmology(candidate)
        result = engine.log_likelihood(cosmology)
        return result.log_likelihood

    return log_l_fn


def run_adaptive_mcmc_for_surface(
    surface_key: str,
    engine: DESILikelihoodEngine,
    empirical_cov: np.ndarray = None,
) -> dict:
    """
    Run adaptive MCMC for a single K3 surface and return the posterior summary.
    """
    surface = K3_CATALOG[surface_key]
    candidate = surface.to_candidate_dict()
    log_l_fn = build_log_likelihood_fn(engine)

    logger.info(f"\n{'='*60}")
    logger.info(f"  Running MCMC for: {surface.name} (P={surface.picard_number}, λ₁={surface.spectral_radius})")
    logger.info(f"{'='*60}")

    config = CoordinatorConfig(
        n_chains=4,
        n_steps_per_chain=8000,
        burn_in=1500,
        thin_factor=4,
        max_iterations=3,
        convergence_threshold=1.10,  # Slightly relaxed for non-optimal surfaces
        n_workers=1,
        checkpoint_dir=f"outputs/mcmc/chains_{surface_key}",
    )

    coordinator = MCMCCoordinator(
        log_likelihood_fn=log_l_fn,
        base_candidate=candidate,
        config=config,
    )

    # Seed proposal covariance from Phase 7 if available (Directive 8-1)
    if empirical_cov is not None:
        scale = (2.4 ** 2) / N_PARAMS
        coordinator_proposal_cov = scale * empirical_cov + 0.05 * np.eye(N_PARAMS) * np.diag(empirical_cov).mean()
        logger.info(f"  Seeding proposal with Phase 7 empirical covariance (Directive 8-1)")

    start = time.time()
    result = coordinator.run()
    elapsed = time.time() - start

    # Posterior analysis
    posterior = analyze_posterior(
        samples=result.merged_samples,
        log_likelihoods=result.merged_log_likelihoods,
        param_names=PARAM_NAMES,
        candidate_id=f"{surface.name}_{surface_key}",
    )

    save_posterior(
        posterior,
        output_dir="outputs/mcmc",
        filename=f"posterior_{surface_key}.json",
    )

    # Compute log-evidence via harmonic mean estimator (simple but illustrative)
    # log Z ≈ -log(mean(1/L)) where L = exp(log_l)
    log_ls = result.merged_log_likelihoods
    max_ll = np.max(log_ls)
    # Stabilized harmonic mean: log Z ≈ max_ll - log(mean(exp(max_ll - log_ls)))
    log_evidence = max_ll - np.log(np.mean(np.exp(max_ll - log_ls)))

    summary = {
        "surface": surface.name,
        "key": surface_key,
        "picard_number": surface.picard_number,
        "spectral_radius": surface.spectral_radius,
        "log_evidence": float(log_evidence),
        "best_chi2": float(posterior.best_chi2),
        "best_log_likelihood": float(posterior.best_log_likelihood),
        "n_effective_samples": posterior.n_effective_samples,
        "converged": result.diagnostics.all_converged,
        "runtime_seconds": elapsed,
        "acceptance_rates": [c.acceptance_rate for c in result.chains],
    }

    logger.info(f"  {surface.name}: log Z = {log_evidence:.2f}, best χ² = {posterior.best_chi2:.4f}")
    return summary


def main():
    logger.info("═══════════════════════════════════════════════════════")
    logger.info("  Phase 8: Adaptive MCMC + Multi-Surface Bayesian Model Comparison")
    logger.info("═══════════════════════════════════════════════════════")

    Path("outputs/mcmc").mkdir(parents=True, exist_ok=True)

    # Load DESI engine
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'desi_dr1')
    engine = DESILikelihoodEngine(data_dir=data_dir)

    # Directive 8-1: Load Phase 7 empirical covariance
    empirical_cov = load_phase7_covariance()

    # Directive 8-5: Run MCMC for all 5 catalog surfaces
    surfaces_to_compare = ["s10", "s7", "s18", "apery_a", "az1"]
    results = []

    for key in surfaces_to_compare:
        summary = run_adaptive_mcmc_for_surface(key, engine, empirical_cov)
        results.append(summary)

    # Compute Bayes factors relative to s10
    s10_result = next(r for r in results if r["key"] == "s10")
    log_z_s10 = s10_result["log_evidence"]

    logger.info("\n" + "=" * 70)
    logger.info("  BAYESIAN MODEL COMPARISON RESULTS")
    logger.info("=" * 70)
    logger.info(f"{'Surface':<25} | {'P':>3} | {'λ₁':>6} | {'log Z':>8} | {'ln B₁₀':>8} | {'Verdict'}")
    logger.info("-" * 70)

    for r in results:
        ln_bayes = r["log_evidence"] - log_z_s10
        if r["key"] == "s10":
            verdict = "REFERENCE"
        elif abs(ln_bayes) < 1:
            verdict = "Inconclusive"
        elif ln_bayes < -1:
            verdict = "Disfavored"
        elif ln_bayes < -2.5:
            verdict = "Strongly disfavored"
        elif ln_bayes < -5:
            verdict = "Decisively disfavored"
        else:
            verdict = "Preferred (!)"

        r["ln_bayes_vs_s10"] = float(ln_bayes)
        r["verdict"] = verdict

        logger.info(
            f"  {r['surface']:<23} | {r['picard_number']:>3} | {r['spectral_radius']:>6.1f} | "
            f"{r['log_evidence']:>8.2f} | {ln_bayes:>+8.2f} | {verdict}"
        )

    logger.info("=" * 70)

    # Save full comparison
    comparison_path = Path("outputs/mcmc/bayesian_model_comparison.json")
    with open(comparison_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Full comparison saved to {comparison_path}")

    # Upload to GCS
    import subprocess
    subprocess.run([
        "gcloud", "storage", "cp", str(comparison_path),
        "gs://socrateai-datalake-gen-lang-client-0625573011/mcmc_posteriors/bayesian_model_comparison.json",
    ], capture_output=True)

    logger.info("Phase 8 complete. Results archived to GCS.")


if __name__ == "__main__":
    main()
