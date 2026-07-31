#!/usr/bin/env python3
"""
P2 Test 5: KiDS-1000 B-Mode Parity Violation Null Test
========================================================
Tests whether the real KiDS-1000 cosmic shear B-mode band powers
are consistent with zero (as expected in ΛCDM) or show evidence
of parity violation from topological defects (as predicted by the
K3×T² Oligon model).

Uses the actual measured bandpowers_BB from the published dataset.
See specs/experimentation_plan.md Experiment 3 for full protocol.
"""

import numpy as np
import json
import os
from pathlib import Path

DATA_DIR = Path(os.path.dirname(__file__)).parent / "data" / "euclid_q2"


def main():
    print("=" * 70)
    print("  P2 Test 5: KiDS-1000 B-Mode Parity Violation Null Test")
    print("=" * 70)

    with open(DATA_DIR / "kids1000_bandpowers_EE.json") as f:
        data = json.load(f)

    ell_centers = np.array(data["ell_centres"])
    bandpowers_EE = np.array(data["bandpowers_EE"])
    bandpowers_BB = np.array(data["bandpowers_BB"])
    sigma_EE = np.array(data["sigma_EE"])

    n_ell, n_tomo = bandpowers_EE.shape
    sigma_BB = sigma_EE  # Conservative estimate

    print(f"\nDataset: KiDS-1000 Band Powers")
    print(f"  {n_ell} ell-bins × {n_tomo} tomo bins = {n_ell * n_tomo} data points")

    # Global null test
    bb_flat = bandpowers_BB.flatten()
    sigma_flat = sigma_BB.flatten()
    chi2_null = float(np.sum((bb_flat / sigma_flat) ** 2))
    n_dof = len(bb_flat)
    chi2_per_dof = chi2_null / n_dof

    print(f"\n--- Global B-mode null test ---")
    print(f"  χ²(BB = 0): {chi2_null:.3f}")
    print(f"  d.o.f.:     {n_dof}")
    print(f"  χ²/dof:     {chi2_per_dof:.3f}")

    try:
        from scipy.stats import chi2 as chi2_dist
        p_value = float(chi2_dist.sf(chi2_null, n_dof))
        print(f"  p-value:    {p_value:.4f}")
    except ImportError:
        p_value = None

    if chi2_per_dof < 1.5:
        verdict = "CONSISTENT WITH ZERO: No evidence for B-mode parity violation."
    elif chi2_per_dof < 2.0:
        verdict = "MARGINAL: Mild excess B-mode power."
    else:
        verdict = "SIGNIFICANT: B-mode excess detected."
    print(f"  Verdict:    {verdict}")

    # Per-ell B/E ratio
    print(f"\n--- B/E Ratio per ell-bin ---")
    be_ratios = []
    for i in range(n_ell):
        mean_bb = np.mean(np.abs(bandpowers_BB[i]))
        mean_ee = np.mean(bandpowers_EE[i])
        ratio = mean_bb / mean_ee if mean_ee > 0 else 0
        be_ratios.append(float(ratio))
        print(f"  ell={ell_centers[i]:8.1f}: BB/EE = {ratio:.4f}")

    # Tomo correlation
    tomo_corr = np.corrcoef(bandpowers_BB.T).tolist()

    os.makedirs("outputs/phase8", exist_ok=True)
    results = {
        "test": "KiDS-1000 B-Mode Null Test",
        "chi2_null": chi2_null,
        "chi2_per_dof": chi2_per_dof,
        "p_value": p_value,
        "verdict": verdict,
        "be_ratios": be_ratios,
        "tomo_correlation": tomo_corr,
    }
    with open("outputs/phase8/kids_bmode_null_test.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to outputs/phase8/kids_bmode_null_test.json")


if __name__ == "__main__":
    main()
