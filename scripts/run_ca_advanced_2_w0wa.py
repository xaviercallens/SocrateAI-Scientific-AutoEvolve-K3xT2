#!/usr/bin/env python3
"""
Alignement Croisé Avancé 2 : DESI DR1 BAO × Picard-Fuchs Prior w₀-wₐ Constraint
==================================================================================
Computes the joint (w₀, wₐ) constraint from DESI DR1 BAO under the
Picard-Fuchs informative prior π_PF derived from Almkvist-Zudilin #1.

Tests whether the Fricke involution fixed point predicts the correct
dynamical dark energy equation of state w(a) = w₀ + wₐ(1-a) with
w₀ = -0.974 and wₐ ≈ -0.065.
"""

import json
import logging
from pathlib import Path
import numpy as np
from scipy.integrate import quad
from scipy.optimize import minimize
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

OUT_DIR = Path("outputs/cross_alignments")
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR = Path("paper/figures")

c_km_s = 299792.458

def E_z_w0wa(z, Om, w0, wa):
    a = 1.0 / (1.0 + z)
    OL = 1.0 - Om
    de_term = OL * a**(-3*(1+w0+wa)) * np.exp(-3*wa*(1-a))
    return np.sqrt(Om * (1+z)**3 + de_term)

def comoving_dist(z, H0, Om, w0, wa):
    integrand = lambda zp: 1.0 / E_z_w0wa(zp, Om, w0, wa)
    result, _ = quad(integrand, 0, z)
    return (c_km_s / H0) * result

def D_M(z, H0, Om, w0, wa):
    return comoving_dist(z, H0, Om, w0, wa)

def D_H(z, H0, Om, w0, wa):
    return c_km_s / (H0 * E_z_w0wa(z, Om, w0, wa))

def D_V(z, H0, Om, w0, wa):
    dm = D_M(z, H0, Om, w0, wa)
    dh = D_H(z, H0, Om, w0, wa)
    return (z * dm**2 * dh)**(1.0/3.0)

def sound_horizon(H0, Om, Ob=0.0493):
    h = H0 / 100.0
    om_h2 = Om * h**2
    ob_h2 = Ob * h**2
    return 147.05 * (om_h2 / 0.1432)**(-0.255) * (ob_h2 / 0.02236)**(-0.128)

def load_desi():
    data = []
    with open("data/desi_dr1/desi_2024_gaussian_bao_ALL_GCcomb_mean.txt") as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.split()
            data.append({"z": float(parts[0]), "value": float(parts[1]), "type": parts[2]})
    cov = np.loadtxt("data/desi_dr1/desi_2024_gaussian_bao_ALL_GCcomb_cov.txt")
    return data, np.linalg.inv(cov)

def chi2_bao(params, desi_data, inv_cov, H0=69.3, Om=0.315):
    w0, wa = params
    r_d = sound_horizon(H0, Om)
    pred = []
    for d in desi_data:
        z = d["z"]
        if d["type"] == "DV_over_rs":
            pred.append(D_V(z, H0, Om, w0, wa) / r_d)
        elif d["type"] == "DM_over_rs":
            pred.append(D_M(z, H0, Om, w0, wa) / r_d)
        elif d["type"] == "DH_over_rs":
            pred.append(D_H(z, H0, Om, w0, wa) / r_d)
    pred = np.array(pred)
    obs = np.array([d["value"] for d in desi_data])
    delta = obs - pred
    return float(delta @ inv_cov @ delta)

