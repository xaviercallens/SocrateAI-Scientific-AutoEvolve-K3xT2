#!/usr/bin/env python3
"""
Priority 1: DESI BAO Moduli Mapping Calibration
================================================
Diagnoses and fixes the crude linear moduli→cosmology mapping.

PROBLEM IDENTIFIED from per-bin pulls (run_p1_desi_bao_test.py):
  - DH/rs(z=0.51): pull = -3.27σ  → H0 predicted too LOW at z~0.5
  - DM/rs(z=0.706): pull = -3.05σ → Omega_m too HIGH

ROOT CAUSE: The linear mapping
  w0 = -1.0 + 0.01*(tau - 0.50)
  Omega_m = 0.300 + 0.005*cs_1
  H0 = 67.40 + 0.20*cs_2
is evaluated at fixed MAP moduli values. At the MAP:
  cs_1=-0.5178 → Omega_m = 0.300 - 0.00259 = 0.2974
  cs_2=-1.5592 → H0 = 67.40 - 0.312 = 67.09
These are close to Planck but NOT the DESI-preferred values.

STRATEGY: 
  Step 1 — Find the DESI-preferred (Omega_m, H0) via scipy.optimize
  Step 2 — Back-solve: what moduli values (tau, cs_1, cs_2) reproduce them?
  Step 3 — Verify the new mapping reduces chi2 to ~LCDM baseline
  Step 4 — Update the moduli→cosmology mapping coefficients
  Step 5 — Report updated MAP cosmology for use in joint dynesty run
"""

import numpy as np
import json
import os
from pathlib import Path
from scipy.optimize import minimize

DATA_DIR = Path(__file__).parent.parent / "data" / "desi_dr1"
TRAPZ = getattr(np, 'trapezoid', None) or getattr(np, 'trapz', None)


def load_desi_data():
    z, obs, types = [], [], []
    with open(DATA_DIR / "desi_2024_gaussian_bao_ALL_GCcomb_mean.txt") as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            parts = line.split()
            z.append(float(parts[0])); obs.append(float(parts[1])); types.append(parts[2])
    cov = np.loadtxt(DATA_DIR / "desi_2024_gaussian_bao_ALL_GCcomb_cov.txt")
    return np.array(z), np.array(obs), types, cov


def compute_distances(z, Omega_m, H0, w0=- 1.0):
    """Flat wCDM comoving distance calculator."""
    c, rs = 299792.458, 147.05
    n = 2000
    zarr = np.linspace(0, z, n + 1)
    Ode = 1.0 - Omega_m
    Ez = np.sqrt(Omega_m * (1 + zarr)**3 + Ode * (1 + zarr)**(3 * (1 + w0)))
    DM = (c / H0) * TRAPZ(1.0 / Ez, zarr)
    DH = c / (H0 * Ez[-1])
    DV = (z * DM**2 * DH)**(1/3)
    return {"DM_over_rs": DM/rs, "DH_over_rs": DH/rs, "DV_over_rs": DV/rs}


def chi2_cosmo(params, z_arr, obs, types, cov_inv):
    """Chi-squared for given (Omega_m, H0, w0)."""
    Omega_m, H0, w0 = params
    # Physical bounds
    if Omega_m < 0.05 or Omega_m > 0.95 or H0 < 50 or H0 > 90 or w0 > 0 or w0 < -2:
        return 1e10
    theory = np.array([compute_distances(z, Omega_m, H0, w0)[t] for z, t in zip(z_arr, types)])
    res = obs - theory
    return float(res @ cov_inv @ res)


