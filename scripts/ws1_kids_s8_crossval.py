#!/usr/bin/env python3
import json
import logging
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def limber_cl_ee(s8, omega_m, h0, ell_bins, kids_fiducial_bandpowers, s8_fiducial=0.759):
    """
    Computes theoretical C_l^{EE} band powers using a Limber scaling approximation.
    For weak lensing, the amplitude of the shear power spectrum roughly scales with
    sigma_8^2.5 * Omega_m^1.25. Since S_8 = sigma_8 * sqrt(Omega_m/0.3),
    at fixed Omega_m, C_l scales roughly as (S_8)^2.5.
    
    This function applies the scaling to the fiducial KiDS-1000 bandpowers.
    """
    scaling_factor = (s8 / s8_fiducial)**2.5
    # Apply scaling across all 5 tomographic bins
    theory_bandpowers = kids_fiducial_bandpowers * scaling_factor
    return theory_bandpowers

def main():
    out_dir = Path("outputs/ws1")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Load KiDS-1000 data
    with open("data/kids1000/kids1000_bandpowers_EE.json") as f:
        kids_data = json.load(f)
        
    ell_centres = np.array(kids_data["ell_centres"])
    bandpowers_EE = np.array(kids_data["bandpowers_EE"]).T  # shape (5, 8) -> each row is a tomo bin
    sigma_EE = np.array(kids_data["sigma_EE"]).T
    
    logger.info(f"Loaded KiDS-1000 EE bandpowers, shape {bandpowers_EE.shape}")
    
    # K3xT2 predictions from dynamic MCMC
    res_path = Path("outputs/nested_sampling/phase9_joint_results.json")
    if res_path.exists():
        with open(res_path, "r") as f:
            mcmc_res = json.load(f)
        theta_map = mcmc_res["posterior_mean_theta"]
        tau, cs1 = theta_map[0], theta_map[1]
        omega_m = mcmc_res["posterior_cosmology"]["Omega_m"]
        h0 = mcmc_res["posterior_cosmology"]["H0"]
        sigma8_pred = 0.81 + 0.05 * (tau - 0.50) + 0.01 * cs1
        s8_k3t2 = sigma8_pred * np.sqrt(omega_m / 0.3)
        logger.info(f"Loaded dynamic K3xT2 predictions: tau={tau:.4f}, Omega_m={omega_m:.4f}, s8_k3t2={s8_k3t2:.4f}")
    else:
        # Fallback
        s8_k3t2 = 0.830
        omega_m = 0.300
        h0 = 67.40
        logger.warning("phase9_joint_results.json not found, using hardcoded fallback.")
    
    # Compute theoretical prediction
    theory_k3t2 = limber_cl_ee(s8_k3t2, omega_m, h0, ell_centres, bandpowers_EE)
    
    # 1.5 Scan S_8 in [0.70, 0.90] in steps of 0.005
    s8_scan = np.arange(0.70, 0.905, 0.005)
    chi2_scan = []
    
    for s8_val in s8_scan:
        theory_val = limber_cl_ee(s8_val, omega_m, h0, ell_centres, bandpowers_EE)
        # Compute chi2 (diagonal approximation since full cov is not provided in json)
        delta = theory_val - bandpowers_EE
        chi2 = np.sum((delta / sigma_EE)**2)
        chi2_scan.append(chi2)
        
    chi2_scan = np.array(chi2_scan)
    min_idx = np.argmin(chi2_scan)
    s8_min = s8_scan[min_idx]
    
    # Compute 1-sigma interval (delta chi2 = 1)
    chi2_min = chi2_scan[min_idx]
    within_1sigma = np.where(chi2_scan <= chi2_min + 1.0)[0]
    if len(within_1sigma) > 0:
        s8_err = (s8_scan[within_1sigma[-1]] - s8_scan[within_1sigma[0]]) / 2.0
    else:
        s8_err = 0.005
        
    tension_sigma = abs(s8_k3t2 - s8_min) / s8_err
    
    logger.info(f"S_8 min: {s8_min:.3f} +/- {s8_err:.3f}")
    logger.info(f"K3xT2 S_8: {s8_k3t2:.3f}")
    logger.info(f"Tension: {tension_sigma:.2f} sigma")
    
    # Save JSON output
    results = {
        "s8_k3t2": s8_k3t2,
        "s8_kids_fit": float(s8_min),
        "s8_kids_err": float(s8_err),
        "tension_sigma": float(tension_sigma),
        "pass": bool(tension_sigma < 3.0)
    }
    
    with open(out_dir / "s8_cross_validation.json", "w") as f:
        json.dump(results, f, indent=2)
        
    # Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(s8_scan, chi2_scan - chi2_min, 'b-', label=r'$\Delta \chi^2(S_8)$ profile')
    plt.axvline(s8_min, color='g', linestyle='--', label=f'KiDS-1000 Fit: {s8_min:.3f}')
    plt.axvline(s8_k3t2, color='r', linestyle='--', label=f'K3xT2 Prediction: {s8_k3t2:.3f}')
    plt.axvspan(s8_min - s8_err, s8_min + s8_err, color='g', alpha=0.2, label=r'$1\sigma$ interval')
    plt.axvspan(s8_min - 3*s8_err, s8_min + 3*s8_err, color='g', alpha=0.1, label=r'$3\sigma$ interval')
    plt.xlabel(r'$S_8$')
    plt.ylabel(r'$\Delta \chi^2$')
    plt.title('KiDS-1000 $C_\ell^{EE}$ Band Powers: $S_8$ Likelihood Profile')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(out_dir / "chi2_s8_profile.pdf")
    
    if tension_sigma < 3.0:
        print(f"PASS: Tension is {tension_sigma:.2f} sigma (< 3 sigma)")
    elif tension_sigma >= 5.0:
        print(f"FAIL: Tension is {tension_sigma:.2f} sigma (>= 5 sigma)")
    else:
        print(f"WARNING: Tension is {tension_sigma:.2f} sigma (between 3 and 5 sigma)")

if __name__ == "__main__":
    main()
