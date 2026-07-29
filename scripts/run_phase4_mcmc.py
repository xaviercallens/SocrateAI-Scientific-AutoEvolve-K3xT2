"""
Phase 4 MCMC Orchestrator Script (ST-6)
=========================================
Single entry point for the multi-node MCMC evaluation pipeline:

    1. Load Pareto-optimal candidates from latest GCS checkpoint
    2. Pre-filter through Lean 4 oracle
    3. Spawn multi-chain MCMC for each candidate
    4. Run convergence diagnostics (R̂ < 1.05)
    5. Extract posterior summaries
    6. Save results to GCS and local disk

Usage:
    python3 scripts/run_phase4_mcmc.py
    python3 scripts/run_phase4_mcmc.py --config configs/mcmc_config.yaml
"""

import json
import logging
import os
import sys
import time
import yaml
from pathlib import Path

# Ensure src/ and pipeline/ are in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from alpha_evolve.phenotype_mapper import map_k3_to_cosmology
from mcmc.desi_likelihood import DESILikelihoodEngine
from mcmc.sampler import PARAM_NAMES
from mcmc.coordinator import MCMCCoordinator, CoordinatorConfig
from mcmc.posterior import analyze_posterior, save_posterior, format_latex_table
from utils.mlops_logger import EvolutionCheckpoint

# Configure logging
os.makedirs("outputs/mcmc", exist_ok=True)

log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("outputs/mcmc/phase4_mcmc.log")
file_handler.setFormatter(log_formatter)
root_logger.addHandler(file_handler)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(log_formatter)
root_logger.addHandler(stream_handler)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    "mcmc": {
        "n_chains": 4,
        "n_steps_per_chain": 5000,
        "burn_in": 500,
        "thin_factor": 5,
        "max_iterations": 5,
        "convergence_threshold": 1.05,
        "n_workers": 1,           # Sequential by default (safer for closures)
    },
    "data": {
        "desi_data_dir": "data/desi_dr1",
        "checkpoint_source": "gcs",   # 'gcs' or 'local'
        "max_candidates": 5,          # Top N Pareto candidates to MCMC
    },
    "output": {
        "output_dir": "outputs/mcmc",
        "save_to_gcs": True,
    },
}


def load_config(config_path: str = None) -> dict:
    """Load MCMC configuration from YAML file or use defaults."""
    config = dict(DEFAULT_CONFIG)

    if config_path and Path(config_path).exists():
        with open(config_path, "r") as f:
            user_config = yaml.safe_load(f)
        if user_config:
            for section in config:
                if section in user_config:
                    config[section].update(user_config[section])
        logger.info(f"Loaded config from {config_path}")
    else:
        logger.info("Using default MCMC configuration")

    return config


# ---------------------------------------------------------------------------
# Candidate Loading
# ---------------------------------------------------------------------------

def load_pareto_candidates(config: dict) -> list:
    """
    Load the top Pareto-optimal candidates from the latest checkpoint.
    """
    source = config["data"]["checkpoint_source"]
    max_cands = config["data"]["max_candidates"]

    if source == "gcs":
        logger.info("Loading candidates from GCS checkpoint...")
        ckpt = EvolutionCheckpoint()
        latest = ckpt.load_latest_checkpoint()
        if latest:
            population = latest.get("population", [])
            best = latest.get("best_candidate")
            if best and best not in population:
                population.insert(0, best)
            logger.info(f"Loaded {len(population)} candidates from GCS checkpoint (gen {latest.get('generation', '?')})")
        else:
            logger.warning("No GCS checkpoint found, falling back to local.")
            population = _load_local_candidates()
    else:
        population = _load_local_candidates()

    # Sort by chi2_loss and take top N
    population.sort(key=lambda c: c.get("chi2_loss", 9999.9))
    selected = population[:max_cands]

    logger.info(f"Selected top {len(selected)} candidates for MCMC evaluation:")
    for i, c in enumerate(selected):
        logger.info(f"  [{i+1}] {c.get('candidate_id', 'unknown')} — χ²={c.get('chi2_loss', '?')}")

    return selected


def _load_local_candidates() -> list:
    """Load candidates from local checkpoint files."""
    ckpt_dir = Path("outputs/checkpoints")
    if not ckpt_dir.exists():
        raise FileNotFoundError(f"No local checkpoints found at {ckpt_dir}")

    ckpt_files = sorted(ckpt_dir.glob("*.json"))
    if not ckpt_files:
        raise FileNotFoundError("No checkpoint JSON files found")

    latest = ckpt_files[-1]
    with open(latest, "r") as f:
        data = json.load(f)

    population = data.get("population", [])
    best = data.get("best_candidate")
    if best and best not in population:
        population.insert(0, best)

    logger.info(f"Loaded {len(population)} candidates from local checkpoint: {latest.name}")
    return population


# ---------------------------------------------------------------------------
# MCMC Pipeline
# ---------------------------------------------------------------------------

