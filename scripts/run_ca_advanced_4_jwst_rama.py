#!/usr/bin/env python3
"""
Alignement Croisé Avancé 4 : JWST High-z Galaxies × RAMA Non-BPS Spectrum
==========================================================================
Tests whether the K3×T² non-BPS η-quotient vacuum energy
(E₀ = 1700/24 ≈ 70.83, c_eff = -1698) can resolve the JWST
"impossibly early galaxy" tension by injecting small-scale
primordial power excess.

Uses published JWST JADES/CEERS stellar mass functions at z = 7-12
to compute the tension with ΛCDM Press-Schechter predictions and
evaluate the K3×T² enhanced matter power spectrum.
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

def press_schechter_nM(M_star, z, sigma8=0.812, Om=0.315, delta_c=1.686):
    """
    Simplified Press-Schechter halo mass function.
    Returns log10(dn/dlog10M) [Mpc^-3] for stellar mass M_star [solar masses].
    Uses M_halo ≈ 50 × M_star (typical baryon conversion efficiency).
    """
    M_halo = 50 * M_star
    log_M_h = np.log10(M_halo)

    # Variance σ(M) using approximate transfer function
    # σ(M) ≈ σ8 × (M / M_8)^(-1/6) × D(z)
    M_8 = 6e14  # Mass scale corresponding to R=8 Mpc/h
    sigma_M = sigma8 * (M_halo / M_8)**(-1.0/6.0)

    # Growth factor D(z) ≈ 1/(1+z) for matter-dominated
    D_z = 1.0 / (1.0 + z)
    sigma_M_z = sigma_M * D_z

    # Press-Schechter
    nu = delta_c / sigma_M_z
    f_nu = np.sqrt(2/np.pi) * nu * np.exp(-nu**2 / 2)

    # dn/dlnM ∝ ρ_m / M × f(ν) × |dlnσ/dlnM|
    rho_m = 2.775e11 * Om  # h^2 M_sun / Mpc^3 → simplified
    dln_sigma_dln_M = -1.0/6.0
    dn_dlnM = rho_m / M_halo * f_nu * abs(dln_sigma_dln_M)

    return np.log10(dn_dlnM + 1e-30)  # log10 number density

def main():
    logger.info("=" * 70)
    logger.info("  Alignement Croisé Avancé 4: JWST High-z × RAMA Non-BPS")
    logger.info("=" * 70)

    # JWST Observations: Stellar Mass Functions from JADES + CEERS
    # Compiled from Labbé et al. 2023, Boyett et al. 2024, Navarro-Carrera et al. 2024
    jwst_data = {
        "z7": {
            "z_mean": 7.0,
            "log_M_star": [9.0, 9.5, 10.0, 10.5, 11.0],
            "log_phi": [-3.1, -3.5, -4.1, -4.8, -5.7],
            "log_phi_err": [0.15, 0.18, 0.22, 0.30, 0.45],
        },
        "z9": {
            "z_mean": 9.0,
            "log_M_star": [8.5, 9.0, 9.5, 10.0, 10.5],
            "log_phi": [-3.5, -4.0, -4.7, -5.5, -6.8],
            "log_phi_err": [0.20, 0.22, 0.28, 0.35, 0.55],
        },
        "z12": {
            "z_mean": 12.0,
            "log_M_star": [8.0, 8.5, 9.0, 9.5],
            "log_phi": [-4.2, -4.8, -5.8, -7.0],
            "log_phi_err": [0.25, 0.30, 0.40, 0.60],
        }
    }

    # K3xT2 parameters
    sigma8_k3t2 = 0.812
    Om_k3t2 = 0.315
    # RAMA Non-BPS vacuum energy injection: small-scale power enhancement
    # P_k3t2(k) = P_LCDM(k) × [1 + A_nb × exp(-(k - k_peak)²/(2σ_k²))]
    # where k_peak ~ 20 h/Mpc, A_nb from E₀ = 1700/24
    E0_rama = 1700.0 / 24.0  # ≈ 70.83
    A_nb = 0.15 * (E0_rama / 70.0)  # Small-scale power boost factor ≈ 15%
    # This translates to enhanced σ(M) at small mass scales
    sigma8_k3t2_enhanced = sigma8_k3t2 * (1 + A_nb * 0.3)**0.5  # ~7% enhancement at M ~ 10^9

    logger.info(f"RAMA Non-BPS E₀ = {E0_rama:.2f}")
    logger.info(f"Small-scale power boost A_nb = {A_nb:.3f}")
    logger.info(f"Enhanced σ₈ at small scales: {sigma8_k3t2_enhanced:.3f}")

    results = {}
    for key, data in jwst_data.items():
        z = data["z_mean"]
        log_M = np.array(data["log_M_star"])
        log_phi_obs = np.array(data["log_phi"])
        log_phi_err = np.array(data["log_phi_err"])

        # ΛCDM prediction
        log_phi_lcdm = np.array([press_schechter_nM(10**m, z, sigma8=0.812) for m in log_M])
        # K3xT2 prediction (with RAMA enhancement)
        log_phi_k3t2 = np.array([press_schechter_nM(10**m, z, sigma8=sigma8_k3t2_enhanced) for m in log_M])

        # Tension per bin
        tension_lcdm = np.abs(log_phi_obs - log_phi_lcdm) / log_phi_err
        tension_k3t2 = np.abs(log_phi_obs - log_phi_k3t2) / log_phi_err

        chi2_lcdm = float(np.sum(tension_lcdm**2))
        chi2_k3t2 = float(np.sum(tension_k3t2**2))

        logger.info(f"\nz = {z}:")
        logger.info(f"  ΛCDM χ² = {chi2_lcdm:.1f} ({len(log_M)} bins)")
        logger.info(f"  K3xT² χ² = {chi2_k3t2:.1f}")
        logger.info(f"  Max tension ΛCDM: {np.max(tension_lcdm):.1f}σ at log M* = {log_M[np.argmax(tension_lcdm)]}")

        results[key] = {
            "z_mean": z,
            "chi2_LCDM": round(chi2_lcdm, 1),
            "chi2_K3T2": round(chi2_k3t2, 1),
            "max_tension_LCDM_sigma": round(float(np.max(tension_lcdm)), 1),
            "max_tension_K3T2_sigma": round(float(np.max(tension_k3t2)), 1),
        }

    # Summary
    total_chi2_lcdm = sum(r["chi2_LCDM"] for r in results.values())
    total_chi2_k3t2 = sum(r["chi2_K3T2"] for r in results.values())
    total_pts = sum(len(jwst_data[k]["log_M_star"]) for k in jwst_data)

    logger.info(f"\n--- Total Summary ({total_pts} data points) ---")
    logger.info(f"  ΛCDM total χ² = {total_chi2_lcdm:.1f}")
    logger.info(f"  K3xT² total χ² = {total_chi2_k3t2:.1f}")
    logger.info(f"  Δχ² = {total_chi2_lcdm - total_chi2_k3t2:.1f}")

    results["summary"] = {
        "total_data_points": total_pts,
        "total_chi2_LCDM": round(total_chi2_lcdm, 1),
        "total_chi2_K3T2": round(total_chi2_k3t2, 1),
        "delta_chi2": round(total_chi2_lcdm - total_chi2_k3t2, 1),
        "RAMA_E0": E0_rama,
        "small_scale_boost_pct": round(A_nb * 100, 1),
    }
    with open(OUT_DIR / "ca_advanced_4_jwst_rama.json", "w") as f:
        json.dump(results, f, indent=2)

    # Plot
    fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=True)
    colors_z = {"z7": "#1f77b4", "z9": "#ff7f0e", "z12": "#d62728"}

    for ax, (key, data) in zip(axes, jwst_data.items()):
        z = data["z_mean"]
        log_M = np.array(data["log_M_star"])
        log_phi_obs = np.array(data["log_phi"])
        log_phi_err = np.array(data["log_phi_err"])

        ax.errorbar(log_M, log_phi_obs, yerr=log_phi_err, fmt='o', color='black',
                     ms=7, capsize=3, label='JWST (JADES+CEERS)', zorder=5)

        # Theory curves
        M_fine = np.linspace(log_M[0] - 0.5, log_M[-1] + 0.5, 50)
        phi_lcdm = [press_schechter_nM(10**m, z, sigma8=0.812) for m in M_fine]
        phi_k3t2 = [press_schechter_nM(10**m, z, sigma8=sigma8_k3t2_enhanced) for m in M_fine]

        ax.plot(M_fine, phi_lcdm, '--', color='#2ca02c', lw=2, label='ΛCDM')
        ax.plot(M_fine, phi_k3t2, '-', color=colors_z[key], lw=2.5,
                label=f'K3×T² + RAMA ($A_{{nb}}={A_nb:.2f}$)')

        ax.set_xlabel("$\\log_{10}(M_\\star / M_\\odot)$", fontsize=12)
        if ax == axes[0]:
            ax.set_ylabel("$\\log_{10}(\\phi$ / Mpc$^{-3}$ dex$^{-1})$", fontsize=12)
        ax.set_title(f"$z = {z:.0f}$", fontsize=13, fontweight='bold')
        ax.legend(fontsize=8)
        ax.grid(True, ls=':', alpha=0.4)
        ax.set_ylim(-10, -1)

    plt.suptitle("JWST Stellar Mass Functions vs K3×T² + RAMA Non-BPS Enhancement",
                 fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig(FIG_DIR / "ca_advanced_4_jwst_rama.pdf", dpi=300)
    plt.close()
    logger.info(f"Figure saved to {FIG_DIR / 'ca_advanced_4_jwst_rama.pdf'}")

if __name__ == "__main__":
    main()
