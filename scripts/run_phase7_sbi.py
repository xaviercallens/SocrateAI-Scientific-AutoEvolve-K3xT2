#!/usr/bin/env python3
"""
Phase 7: SBI (Normalizing Flows) Posterior Characterization
===========================================================
Replaces traditional MCMC with Simulation-Based Inference (SBI)
using Masked Autoregressive Flows (MAF) to rapidly estimate the 
posterior over K3xT2 moduli from DESI BAO observables.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

import torch
import numpy as np

# Ensure src/ is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from alpha_evolve.phenotype_mapper import map_k3_to_cosmology

# Try importing SBI
try:
    from sbi.inference import SNPE, simulate_for_sbi
    from sbi.neural_nets import posterior_nn
    from sbi import utils as sbi_utils
except ImportError:
    print("Error: sbi package not found. Run 'pip install sbi torch'.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("outputs/mcmc/phase7_sbi.log", mode='w'),
    ]
)
logger = logging.getLogger(__name__)

def build_simulator():
    """
    Returns a forward simulator function for SBI.
    Input theta: [tau_T2, re_tau_K3, im_tau_K3, rho_K3, delta_P]
    Output x: [w0, omega_m, h0] (the cosmological observables)
    """
    def simulator(theta: torch.Tensor) -> torch.Tensor:
        # SBI passes batches, but for simplicity we simulate one by one
        # if the input is a batch, we iterate
        if theta.ndim > 1:
            results = []
            for t in theta:
                results.append(simulator(t))
            return torch.stack(results)
        
        # Convert theta to candidate dict
        t = theta.numpy()
        candidate = {
            "candidate_id": "sbi_sample",
            "t2_modulus_tau": float(t[0]),
            "complex_structure": [float(t[1]), float(t[2]), float(t[4])], # TASK-10/B7: removed hardcoded 0.96 bias
            "picard_number": int(round(float(t[3]))),
            "moduli_stabilization": 0.0, # Not used in map_k3_to_cosmology directly
        }
        
        # Map to cosmology
        cosmology = map_k3_to_cosmology(candidate)
        
        # We extract w0, omega_m, h0
        return torch.tensor([
            cosmology.get("w0", -1.0),
            cosmology.get("omega_m", 0.3),
            cosmology.get("h0", 67.4)
        ], dtype=torch.float32)
        
    return simulator

def generate_sbi_corner_plot(samples: np.ndarray, output_path: str):
    """Generate a corner plot from SBI samples."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    
    n_params = samples.shape[1]
    fig, axes = plt.subplots(n_params, n_params, figsize=(10, 10))
    labels = [r"$\tau_{T^2}$", r"$cs_1$", 
              r"$cs_2$", r"$\rho_{K3}$", r"$cs_3$"]
    
    for i in range(n_params):
        for j in range(n_params):
            ax = axes[i, j]
            if j > i:
                ax.set_visible(False)
                continue
            if i == j:
                ax.hist(samples[:, i], bins=50, density=True, color='#a78bfa', alpha=0.7)
            else:
                ax.scatter(samples[:, j], samples[:, i], s=1, alpha=0.1, color='#00f0ff')
                
            if i == n_params - 1:
                ax.set_xlabel(labels[j])
            if j == 0 and i > 0:
                ax.set_ylabel(labels[i])
                
    fig.suptitle("SBI Posterior: Normalizing Flow (MAF)", fontsize=16)
    plt.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)
    logger.info(f"SBI Corner plot saved to {output_path}")

def main():
    start_time = time.time()
    
    logger.info("=======================================================")
    logger.info("  Phase 7b: Simulation-Based Inference (Normalizing Flows)")
    logger.info("=======================================================")
    
    Path("outputs/mcmc").mkdir(parents=True, exist_ok=True)
    Path("paper/figures").mkdir(parents=True, exist_ok=True)
    
    # 1. Define the Uniform Prior over the K3xT2 moduli space
    # Bounds: [tau_T2, re_tau_K3, im_tau_K3, rho_K3, delta_P]
    prior_min = [0.4, -2.0, 0.1, 10.0, 0.5]
    prior_max = [0.6, 2.0, 2.0, 20.0, 1.0]
    prior = sbi_utils.BoxUniform(low=torch.tensor(prior_min), 
                                 high=torch.tensor(prior_max))
    
    # 2. Setup the simulator
    simulator = build_simulator()
    
    # 4. Generate training data from the forward model
    num_simulations = 100000  # AUDIT FIX (TASK 12-03): Scaled from 2k to 100k for 5D convergence
    logger.info(f"Running {num_simulations} forward simulations...")
    theta, x = simulate_for_sbi(simulator, proposal=prior, num_simulations=num_simulations)
    
    # 5 & 6. Train the Normalizing Flow (MAF) or Load Pretrained
    pretrained_path = Path("models/pretrained/sbi_posterior.pt")
    
    if pretrained_path.exists():
        logger.info(f"📥 Loading pretrained Neural Posterior from {pretrained_path}...")
        try:
            # Note: For production with `sbi`, it's safer to load state_dicts, 
            # but for demonstration we use torch.load
            posterior = torch.load(pretrained_path, weights_only=False)
            logger.info("✅ Pretrained Posterior loaded successfully.")
        except Exception as e:
            logger.error(f"⚠️ Failed to load pretrained posterior: {e}")
            posterior = None
    else:
        posterior = None
        
    if posterior is None:
        logger.info("Training the Masked Autoregressive Flow (MAF) neural density estimator...")
        density_estimator_build = posterior_nn(model='maf', hidden_features=50, num_transforms=5)
        inference = SNPE(prior=prior, density_estimator=density_estimator_build)
        inference = inference.append_simulations(theta, x)
        density_estimator = inference.train()
        
        # Build the posterior
        posterior = inference.build_posterior(density_estimator)
        
        # Save for future use
        pretrained_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(posterior, pretrained_path)
        logger.info(f"💾 Neural Posterior saved to: {pretrained_path}")
    
    # 7. Perform Inference on the actual DESI 2024 observations
    # Observables: [w0=-0.974, omega_m=0.295, h0=69.3]
    x_obs = torch.tensor([-0.974, 0.295, 69.3])
    logger.info(f"Target Observations (DESI/Planck): {x_obs.numpy()}")
    
    logger.info("Sampling 10,000 points from the neural posterior...")
    samples = posterior.sample((10000,), x=x_obs)
    samples_np = samples.numpy()
    
    elapsed = time.time() - start_time
    logger.info(f"SBI Pipeline completed in {elapsed:.1f}s")
    
    # 8. Post-processing and Plotting
    means = np.mean(samples_np, axis=0)
    stds = np.std(samples_np, axis=0)
    
    logger.info("=======================================================")
    logger.info("  SBI NEURAL POSTERIOR SUMMARY")
    logger.info("=======================================================")
    names = ["tau_T2", "Re_tau_K3", "Im_tau_K3", "rho_K3", "delta_P"]
    for i, name in enumerate(names):
        logger.info(f"  {name:15s}: {means[i]:.4f} ± {stds[i]:.4f}")
    
    generate_sbi_corner_plot(samples_np, "paper/figures/sbi_normalizing_flow_corner.pdf")
    logger.info("=======================================================")

if __name__ == "__main__":
    main()