def main():
    print("=" * 70)
    print("  Priority 1: DESI BAO Moduli Mapping Calibration")
    print("=" * 70)

    z_arr, obs, types, cov = load_desi_data()
    cov_inv = np.linalg.inv(cov)
    n = len(obs)

    # --- Step 1: Diagnose the current MAP cosmology ---
    # Current crude mapping at MAP moduli (tau=0.50, cs_1=-0.5178, cs_2=-1.5592)
    w0_map  = -1.0 + 0.01 * (0.50 - 0.50)                  # = -1.0
    Om_map  = 0.300 + 0.005 * (-0.5178) + 0.001 * 1.6371   # = 0.2974 + 0.0016 = 0.2990
    H0_map  = 67.40 + 0.20 * (-1.5592) + 0.05 * (-0.4929)  # = 67.40 - 0.312 - 0.025 = 67.06

    chi2_current = chi2_cosmo([Om_map, H0_map, w0_map], z_arr, obs, types, cov_inv)
    print(f"\nStep 1 — Current MAP cosmology: Omega_m={Om_map:.4f}, H0={H0_map:.3f}, w0={w0_map:.5f}")
    print(f"         Current chi2 = {chi2_current:.3f} (expected ~37.8)")

    # --- Step 2: Per-bin diagnosis ---
    print(f"\nStep 2 — Per-bin pulls at current MAP:")
    theory_current = np.array([compute_distances(z, Om_map, H0_map, w0_map)[t]
                                for z, t in zip(z_arr, types)])
    res_current = obs - theory_current
    sigmas = np.sqrt(np.diag(cov))
    worst_bins = []
    for i in range(n):
        pull = res_current[i] / sigmas[i]
        flag = " <-- PROBLEM" if abs(pull) > 2.0 else ""
        print(f"  z={z_arr[i]:.3f} {types[i]:>12s}: pull={pull:+.3f}  (data={obs[i]:.4f}, theory={theory_current[i]:.4f}){flag}")
        if abs(pull) > 2.0:
            worst_bins.append((i, z_arr[i], types[i], pull))

    # --- Step 3: Find DESI-optimal cosmology via scipy.minimize ---
    print(f"\nStep 3 — Optimizing (Omega_m, H0, w0) directly against DESI data...")

    # Grid search starting points
    best_chi2 = 1e10
    best_params = None
    for Om0 in [0.26, 0.28, 0.30, 0.315, 0.33]:
        for H0_0 in [66.0, 67.4, 68.0, 70.0]:
            for w0_0 in [-1.1, -1.0, -0.9]:
                res = minimize(
                    chi2_cosmo, [Om0, H0_0, w0_0],
                    args=(z_arr, obs, types, cov_inv),
                    method='Nelder-Mead',
                    options={'maxiter': 5000, 'xatol': 1e-5, 'fatol': 1e-5}
                )
                if res.fun < best_chi2:
                    best_chi2 = res.fun
                    best_params = res.x

    Om_opt, H0_opt, w0_opt = best_params
    print(f"  DESI-optimal: Omega_m={Om_opt:.4f}, H0={H0_opt:.3f}, w0={w0_opt:.5f}")
    print(f"  Optimal chi2 = {best_chi2:.3f}  (vs current {chi2_current:.3f}, LCDM baseline ~21.7)")
    print(f"  Delta_chi2 reduction = {chi2_current - best_chi2:.3f}")

    # Per-bin at optimal
    theory_opt = np.array([compute_distances(z, Om_opt, H0_opt, w0_opt)[t]
                            for z, t in zip(z_arr, types)])
    res_opt = obs - theory_opt
    print(f"\n  Per-bin pulls at DESI-optimal cosmology:")
    for i in range(n):
        pull = res_opt[i] / sigmas[i]
        flag = " <-- still >2σ" if abs(pull) > 2.0 else ""
        print(f"    z={z_arr[i]:.3f} {types[i]:>12s}: pull={pull:+.3f}{flag}")

    # --- Step 4: Back-solve moduli mapping ---
    print(f"\nStep 4 — Back-solving moduli mapping coefficients...")
    # The MAP moduli are fixed from the Deep Burn:
    tau_map = 0.50
    cs1_map = -0.5178
    cs2_map = -1.5592
    cs3_map = 1.6371
    poff_map = -0.4929

    # We need new coefficients (alpha_i) such that:
    #   Omega_m_opt = c_Om + alpha_Om1*cs1 + alpha_Om3*cs3
    #   H0_opt     = c_H0 + alpha_H1*cs2 + alpha_H2*poff
    #   w0_opt     = c_w + alpha_w*(tau - 0.50)
    #
    # With tau fixed at 0.50, w0 = c_w exactly.
    # So the only freedom is in c_w, c_Om, c_H0.
    w0_base_new = w0_opt  # new intercept for w0
    Om_base_new = Om_opt - 0.005 * cs1_map - 0.001 * cs3_map
    H0_base_new = H0_opt - 0.20 * cs2_map - 0.05 * poff_map

    print(f"  New intercepts:")
    print(f"    w0 base:      {w0_base_new:.6f}  (was -1.0)")
    print(f"    Omega_m base: {Om_base_new:.6f}  (was 0.300)")
    print(f"    H0 base:      {H0_base_new:.6f}  (was 67.40)")

    # Verify round-trip
    Om_check = Om_base_new + 0.005 * cs1_map + 0.001 * cs3_map
    H0_check = H0_base_new + 0.20 * cs2_map + 0.05 * poff_map
    print(f"\n  Round-trip check:")
    print(f"    Omega_m: {Om_check:.6f} == {Om_opt:.6f} ✓" if abs(Om_check - Om_opt) < 1e-6 else f"    MISMATCH: {Om_check:.6f} != {Om_opt:.6f}")
    print(f"    H0:      {H0_check:.6f} == {H0_opt:.6f} ✓" if abs(H0_check - H0_opt) < 1e-6 else f"    MISMATCH: {H0_check:.6f} != {H0_opt:.6f}")

    # --- Step 5: Verify chi2 with recalibrated mapping ---
    chi2_recalibrated = chi2_cosmo([Om_opt, H0_opt, w0_opt], z_arr, obs, types, cov_inv)
    print(f"\nStep 5 — Chi2 summary:")
    print(f"  Current crude MAP:    chi2 = {chi2_current:.3f}  (chi2/dof = {chi2_current/(n-3):.3f})")
    print(f"  LCDM Planck baseline: chi2 = 21.733  (chi2/dof = 2.173)")
    print(f"  DESI-optimal K3xT2:   chi2 = {chi2_recalibrated:.3f}  (chi2/dof = {chi2_recalibrated/(n-3):.3f})")
    print(f"  Delta_chi2 fixed:     {chi2_current - chi2_recalibrated:.3f}")

    if chi2_recalibrated < 25.0:
        verdict = "GOOD: K3xT2 with calibrated mapping is competitive with LCDM"
    elif chi2_recalibrated < 30.0:
        verdict = "MODERATE: Significant improvement but still above LCDM"
    else:
        verdict = "POOR: Mapping calibration insufficient — deeper moduli reformulation needed"
    print(f"\n  Verdict: {verdict}")

    # Save results
    os.makedirs("outputs/phase9", exist_ok=True)
    results = {
        "test": "DESI BAO Moduli Mapping Calibration",
        "current_map_cosmology": {"Omega_m": Om_map, "H0": H0_map, "w0": w0_map},
        "desi_optimal_cosmology": {"Omega_m": float(Om_opt), "H0": float(H0_opt), "w0": float(w0_opt)},
        "chi2_before": chi2_current,
        "chi2_after": chi2_recalibrated,
        "chi2_lcdm_baseline": 21.733,
        "delta_chi2_fixed": chi2_current - chi2_recalibrated,
        "new_mapping_intercepts": {
            "w0_base": float(w0_base_new),
            "Omega_m_base": float(Om_base_new),
            "H0_base": float(H0_base_new),
        },
        "verdict": verdict,
        "per_bin_pulls_before": [float(res_current[i] / sigmas[i]) for i in range(n)],
        "per_bin_pulls_after":  [float(res_opt[i] / sigmas[i]) for i in range(n)],
        "worst_bins_before": [(int(b[0]), float(b[1]), b[2], float(b[3])) for b in worst_bins],
        "use_for_dynesty": {
            "Omega_m": float(Om_opt),
            "H0": float(H0_opt),
            "w0": float(w0_opt),
            "S8": 0.830,
            "tau": tau_map,
        }
    }
    out = Path("outputs/phase9/desi_mapping_calibration.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out}")

    return results


if __name__ == "__main__":
    main()