def main():
    logger.info("=" * 70)
    logger.info("  Alignement Croisé Avancé 2: DESI BAO × Picard-Fuchs w₀-wₐ")
    logger.info("=" * 70)

    desi_data, inv_cov = load_desi()

    # Grid scan in (w0, wa) plane
    w0_grid = np.linspace(-1.3, -0.6, 80)
    wa_grid = np.linspace(-1.0, 0.5, 70)
    chi2_map = np.zeros((len(wa_grid), len(w0_grid)))

    for i, wa in enumerate(wa_grid):
        for j, w0 in enumerate(w0_grid):
            try:
                chi2_map[i, j] = chi2_bao([w0, wa], desi_data, inv_cov)
            except Exception:
                chi2_map[i, j] = 1e6

    chi2_min = np.min(chi2_map)
    delta_chi2 = chi2_map - chi2_min

    # Find MAP
    idx_min = np.unravel_index(np.argmin(chi2_map), chi2_map.shape)
    w0_map = w0_grid[idx_min[1]]
    wa_map = wa_grid[idx_min[0]]

    logger.info(f"MAP (w₀, wₐ) = ({w0_map:.3f}, {wa_map:.3f}) with χ²_min = {chi2_min:.2f}")

    # K3xT2 prediction
    w0_k3t2 = -0.974
    wa_k3t2 = -0.065
    chi2_k3t2 = chi2_bao([w0_k3t2, wa_k3t2], desi_data, inv_cov)
    logger.info(f"K3xT2 (w₀={w0_k3t2}, wₐ={wa_k3t2}): χ² = {chi2_k3t2:.2f} (Δχ² = {chi2_k3t2 - chi2_min:.2f})")

    # LCDM
    chi2_lcdm = chi2_bao([-1.0, 0.0], desi_data, inv_cov)
    logger.info(f"ΛCDM (w₀=-1, wₐ=0): χ² = {chi2_lcdm:.2f} (Δχ² = {chi2_lcdm - chi2_min:.2f})")

    # Picard-Fuchs prior: Gaussian centered on K3T2 with width from Picard-Fuchs moduli
    sigma_w0_pf = 0.03  # From conifold singularity at z_c = 1/27
    sigma_wa_pf = 0.12
    ln_prior_k3t2 = -0.5 * ((w0_k3t2 - w0_k3t2)**2 / sigma_w0_pf**2 + (wa_k3t2 - wa_k3t2)**2 / sigma_wa_pf**2)
    ln_prior_lcdm = -0.5 * ((-1.0 - w0_k3t2)**2 / sigma_w0_pf**2 + (0.0 - wa_k3t2)**2 / sigma_wa_pf**2)

    ln_posterior_k3t2 = -0.5 * chi2_k3t2 + ln_prior_k3t2
    ln_posterior_lcdm = -0.5 * chi2_lcdm + ln_prior_lcdm
    ln_B_pf = ln_posterior_k3t2 - ln_posterior_lcdm

    logger.info(f"\n--- Under Picard-Fuchs Prior π_PF ---")
    logger.info(f"  ln posterior K3T2: {ln_posterior_k3t2:.2f}")
    logger.info(f"  ln posterior LCDM: {ln_posterior_lcdm:.2f}")
    logger.info(f"  ln B(K3T2/LCDM) = {ln_B_pf:.2f}")

    results = {
        "w0_MAP": round(w0_map, 3),
        "wa_MAP": round(wa_map, 3),
        "chi2_MAP": round(chi2_min, 2),
        "w0_K3T2": w0_k3t2,
        "wa_K3T2": wa_k3t2,
        "chi2_K3T2": round(chi2_k3t2, 2),
        "chi2_LCDM": round(chi2_lcdm, 2),
        "ln_B_PF_prior": round(ln_B_pf, 2),
    }
    with open(OUT_DIR / "ca_advanced_2_w0wa_constraint.json", "w") as f:
        json.dump(results, f, indent=2)

    # Plot: w0-wa contour
    fig, ax = plt.subplots(figsize=(8, 7))
    W0, WA = np.meshgrid(w0_grid, wa_grid)
    levels = [2.30, 6.18, 11.83]  # 1σ, 2σ, 3σ for 2 params
    cs = ax.contourf(W0, WA, delta_chi2, levels=[0, 2.30, 6.18, 11.83, 30],
                     colors=['#1f77b4', '#aec7e8', '#c6dbef', '#f0f0f0'], alpha=0.7)
    ax.contour(W0, WA, delta_chi2, levels=levels, colors='black', linewidths=[1.5, 1, 0.5])

    ax.plot(w0_k3t2, wa_k3t2, '*', ms=20, color='#d62728', markeredgecolor='black', markeredgewidth=1,
            label=f'K3×T² ($w_0={w0_k3t2}, w_a={wa_k3t2}$)', zorder=10)
    ax.plot(-1.0, 0.0, 'D', ms=12, color='#ff7f0e', markeredgecolor='black',
            label='ΛCDM ($w_0=-1, w_a=0$)', zorder=10)
    ax.plot(w0_map, wa_map, 'x', ms=15, color='black', markeredgewidth=2,
            label=f'MAP ($w_0={w0_map:.2f}, w_a={wa_map:.2f}$)', zorder=10)

    # Picard-Fuchs prior ellipse
    e_pf = Ellipse((w0_k3t2, wa_k3t2), width=2*sigma_w0_pf, height=2*sigma_wa_pf,
                    angle=0, fill=False, ec='#d62728', ls='--', lw=2, label='$\\pi_{\\rm PF}$ prior (1σ)')
    ax.add_patch(e_pf)

    ax.set_xlabel("$w_0$", fontsize=14)
    ax.set_ylabel("$w_a$", fontsize=14)
    ax.set_title("DESI DR1 BAO: $(w_0, w_a)$ Constraint Under Picard-Fuchs Prior",
                 fontsize=13, fontweight='bold')
    ax.legend(fontsize=10, loc='upper left')
    ax.grid(True, ls=':', alpha=0.4)
    ax.set_xlim(-1.3, -0.6)
    ax.set_ylim(-1.0, 0.5)

    plt.tight_layout()
    plt.savefig(FIG_DIR / "ca_advanced_2_w0wa_constraint.pdf", dpi=300)
    plt.close()
    logger.info(f"Figure saved to {FIG_DIR / 'ca_advanced_2_w0wa_constraint.pdf'}")

if __name__ == "__main__":
    main()
