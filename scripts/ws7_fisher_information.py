#!/usr/bin/env python3
import sys
import os
import json
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add src to python path
sys.path.insert(0, os.path.abspath('.'))

from src.mcmc.desi_likelihood import DESILikelihoodEngine
from src.alpha_evolve.phenotype_mapper import map_k3_to_cosmology
from src.mcmc.spherical_sampler import spherical_to_candidate, candidate_to_spherical, SPHER_PARAM_NAMES

def get_log_likelihood(theta, engine, base_candidate):
    candidate = spherical_to_candidate(theta, base_candidate)
    phenotype = map_k3_to_cosmology(candidate)
    res = engine.log_likelihood(phenotype)
    return res.log_likelihood

def compute_hessian(func, x0, epsilon=1e-4):
    n = len(x0)
    hessian = np.zeros((n, n))
    f0 = func(x0)
    
    for i in range(n):
        for j in range(i, n):
            if i == j:
                x_fwd = x0.copy()
                x_bwd = x0.copy()
                x_fwd[i] += epsilon
                x_bwd[i] -= epsilon
                hessian[i, i] = (func(x_fwd) - 2 * f0 + func(x_bwd)) / (epsilon ** 2)
            else:
                x_pp = x0.copy()
                x_pm = x0.copy()
                x_mp = x0.copy()
                x_mm = x0.copy()
                
                x_pp[i] += epsilon
                x_pp[j] += epsilon
                
                x_pm[i] += epsilon
                x_pm[j] -= epsilon
                
                x_mp[i] -= epsilon
                x_mp[j] += epsilon
                
                x_mm[i] -= epsilon
                x_mm[j] -= epsilon
                
                val = (func(x_pp) - func(x_pm) - func(x_mp) + func(x_mm)) / (4 * epsilon ** 2)
                hessian[i, j] = val
                hessian[j, i] = val
                
    return hessian

def main():
    engine = DESILikelihoodEngine()
    
    base_candidate = {
        "candidate_id": "cooper_s10_g63_32",
        "picard_number": 19,
        "complex_structure": [0.22742914757560284, -1.435738265137309, 0.9453496565018775],
        "t2_modulus_tau": 0.4998315525628445,
    }
    
    theta_map = candidate_to_spherical(base_candidate)
    logger.info(f"MAP point (Spherical): {theta_map}")
    
    func = lambda t: get_log_likelihood(t, engine, base_candidate)
    
    logger.info("Computing 4D Continuous Hessian (ignoring discrete picard_offset)...")
    
    # We only compute FIM for the first 4 continuous parameters
    theta_continuous = theta_map[:4]
    epsilons = [1e-3, 1e-3, 1e-3, 1e-3]
    
    # Custom hessian with variable epsilon
    n = 4
    hessian = np.zeros((n, n))
    f0 = func(theta_map)
    
    for i in range(n):
        for j in range(i, n):
            ei = epsilons[i]
            ej = epsilons[j]
            if i == j:
                x_fwd = theta_map.copy()
                x_bwd = theta_map.copy()
                x_fwd[i] += ei
                x_bwd[i] -= ei
                hessian[i, i] = (func(x_fwd) - 2 * f0 + func(x_bwd)) / (ei ** 2)
            else:
                x_pp = theta_map.copy()
                x_pm = theta_map.copy()
                x_mp = theta_map.copy()
                x_mm = theta_map.copy()
                
                x_pp[i] += ei
                x_pp[j] += ej
                
                x_pm[i] += ei
                x_pm[j] -= ej
                
                x_mp[i] -= ei
                x_mp[j] += ej
                
                x_mm[i] -= ei
                x_mm[j] -= ej
                
                val = (func(x_pp) - func(x_pm) - func(x_mp) + func(x_mm)) / (4 * ei * ej)
                hessian[i, j] = val
                hessian[j, i] = val
                
    fisher = -hessian
    
    logger.info("Fisher Information Matrix:")
    logger.info("\n" + str(fisher))
    
    # Covariance matrix is inverse of Fisher matrix
    try:
        cov = np.linalg.inv(fisher)
        logger.info("Covariance Matrix:")
        logger.info("\n" + str(cov))
        
        # Calculate parameter degeneracies (correlation matrix)
        stds = np.sqrt(np.diag(cov))
        corr = cov / np.outer(stds, stds)
        logger.info("Correlation Matrix:")
        logger.info("\n" + str(corr))
        
    except np.linalg.LinAlgError:
        logger.error("Fisher Matrix is singular! Cannot compute covariance.")
        cov = np.zeros_like(fisher)
        corr = np.zeros_like(fisher)
        stds = np.zeros(n)
        
    out_dir = os.path.join("outputs", "ws7")
    os.makedirs(out_dir, exist_ok=True)
    
    results = {
        "parameters": SPHER_PARAM_NAMES[:4],
        "MAP_point": theta_continuous.tolist(),
        "fisher_matrix": fisher.tolist(),
        "covariance_matrix": cov.tolist(),
        "correlation_matrix": corr.tolist(),
        "uncertainties": stds.tolist() if 'stds' in locals() else []
    }
    
    with open(os.path.join(out_dir, "fim_results.json"), "w") as f:
        json.dump(results, f, indent=2)
        
    logger.info("Done.")

if __name__ == "__main__":
    main()
