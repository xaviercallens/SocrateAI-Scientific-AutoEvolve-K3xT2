#!/usr/bin/env python3
"""
Phase 7: MCMC Posterior Characterization of cooper_s10_g120_39
===============================================================
Runs a 4-chain MCMC campaign using the DESI+NanoGrav combined likelihood
against the Deep Burn Gen 150 best candidate, then extracts publication-ready
posterior summaries and generates corner plots.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

import numpy as np

# Ensure src/ is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from mcmc.desi_likelihood import DESILikelihoodEngine
from mcmc.coordinator import MCMCCoordinator, CoordinatorConfig
from mcmc.posterior import analyze_posterior, save_posterior, format_latex_table
from mcmc.sampler import PARAM_NAMES

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("outputs/mcmc/phase7_mcmc.log"),
    ]
)
logger = logging.getLogger(__name__)


def load_best_candidate() -> dict:
    """Load the Gen 150 best candidate from GCS checkpoint."""
    import subprocess
    
    gcs_path = "gs://socrateai-datalake-gen-lang-client-0625573011/checkpoints/run_20260729_074350_gen_0150.json"
    logger.info(f"Loading seed candidate from {gcs_path}")
    
    result = subprocess.run(
        ["gcloud", "storage", "cat", gcs_path],
        capture_output=True, text=True, timeout=30,
    )
    
    if result.returncode != 0:
        logger.warning(f"GCS load failed: {result.stderr}")
        # Fallback: use hardcoded best from Deep Burn log
        return {
            "candidate_id": "cooper_s10_g120_39",
            "picard_number": 19,
            "moduli_stabilization": 0.75,
            "complex_structure": [0.1442076635760447, -1.4270030737098205, 0.968729155608357],
            "t2_modulus_tau": 0.4999066173136379,
            "phenotype": {
                "w0": -0.999953308656819,
                "omega_m": 0.3,
                "h0": 67.39744127758337,
                "pta_f_monopole": 9.99990661731364e-10,
                "s8_gradient": 0.83,
            },
            "likelihood": {
                "chi2": 1.9774028401080412e-06,
                "fitness": 0.99999802260107,
            },
        }
    
    data = json.loads(result.stdout)
    return data.get("best_candidate", data)


def build_log_likelihood_fn(engine: DESILikelihoodEngine):
    """
    Build a log-likelihood function that maps a K3xT2 candidate dict
    to a scalar log-likelihood value via the phenotype mapper + DESI+NanoGrav.
    """
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
    from alpha_evolve.phenotype_mapper import map_k3_to_cosmology
    
    def log_l_fn(candidate: dict) -> float:
        cosmology = map_k3_to_cosmology(candidate)
        result = engine.log_likelihood(cosmology)
        return result.log_likelihood
    
    return log_l_fn


def generate_corner_plot(samples: np.ndarray, param_names: list, output_path: str):
    """Generate a publication-quality corner plot from MCMC samples."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    
    n_params = samples.shape[1]
    fig, axes = plt.subplots(n_params, n_params, figsize=(12, 12))
    
    # Cosmological parameter labels
    labels = [r"$\tau_{T^2}$", r"$\mathrm{Re}(\tau_{K3})$", 
              r"$\mathrm{Im}(\tau_{K3})$", r"$\rho_{K3}$", r"$\delta P$"]
    
    colors = {
        'hist': '#2563eb',
        'scatter': '#2563eb',
        'contour_68': '#3b82f6',
        'contour_95': '#93c5fd',
    }
    
    for i in range(n_params):
        for j in range(n_params):
            ax = axes[i, j]
            if j > i:
                ax.set_visible(False)
                continue
            
            if i == j:
                # 1D marginal histogram
                ax.hist(samples[:, i], bins=50, density=True,
                        color=colors['hist'], alpha=0.7, edgecolor='white', linewidth=0.3)
                ax.set_yticks([])
                
                # Mark MAP
                ax.axvline(np.mean(samples[:, i]), color='#dc2626', linewidth=1.5, 
                          linestyle='--', alpha=0.8)
            else:
                # 2D scatter/contour
                ax.scatter(samples[:, j], samples[:, i], s=0.5, alpha=0.05, 
                          color=colors['scatter'], rasterized=True)
                
                # 2D kernel density contours (if enough samples)
                if len(samples) > 100:
                    from scipy.stats import gaussian_kde
                    try:
                        xy = np.vstack([samples[:, j], samples[:, i]])
                        kde = gaussian_kde(xy)
                        x_grid = np.linspace(samples[:, j].min(), samples[:, j].max(), 50)
                        y_grid = np.linspace(samples[:, i].min(), samples[:, i].max(), 50)
                        X, Y = np.meshgrid(x_grid, y_grid)
                        Z = kde(np.vstack([X.ravel(), Y.ravel()])).reshape(X.shape)
                        ax.contour(X, Y, Z, levels=2, colors=[colors['contour_95'], colors['contour_68']],
                                  linewidths=1.0, alpha=0.8)
                    except Exception:
                        pass  # Skip contours if KDE fails
            
            # Labels on edges only
            if i == n_params - 1:
                ax.set_xlabel(labels[j], fontsize=10)
            else:
                ax.set_xticklabels([])
            
            if j == 0 and i > 0:
                ax.set_ylabel(labels[i], fontsize=10)
            elif j > 0:
                ax.set_yticklabels([])
    
    fig.suptitle(r"$K3 \times T^2$ Posterior: Cooper $s_{10}$ ($P=19$)", fontsize=14, y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    fig.savefig(output_path.replace('.pdf', '.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)
    logger.info(f"Corner plot saved to {output_path}")


def main():
    start_time = time.time()
    
    logger.info("═══════════════════════════════════════════════════════")
    logger.info("  Phase 7: MCMC Posterior Characterization")
    logger.info("  Candidate: cooper_s10_g120_39 (Deep Burn Gen 150)")
    logger.info("═══════════════════════════════════════════════════════")
    
    # Ensure output directories exist
    Path("outputs/mcmc/chains").mkdir(parents=True, exist_ok=True)
    
    # 1. Load the best candidate from GCS
    best_candidate = load_best_candidate()
    logger.info(f"Seed candidate: {best_candidate.get('candidate_id', 'unknown')}")
    logger.info(f"Seed χ² = {best_candidate.get('chi2_loss', best_candidate.get('likelihood', {}).get('chi2', 'N/A'))}")
    
    # 2. Initialize the DESI+NanoGrav likelihood engine
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'desi_dr1')
    engine = DESILikelihoodEngine(data_dir=data_dir)
    log_l_fn = build_log_likelihood_fn(engine)
    
    # 3. Configure the 4-chain MCMC coordinator
    config = CoordinatorConfig(
        n_chains=4,
        n_steps_per_chain=10000,
        burn_in=2000,
        thin_factor=5,
        max_iterations=5,
        convergence_threshold=1.05,
        n_workers=1,   # Sequential for stability (avoid pickle issues)
        checkpoint_dir="outputs/mcmc/chains",
    )
    
    coordinator = MCMCCoordinator(
        log_likelihood_fn=log_l_fn,
        base_candidate=best_candidate,
        config=config,
    )
    
    # 4. Run the MCMC
    logger.info("Launching 4-chain MCMC with iterative convergence control...")
    result = coordinator.run()
    
    elapsed = time.time() - start_time
    logger.info(f"MCMC completed in {elapsed:.1f}s ({elapsed/3600:.2f}h)")
    logger.info(f"Convergence iterations: {result.n_iterations}")
    logger.info(f"Total merged samples: {result.merged_samples.shape}")
    
    # 5. Posterior analysis
    logger.info("Computing posterior summary statistics...")
    posterior = analyze_posterior(
        samples=result.merged_samples,
        log_likelihoods=result.merged_log_likelihoods,
        param_names=PARAM_NAMES,
        candidate_id=result.candidate_id,
    )
    
    # Save posterior JSON
    save_posterior(
        posterior,
        output_dir="outputs/mcmc",
        filename=f"posterior_{result.candidate_id}.json",
    )
    
    # Generate LaTeX table
    latex_table = format_latex_table(posterior)
    latex_path = Path("outputs/mcmc") / f"latex_table_{result.candidate_id}.tex"
    with open(latex_path, "w") as f:
        f.write(latex_table)
    logger.info(f"LaTeX table saved to {latex_path}")
    
    # 6. Generate corner plot
    logger.info("Generating publication corner plot...")
    generate_corner_plot(
        samples=result.merged_samples,
        param_names=PARAM_NAMES,
        output_path="paper/figures/dual_track_corner.pdf",
    )
    
    # 7. Upload results to GCS
    logger.info("Archiving results to GCS Data Lake...")
    import subprocess
    
    posterior_json = f"outputs/mcmc/posterior_{result.candidate_id}.json"
    subprocess.run([
        "gcloud", "storage", "cp", posterior_json,
        f"gs://socrateai-datalake-gen-lang-client-0625573011/mcmc_posteriors/posterior_{result.candidate_id}.json",
    ], capture_output=True)
    
    subprocess.run([
        "gcloud", "storage", "cp", "-r", "outputs/mcmc/chains/",
        f"gs://socrateai-datalake-gen-lang-client-0625573011/mcmc_chains/",
    ], capture_output=True)
    
    subprocess.run([
        "gcloud", "storage", "cp",
        "paper/figures/dual_track_corner.pdf",
        "gs://socrateai-datalake-gen-lang-client-0625573011/publications/paper_figures/dual_track_corner.pdf",
    ], capture_output=True)
    
    logger.info("═══════════════════════════════════════════════════════")
    logger.info("  Phase 7 MCMC COMPLETE")
    logger.info(f"  Runtime: {elapsed:.1f}s")
    logger.info(f"  Converged: {result.diagnostics.all_converged}")
    logger.info(f"  Effective samples: {posterior.n_effective_samples}")
    logger.info("═══════════════════════════════════════════════════════")
    
    # Print summary
    print("\n" + "=" * 60)
    print("  POSTERIOR SUMMARY")
    print("=" * 60)
    for p in posterior.parameters:
        print(f"  {p.name:20s}: {p.mean:.5f} ± {p.std:.5f}")
        print(f"  {'':20s}  68% HPD: [{p.hpd_68[0]:.5f}, {p.hpd_68[1]:.5f}]")
        print(f"  {'':20s}  95% HPD: [{p.hpd_95[0]:.5f}, {p.hpd_95[1]:.5f}]")
    print("=" * 60)


if __name__ == "__main__":
    main()
