#!/usr/bin/env python3
"""
Alignement Croisé Avancé 1 : Euclid Q1 Shear × Planck PR4 CMB Lensing
=======================================================================
Simulates the angular cross-power spectrum C_l^{κγ} between:
  - CMB lensing convergence κ (Planck PR4 NPIPE / ACT DR6)
  - Galaxy shear γ (Euclid Q1 MER ellipticities)

Tests whether the Weyl potential (Φ+Ψ)/2 is consistent with G_eff/G_N ≡ 1
(no unscreened scalar fifth force from Kähler stabilization).

Since we don't have the full Planck lensing map locally, we compute the
theoretical cross-spectrum and compare against the expected signal-to-noise
for the Euclid Q1 footprint (17.3 deg²).
"""

import json
import logging
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

OUT_DIR = Path("outputs/cross_alignments")
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR = Path("paper/figures")

def main():
    logger.info("=" * 70)
    logger.info("  Alignement Croisé Avancé 1: Euclid Q1 γ × Planck PR4 κ")
    logger.info("=" * 70)

    # Multipole range
    ell = np.arange(50, 2001)

    # Cosmological parameters (K3xT2 AZ1 P=18)
    Om = 0.315
    sigma8 = 0.812
    h = 0.693
    ns = 0.9636
    S8 = 0.8318

    # Theory: C_l^{κγ} ∝ (Ω_m H₀²/c²)² × ∫ W^κ(χ) W^γ(χ) P(k=l/χ, χ) dχ / χ²
    # Use Limber approximation with simplified amplitude scaling
    # Normalization to match Planck × DES Y3 detection (Omori et al. 2023)
    A_kg = 1.2e-8  # Typical amplitude at l=200

    # K3xT2: G_eff/G_N = 1 (no modification)
    Cl_kg_k3t2 = A_kg * (ell / 200.0)**(-1.2) * (S8 / 0.80)**3

    # Modified gravity scenario: G_eff/G_N = 1.05 (5% enhancement)
    S8_mg = S8 * 1.05**0.5
    Cl_kg_mg = A_kg * (ell / 200.0)**(-1.2) * (S8_mg / 0.80)**3

    # LCDM with Planck S8
    S8_planck = 0.832
    Cl_kg_lcdm = A_kg * (ell / 200.0)**(-1.2) * (S8_planck / 0.80)**3

    # Noise: shot noise from Euclid Q1 (17.3 deg², n_gal ~ 30/arcmin²)
    f_sky = 17.3 / 41253.0  # Fraction of sky
    n_gal_per_sr = 30 * (180/np.pi * 60)**2  # per steradian
    sigma_e = 0.26  # Shape noise per component
    Nl_kg = sigma_e**2 / n_gal_per_sr  # Shot noise contribution

    # Signal-to-noise per multipole bin
    delta_ell = 50
    snr_per_bin = []
    ell_bins = np.arange(100, 1500, delta_ell)
    for l_center in ell_bins:
        mask = (ell >= l_center - delta_ell/2) & (ell < l_center + delta_ell/2)
        if np.sum(mask) == 0:
            snr_per_bin.append(0)
            continue
        Cl_sig = np.mean(Cl_kg_k3t2[mask])
        Cl_noise = Nl_kg
        # Knox formula: σ(C_l) = sqrt(2/(2l+1)/f_sky/Δl) * (C_l + N_l)
        n_modes = (2 * l_center + 1) * f_sky * delta_ell
        if n_modes > 0:
            sigma = (Cl_sig + Cl_noise) / np.sqrt(n_modes)
            snr = Cl_sig / sigma if sigma > 0 else 0
        else:
            snr = 0
        snr_per_bin.append(float(snr))

    snr_per_bin = np.array(snr_per_bin)
    snr_total = float(np.sqrt(np.sum(snr_per_bin**2)))

    logger.info(f"Euclid Q1 footprint: {17.3} deg² (f_sky = {f_sky:.6f})")
    logger.info(f"Galaxy density: ~30 arcmin⁻²")
    logger.info(f"Total S/N for κ×γ cross-correlation: {snr_total:.1f}σ")
    logger.info(f"Peak per-bin S/N at ℓ ≈ {ell_bins[np.argmax(snr_per_bin)]}: {np.max(snr_per_bin):.2f}")

    # S8 constraint from cross-correlation
    # Fisher forecast: σ(S8) ∝ S8 / SNR_total
    sigma_s8_forecast = S8 / snr_total if snr_total > 0 else float('inf')
    logger.info(f"Forecast σ(S₈) from κ×γ: ±{sigma_s8_forecast:.4f}")
    logger.info(f"K3xT2 prediction: S₈ = {S8} → within {abs(S8 - S8_planck)/sigma_s8_forecast:.1f}σ of Planck")

    # G_eff/G_N discrimination
    delta_Cl = np.mean(np.abs(Cl_kg_mg - Cl_kg_k3t2))
    delta_Cl_sigma = delta_Cl / (np.mean(Cl_kg_k3t2) / snr_total) if snr_total > 0 else 0
    logger.info(f"G_eff/G_N = 1.05 discrimination: {delta_Cl_sigma:.1f}σ")

    results = {
        "footprint_deg2": 17.3,
        "f_sky": round(f_sky, 6),
        "S8_K3T2": S8,
        "SNR_total_kappa_gamma": round(snr_total, 1),
        "sigma_S8_forecast": round(sigma_s8_forecast, 4),
        "G_eff_discrimination_sigma": round(delta_Cl_sigma, 1),
        "verdict": f"Detection at {snr_total:.0f}σ; G_eff=1.05 distinguishable at {delta_Cl_sigma:.0f}σ"
    }
    with open(OUT_DIR / "ca_advanced_1_euclid_planck_kappa.json", "w") as f:
        json.dump(results, f, indent=2)

    # Plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    ax1.loglog(ell, ell * (ell+1) * Cl_kg_k3t2 / (2*np.pi), '-', color='#1f77b4', lw=2,
               label=f'K3×T² ($S_8={S8}, G_{{\\rm eff}}/G_N=1$)')
    ax1.loglog(ell, ell * (ell+1) * Cl_kg_lcdm / (2*np.pi), '--', color='#2ca02c', lw=2,
               label=f'ΛCDM ($S_8={S8_planck}$)')
    ax1.loglog(ell, ell * (ell+1) * Cl_kg_mg / (2*np.pi), ':', color='#d62728', lw=2,
               label=f'Mod. Gravity ($G_{{\\rm eff}}=1.05$)')
    ax1.loglog(ell, ell * (ell+1) * Nl_kg * np.ones_like(ell) / (2*np.pi), 'k--', alpha=0.3, label='Shot noise')
    ax1.set_xlabel("Multipole $\\ell$", fontsize=13)
    ax1.set_ylabel("$\\ell(\\ell+1) C_\\ell^{\\kappa\\gamma} / 2\\pi$", fontsize=13)
    ax1.set_title("Panel A: Cross-Power Spectrum $\\kappa_{\\rm CMB} \\times \\gamma_{\\rm Euclid}$",
                   fontsize=11, fontweight='bold')
    ax1.legend(fontsize=9)
    ax1.grid(True, ls=':', alpha=0.4)

    ax2.bar(ell_bins, snr_per_bin, width=delta_ell*0.8, color='#1f77b4', alpha=0.8)
    ax2.set_xlabel("Multipole $\\ell$", fontsize=13)
    ax2.set_ylabel("Per-bin S/N", fontsize=13)
    ax2.set_title(f"Panel B: Per-Bin S/N (Total = {snr_total:.1f}σ)", fontsize=11, fontweight='bold')
    ax2.grid(True, ls=':', alpha=0.4, axis='y')
    ax2.text(0.95, 0.95, f"$\\sigma(S_8) = \\pm{sigma_s8_forecast:.3f}$\n$S_8^{{\\rm K3T2}} = {S8}$",
             transform=ax2.transAxes, fontsize=11, va='top', ha='right',
             bbox=dict(facecolor='white', edgecolor='#1f77b4', alpha=0.9, boxstyle='round'))

    plt.tight_layout()
    plt.savefig(FIG_DIR / "ca_advanced_1_euclid_planck_kappa.pdf", dpi=300)
    plt.close()
    logger.info(f"Figure saved to {FIG_DIR / 'ca_advanced_1_euclid_planck_kappa.pdf'}")

if __name__ == "__main__":
    main()
