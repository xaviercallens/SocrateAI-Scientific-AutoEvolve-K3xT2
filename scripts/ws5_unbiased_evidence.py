#!/usr/bin/env python3
import os
import sys
import json
import logging
import numpy as np
import subprocess
from pathlib import Path
from scipy.stats import multivariate_normal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add src to python path
sys.path.insert(0, os.path.abspath('.'))

from src.mcmc.desi_likelihood import DESILikelihoodEngine
from src.mcmc.spherical_sampler import candidate_to_spherical, SPHER_PARAM_NAMES
from src.alpha_evolve.phenotype_mapper import map_k3_to_cosmology

def download_checkpoints():
    logger.info("Downloading GCS checkpoints for generation 1-300...")
    os.makedirs("data/checkpoints", exist_ok=True)
    
    # Check if they are already downloaded
    existing = list(Path("data/checkpoints").glob("*.json"))
    if len(existing) >= 300:
        logger.info(f"Found {len(existing)} checkpoints already downloaded.")
        return
        
    cmd = [
        "gcloud", "storage", "cp", 
        "gs://socrateai-datalake-gen-lang-client-0625573011/checkpoints/run_20260729_074350_gen_*.json", 
        "data/checkpoints/"
    ]
    subprocess.run(cmd, check=True)

def load_candidates():
    candidates_train = []
    candidates_test = []
    
    files = sorted(Path("data/checkpoints").glob("*.json"))
    for f in files:
        # Extract generation number
        try:
            gen = int(f.stem.split("_gen_")[-1])
            with open(f, "r") as fh:
                data = json.load(fh)
                
            # data could be dict with candidate_id or "global_best" etc.
            if "best_candidate" in data:
                c = data["best_candidate"]
            elif "global_best" in data:
                c = data["global_best"]
            else:
                c = data
                
            if gen <= 150:
                candidates_train.append(c)
            else:
                candidates_test.append(c)
        except Exception as e:
            logger.warning(f"Failed to load {f}: {e}")
            
    return candidates_train, candidates_test

def extract_theta(candidates):
    thetas = []
    for c in candidates:
        if "t2_modulus_tau" in c and "complex_structure" in c:
            th = candidate_to_spherical(c)
            thetas.append(th)
    return np.array(thetas)

def log_likelihood_joint(theta, engine):
    from src.mcmc.spherical_sampler import spherical_to_candidate
    base = {"picard_number": 18}
    cand = spherical_to_candidate(theta, base)
    pheno = map_k3_to_cosmology(cand)
    res = engine.log_likelihood(pheno)
    return res.log_likelihood

def main():
    out_dir = Path("outputs/ws5")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    download_checkpoints()
    
    train_cands, test_cands = load_candidates()
    logger.info(f"Loaded {len(train_cands)} training candidates and {len(test_cands)} test candidates.")
    
    theta_train = extract_theta(train_cands)
    theta_test = extract_theta(test_cands)
    
    if len(theta_train) < 2:
        logger.error("Not enough training candidates to form covariance prior.")
        sys.exit(1)
        
    # Build prior from training set
    mu_prior = np.mean(theta_train, axis=0)
    cov_prior = np.cov(theta_train, rowvar=False) + np.eye(len(mu_prior)) * 1e-4  # regularize
    
    logger.info(f"Prior Mean: {mu_prior}")
    
    # We will compute the evidence using Monte Carlo integration (a very simplified form of nested sampling for this script)
    # Evidence Z = \int L(theta) * p(theta) d\theta
    # We draw samples from the prior and average the likelihood.
    engine = DESILikelihoodEngine()
    
    # Generate samples from prior
    N_samples = 1000
    np.random.seed(42)
    prior_samples = np.random.multivariate_normal(mu_prior, cov_prior, size=N_samples)
    
    logger.info(f"Computing unbiased evidence using {N_samples} Monte Carlo samples from train prior...")
    
    likelihoods = []
    for i, th in enumerate(prior_samples):
        # Apply bounds manually (from SPHER_PARAM_BOUNDS)
        from src.mcmc.spherical_sampler import SPHER_PARAM_BOUNDS
        valid = True
        for j, bounds in enumerate(SPHER_PARAM_BOUNDS):
            if not (bounds[0] <= th[j] <= bounds[1]):
                valid = False
                break
        
        if valid:
            ll = log_likelihood_joint(th, engine)
            likelihoods.append(ll)
        else:
            likelihoods.append(-1e10) # invalid prior
            
    likelihoods = np.array(likelihoods)
    
    # LogSumExp trick for numerical stability
    max_ll = np.max(likelihoods)
    if max_ll == -1e10:
        log_Z = -np.inf
    else:
        sum_exp = np.sum(np.exp(likelihoods - max_ll))
        log_Z = max_ll + np.log(sum_exp / N_samples)
        
    logger.info(f"Unbiased Bayesian Evidence ln(Z) = {log_Z:.2f}")
    
    # The current ln Z is -7.38 from biased estimates
    biased_log_Z = -7.38
    # Occam penalty = difference
    diff = log_Z - biased_log_Z
    
    # Save results
    results = {
        "train_samples": len(theta_train),
        "test_samples": len(theta_test),
        "prior_mean": mu_prior.tolist(),
        "prior_cov": cov_prior.tolist(),
        "unbiased_log_Z": float(log_Z),
        "biased_log_Z": float(biased_log_Z),
        "difference": float(diff),
        "pass": bool(log_Z > -10.0)
    }
    
    with open(out_dir / "split_bayes_evidence.json", "w") as f:
        json.dump(results, f, indent=2)
        
    with open(out_dir / "WS5_REPORT.md", "w") as f:
        f.write("# WS5 Unbiased Bayesian Evidence Report\n\n")
        f.write(f"- **Unbiased ln(Z)**: {log_Z:.2f}\n")
        f.write(f"- **Biased ln(Z)**: {biased_log_Z:.2f}\n")
        f.write(f"- **Difference**: {diff:.2f}\n\n")
        
        if log_Z > -10.0:
            f.write("PASS: The unbiased Bayes factor is not strongly against K3xT2.\n")
        else:
            f.write("FAIL: Strong evidence against, indicating original result was an artifact of circular priors.\n")
            
    logger.info("Done.")

if __name__ == "__main__":
    main()
