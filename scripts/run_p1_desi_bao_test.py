#!/usr/bin/env python3
"""
P1 Test 2: DESI BAO Redshift Evolution χ² Test
================================================
Computes the chi-squared of the K3×T² MAP cosmology (w0=-0.99992, Ωm=0.300,
H0=67.40) against the full DESI 2024 BAO dataset (12 measurements, 7 redshift
bins) using the published covariance matrix.

Compares against plain ΛCDM (w=-1) and reports per-bin residuals to identify
whether the DESI w0waCDM hint at z>1.3 is accommodated or contradicted.
"""

import numpy as np
import json
import os
from pathlib import Path

DATA_DIR = Path(os.path.dirname(__file__)).parent / "data" / "desi_dr1"


def load_desi_data():
    """Load DESI 2024 BAO measurements and covariance."""
    mean_file = DATA_DIR / "desi_2024_gaussian_bao_ALL_GCcomb_mean.txt"
    cov_file = DATA_DIR / "desi_2024_gaussian_bao_ALL_GCcomb_cov.txt"

    redshifts, observables, obs_types = [], [], []
    with open(mean_file) as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            parts = line.split()
            redshifts.append(float(parts[0]))
            observables.append(float(parts[1]))
            obs_types.append(parts[2])

    cov = np.loadtxt(cov_file)
    return np.array(redshifts), np.array(observables), obs_types, cov


def friedmann_Ez(z, Omega_m, w0, wa=0.0):
    """E(z) = H(z)/H0 for flat w0waCDM."""
    Omega_de = 1.0 - Omega_m
    a = 1.0 / (1.0 + z)
    de_term = Omega_de * a**(-3*(1+w0+wa)) * np.exp(-3*wa*(1-a))
    return np.sqrt(Omega_m * (1+z)**3 + de_term)


def compute_distances(z, Omega_m, H0, w0, wa=0.0):
    """Compute D_M, D_H, D_V at redshift z."""
    c = 299792.458  # km/s
    r_s = 147.05     # Mpc (Planck 2018)

    # Numerical integration for comoving distance
    n_steps = 2000
    z_arr = np.linspace(0, z, n_steps + 1)
    E_arr = friedmann_Ez(z_arr, Omega_m, w0, wa)
    D_M = (c / H0) * np.trapz(1.0 / E_arr, z_arr)

    # Hubble distance
    E_at_z = friedmann_Ez(z, Omega_m, w0, wa)
    D_H = c / (H0 * E_at_z)

    # Volume-averaged distance
    D_V = (z * D_M**2 * D_H) ** (1.0/3.0)

    return {
        "DM_over_rs": D_M / r_s,
        "DH_over_rs": D_H / r_s,
        "DV_over_rs": D_V / r_s,
    }


def compute_chi2(Omega_m, H0, w0, wa=0.0):
    """Compute χ² against DESI data."""
    redshifts, observables, obs_types, cov = load_desi_data()

    theory = []
    for z, ot in zip(redshifts, obs_types):
        dists = compute_distances(z, Omega_m, H0, w0, wa)
        theory.append(dists[ot])
    theory = np.array(theory)

    residuals = observables - theory
    cov_inv = np.linalg.inv(cov)
    chi2 = float(residuals @ cov_inv @ residuals)

    return chi2, residuals, theory


