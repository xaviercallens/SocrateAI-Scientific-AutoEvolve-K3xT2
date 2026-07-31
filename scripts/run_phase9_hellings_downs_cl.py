#!/usr/bin/env python3
"""
Phase 9 Task 4: Hellings-Downs C_l Decomposition
=================================================
Decomposes the standard Hellings-Downs GWB angular correlation
into Legendre (spherical harmonic) moments C_l, and compares
the l=4 ratio against the Oligon hexadecapole prediction (16.07).
"""
import numpy as np
import json
import os
from scipy.special import eval_legendre

def hellings_downs(zeta):
    """Standard Hellings-Downs angular correlation function."""
    x = 0.5 * (1.0 - np.cos(zeta))
    # Avoid log(0)
    x = np.where(x < 1e-12, 1e-12, x)
    hd = 0.5 * (3 * x * np.log(x) - x / 2 + 1.0 / 2)
    return hd

def main():
    print("=" * 70)
    print("  Phase 9 Task 4: Hellings-Downs C_l Decomposition")
    print("=" * 70)

    # Dense angular grid (avoid exact 0 and pi)
    zeta = np.linspace(1e-5, np.pi - 1e-5, 8000)
    hd = hellings_downs(zeta)

    # Normalise to Gamma(pi/2) = 0 convention (standard PTA)
    # Actually normalise so max=1 for ratio comparison
    hd_norm = hd / np.max(np.abs(hd))

    # Isotropic baseline: Gamma = 1 everywhere
    hd_iso = np.ones_like(zeta)

    print(f"\nComputing Legendre moments C_l for l=0..9...")
    C_l = {}
    C_l_iso = {}
    for l in range(10):
        Pl = eval_legendre(l, np.cos(zeta))
        # C_l = (2l+1)/2 * integral Gamma(zeta) P_l(cos zeta) sin(zeta) dzeta
        integrand = hd_norm * Pl * np.sin(zeta)
        integrand_iso = hd_iso * Pl * np.sin(zeta)
        C_l[l] = float((2 * l + 1) / 2 * np.trapezoid(integrand, zeta))
        C_l_iso[l] = float((2 * l + 1) / 2 * np.trapezoid(integrand_iso, zeta))
        print(f"  l={l}: C_l(HD) = {C_l[l]:+.6f}  |  C_l(Iso) = {C_l_iso[l]:+.6f}")

    # l=4 ratio
    prediction = 16.07
    if abs(C_l_iso[4]) > 1e-10:
        l4_ratio = C_l[4] / C_l_iso[4]
    else:
        l4_ratio = float('nan')

    tension_pct = abs(l4_ratio - prediction) / abs(prediction) * 100

    print(f"\n--- l=4 Hexadecapole Analysis ---")
    print(f"  C_l(HD, l=4):       {C_l[4]:.6f}")
    print(f"  C_l(Iso, l=4):      {C_l_iso[4]:.6f}")
    print(f"  Ratio measured:     {l4_ratio:.4f}")
    print(f"  Oligon prediction:  {prediction}")
    print(f"  Tension:            {tension_pct:.1f}%")

    if tension_pct < 10:
        verdict = "consistent with Oligon prediction"
    elif tension_pct < 50:
        verdict = f"moderate tension at {tension_pct:.0f}%"
    else:
        verdict = f"significant tension at {tension_pct:.0f}% — HD curve does not support l=4 excess"

    print(f"  Verdict:            {verdict}")

    # Physical interpretation
    print(f"\n--- Physical interpretation ---")
    print(f"  The Hellings-Downs curve is the isotropic GWB correlation.")
    print(f"  Its C_l spectrum is dominated by low multipoles (l=0,1,2).")
    print(f"  If C_l(l=4)/C_l_iso(l=4) >> 1 were measured in NANOGrav data,")
    print(f"  it would indicate excess anisotropy at the hexadecapole scale.")
    print(f"  The Oligon prediction of 16.07 must be tested against residuals")
    print(f"  of the NANOGrav 15yr inter-pulsar correlations beyond the HD template.")

    os.makedirs("outputs/phase9", exist_ok=True)
    results = {
        "test": "Hellings-Downs C_l Decomposition vs Oligon Hexadecapole",
        "cl_spectrum": {str(l): C_l[l] for l in range(10)},
        "cl_isotropic": {str(l): C_l_iso[l] for l in range(10)},
        "l4_ratio_measured": l4_ratio,
        "l4_ratio_predicted": prediction,
        "tension_percent": tension_pct,
        "verdict": verdict,
        "note": (
            "The l=4 ratio from the Hellings-Downs TEMPLATE differs from the "
            "Oligon prediction. A definitive test requires decomposing the "
            "RESIDUAL inter-pulsar correlation BEYOND the HD template from "
            "real NANOGrav 15yr pulsar timing data."
        )
    }
    with open("outputs/phase9/hellings_downs_cl_analysis.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to outputs/phase9/hellings_downs_cl_analysis.json")


if __name__ == "__main__":
    main()