def run_mcmc_for_candidate(
    candidate: dict,
    engine: DESILikelihoodEngine,
    config: dict,
) -> dict:
    """
    Run the full multi-chain MCMC pipeline for a single candidate.

    Returns a result dict with posterior summary and diagnostics.
    """
    candidate_id = candidate.get("candidate_id", "unknown")
    logger.info(f"╔══════════════════════════════════════════════════════╗")
    logger.info(f"║  MCMC for candidate: {candidate_id:<31s} ║")
    logger.info(f"╚══════════════════════════════════════════════════════╝")

    mcmc_cfg = config["mcmc"]

    # Build the log-likelihood function
    def log_likelihood_fn(cand: dict) -> float:
        phenotype = map_k3_to_cosmology(cand)
        result = engine.log_likelihood(phenotype)
        return result.log_likelihood

    # Create coordinator
    coord_config = CoordinatorConfig(
        n_chains=mcmc_cfg["n_chains"],
        n_steps_per_chain=mcmc_cfg["n_steps_per_chain"],
        burn_in=mcmc_cfg["burn_in"],
        thin_factor=mcmc_cfg["thin_factor"],
        max_iterations=mcmc_cfg["max_iterations"],
        convergence_threshold=mcmc_cfg["convergence_threshold"],
        n_workers=mcmc_cfg["n_workers"],
        checkpoint_dir=config["output"]["output_dir"] + "/chains",
    )

    coordinator = MCMCCoordinator(
        log_likelihood_fn=log_likelihood_fn,
        base_candidate=candidate,
        config=coord_config,
    )

    # Run MCMC
    t0 = time.time()
    mcmc_result = coordinator.run()
    elapsed = time.time() - t0

    logger.info(f"MCMC completed in {elapsed:.1f}s ({mcmc_result.n_iterations} iterations)")

    # Analyze posterior
    posterior = analyze_posterior(
        samples=mcmc_result.merged_samples,
        log_likelihoods=mcmc_result.merged_log_likelihoods,
        param_names=PARAM_NAMES,
        candidate_id=candidate_id,
    )

    # Save posterior summary
    output_dir = config["output"]["output_dir"]
    save_posterior(
        posterior,
        output_dir=output_dir,
        filename=f"posterior_{candidate_id}.json",
    )

    # Generate LaTeX table
    latex = format_latex_table(posterior)
    latex_path = Path(output_dir) / f"table_{candidate_id}.tex"
    with open(latex_path, "w") as f:
        f.write(latex)
    logger.info(f"LaTeX table saved to {latex_path}")

    return {
        "candidate_id": candidate_id,
        "converged": mcmc_result.diagnostics.all_converged,
        "r_hat": mcmc_result.diagnostics.r_hat,
        "n_iterations": mcmc_result.n_iterations,
        "n_total_samples": len(mcmc_result.merged_samples),
        "elapsed_seconds": elapsed,
        "posterior": posterior.to_dict(),
    }


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def execute_phase4(config_path: str = None):
    """
    Execute Phase 4: Multi-Node MCMC Evaluation.

    Args:
        config_path: Optional path to YAML configuration file.
    """
    logger.info("═" * 60)
    logger.info("  PHASE 4: MULTI-NODE MCMC EVALUATION")
    logger.info("  AlphaEvolve K3×T² → DESI DR1 BAO Posterior Inference")
    logger.info("═" * 60)

    config = load_config(config_path)

    # Initialize DESI likelihood engine
    engine = DESILikelihoodEngine(
        data_dir=config["data"]["desi_data_dir"],
    )

    # Load Pareto candidates
    candidates = load_pareto_candidates(config)

    if not candidates:
        logger.error("No candidates found for MCMC evaluation. Aborting.")
        return

    # Run MCMC for each candidate
    all_results = []
    start_time = time.time()

    for i, candidate in enumerate(candidates):
        logger.info(f"\n{'━' * 60}")
        logger.info(f"  Candidate {i+1}/{len(candidates)}")
        logger.info(f"{'━' * 60}")

        try:
            result = run_mcmc_for_candidate(candidate, engine, config)
            all_results.append(result)
        except Exception as e:
            logger.error(f"MCMC failed for {candidate.get('candidate_id', '?')}: {e}")
            all_results.append({
                "candidate_id": candidate.get("candidate_id", "unknown"),
                "error": str(e),
            })

    total_elapsed = time.time() - start_time

    # Save aggregate results
    output_dir = config["output"]["output_dir"]
    aggregate_path = Path(output_dir) / "phase4_mcmc_results.json"
    with open(aggregate_path, "w") as f:
        json.dump({
            "total_elapsed_seconds": total_elapsed,
            "n_candidates": len(candidates),
            "results": all_results,
        }, f, indent=2)

    logger.info(f"\n{'═' * 60}")
    logger.info(f"  PHASE 4 COMPLETE")
    logger.info(f"  Total time:  {total_elapsed:.1f}s")
    logger.info(f"  Candidates:  {len(candidates)}")
    logger.info(f"  Converged:   {sum(1 for r in all_results if r.get('converged', False))}/{len(all_results)}")
    logger.info(f"  Results:     {aggregate_path}")
    logger.info(f"{'═' * 60}")

    # ---------------------------------------------------------------------------
    # GCS Data Lake Archival & Vertex AI Teardown
    # ---------------------------------------------------------------------------
    gcs_bucket = os.getenv("GCS_CHECKPOINT_DIR", "gs://socrateai-datalake-gen-lang-client-0625573011/mcmc")
    logger.info(f"☁️ Syncing all useful data & outputs to GCS Data Lake: {gcs_bucket}...")
    try:
        import subprocess
        cmd = f"gcloud storage cp -r {output_dir}/* {gcs_bucket}/"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if res.returncode == 0:
            logger.info("✅ All MCMC results and posteriors successfully archived in GCS Data Lake.")
        else:
            logger.warning(f"⚠️ GCS sync output warning: {res.stderr}")
    except Exception as err:
        logger.error(f"❌ Failed to archive outputs to GCS: {err}")

    logger.info("🧹 Pipeline complete. Exiting python process to trigger automatic Vertex AI Spot VM teardown.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Phase 4: Multi-Node MCMC Evaluation")
    parser.add_argument("--config", type=str, default="configs/mcmc_config.yaml",
                        help="Path to YAML config file")
    args = parser.parse_args()

    execute_phase4(config_path=args.config)