def main():
    print("=" * 70)
    print("  P1 Test 2: DESI BAO Redshift Evolution χ² Test")
    print("=" * 70)

    redshifts, observables, obs_types, cov = load_desi_data()
    n_data = len(observables)
    sigmas = np.sqrt(np.diag(cov))

    # --- Model 1: K3×T² MAP cosmology ---
    chi2_k3t2, res_k3t2, theory_k3t2 = compute_chi2(
        Omega_m=0.300, H0=67.40, w0=-0.99992
    )

    # --- Model 2: Plain ΛCDM (w=-1 exactly) ---
    chi2_lcdm, res_lcdm, theory_lcdm = compute_chi2(
        Omega_m=0.315, H0=67.36, w0=-1.0  # Planck 2018 bestfit
    )

    # --- Model 3: w0waCDM (DESI 2024 bestfit) ---
    chi2_w0wa, res_w0wa, theory_w0wa = compute_chi2(
        Omega_m=0.295, H0=67.97, w0=-0.55, wa=-1.32  # DESI+CMB+SN bestfit
    )

    # --- Report ---
    print(f"\nDataset: DESI 2024 BAO ({n_data} measurements, 7 redshift bins)")
    print(f"\n{'Model':<25s} | {'χ²':>8s} | {'χ²/dof':>8s} | {'Δχ² vs ΛCDM':>12s}")
    print("-" * 60)

    models = [
        ("K3×T² (w0=-0.99992)", chi2_k3t2, 3),
        ("ΛCDM (w=-1)", chi2_lcdm, 2),
        ("w0waCDM (DESI bestfit)", chi2_w0wa, 4),
    ]

    for name, chi2, n_params in models:
        dof = n_data - n_params
        delta = chi2 - chi2_lcdm
        print(f"  {name:<23s} | {chi2:8.3f} | {chi2/dof:8.3f} | {delta:+12.3f}")

    # Per-bin residuals for K3×T²
    print(f"\n--- Per-bin residuals (K3×T² MAP) ---")
    print(f"{'z':>6s} | {'Observable':>12s} | {'Data':>10s} | {'Theory':>10s} | {'Residual':>10s} | {'Pull (σ)':>10s}")
    print("-" * 70)
    for i in range(n_data):
        pull = res_k3t2[i] / sigmas[i]
        print(f"  {redshifts[i]:5.3f} | {obs_types[i]:>12s} | {observables[i]:10.4f} | {theory_k3t2[i]:10.4f} | {res_k3t2[i]:+10.4f} | {pull:+10.3f}")

    # Diagnostic: high-z anomaly
    high_z_mask = redshifts > 1.3
    chi2_highz_k3t2 = float(res_k3t2[high_z_mask] @ np.linalg.inv(cov[np.ix_(high_z_mask, high_z_mask)]) @ res_k3t2[high_z_mask])
    chi2_highz_lcdm = float(res_lcdm[high_z_mask] @ np.linalg.inv(cov[np.ix_(high_z_mask, high_z_mask)]) @ res_lcdm[high_z_mask])

    print(f"\n--- High-z diagnostic (z > 1.3, {np.sum(high_z_mask)} bins) ---")
    print(f"  K3×T² χ²(z>1.3): {chi2_highz_k3t2:.3f}")
    print(f"  ΛCDM  χ²(z>1.3): {chi2_highz_lcdm:.3f}")
    print(f"  Δχ²:             {chi2_highz_k3t2 - chi2_highz_lcdm:+.3f}")

    # Save results
    os.makedirs("outputs/phase8", exist_ok=True)
    results = {
        "test": "DESI BAO Redshift Evolution χ² Test",
        "n_data": n_data,
        "models": {
            "K3xT2": {"chi2": chi2_k3t2, "n_params": 3, "chi2_per_dof": chi2_k3t2/(n_data-3)},
            "LCDM": {"chi2": chi2_lcdm, "n_params": 2, "chi2_per_dof": chi2_lcdm/(n_data-2)},
            "w0waCDM": {"chi2": chi2_w0wa, "n_params": 4, "chi2_per_dof": chi2_w0wa/(n_data-4)},
        },
        "delta_chi2_k3t2_vs_lcdm": chi2_k3t2 - chi2_lcdm,
        "high_z_diagnostic": {
            "chi2_k3t2_z_gt_1.3": chi2_highz_k3t2,
            "chi2_lcdm_z_gt_1.3": chi2_highz_lcdm,
        },
        "per_bin_pulls_k3t2": [float(res_k3t2[i]/sigmas[i]) for i in range(n_data)],
    }
    with open("outputs/phase8/desi_bao_chi2_test.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to outputs/phase8/desi_bao_chi2_test.json")


if __name__ == "__main__":
    main()
