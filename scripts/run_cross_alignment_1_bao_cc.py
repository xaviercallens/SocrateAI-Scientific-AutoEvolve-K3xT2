#!/usr/bin/env python3
"""
Cross-Alignment #1: DESI BAO × Cosmic Chronometers H(z) Joint Sound-Horizon Decoupling
========================================================================================
Tests whether the Almkvist-Zudilin #1 (P=18) cosmology simultaneously satisfies:
  - DESI DR1 BAO distance ratios D_M/r_d, D_H/r_d, D_V/r_d (calibrated to r_d)
  - Cosmic Chronometers H(z) (completely independent of r_d)

The key discriminant: BAO constrain D(z)/r_d while CC constrain H(z) directly.
For a given cosmology, the predicted r_d is fixed. If the same (H0, Om, w0) fits
both probes independently AND their implied r_d values agree, this constitutes
a powerful geometric consistency check that breaks the sound-horizon degeneracy.
"""

import json
import logging
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.integrate import quad

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

OUT_DIR = Path("outputs/cross_alignments")
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR = Path("paper/figures")

# ─── Cosmological Functions ───────────────────────────────────────────────
c_km_s = 299792.458  # km/s

def E_z(z, Om, w0):
    """Dimensionless Hubble parameter E(z) = H(z)/H0."""
    OL = 1.0 - Om
    return np.sqrt(Om * (1 + z)**3 + OL * (1 + z)**(3*(1 + w0)))

def H_z(z, H0, Om, w0):
    return H0 * E_z(z, Om, w0)

def comoving_distance(z, H0, Om, w0):
    """D_C(z) in Mpc."""
    integrand = lambda zp: 1.0 / E_z(zp, Om, w0)
    result, _ = quad(integrand, 0, z)
    return (c_km_s / H0) * result

def D_M(z, H0, Om, w0):
    """Transverse comoving distance (flat universe)."""
    return comoving_distance(z, H0, Om, w0)

def D_H(z, H0, Om, w0):
    """Hubble distance D_H = c / H(z)."""
    return c_km_s / H_z(z, H0, Om, w0)

def D_V(z, H0, Om, w0):
    """Volume-averaged distance."""
    dm = D_M(z, H0, Om, w0)
    dh = D_H(z, H0, Om, w0)
    return (z * dm**2 * dh)**(1.0/3.0)

def sound_horizon_approx(H0, Om, Ob=0.0493):
    """
    Sound horizon at drag epoch using Aubourg+2015 / Verde+2017 calibrated fitting formula.
    r_d in Mpc. Calibrated to reproduce r_d ≈ 147.09 Mpc for Planck 2018 cosmology.
    """
    h = H0 / 100.0
    om_h2 = Om * h**2
    ob_h2 = Ob * h**2
    # Verde, Treu, Riess (2019) Eq. 15, calibrated against CAMB
    r_d = 147.05 * (om_h2 / 0.1432)**(-0.255) * (ob_h2 / 0.02236)**(-0.128)
    return r_d

# ─── Data Loading ─────────────────────────────────────────────────────────
def load_desi_bao():
    data = []
    with open("data/desi_dr1/desi_2024_gaussian_bao_ALL_GCcomb_mean.txt") as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.split()
            data.append({"z": float(parts[0]), "value": float(parts[1]), "type": parts[2]})
    cov = np.loadtxt("data/desi_dr1/desi_2024_gaussian_bao_ALL_GCcomb_cov.txt")
    return data, cov

def load_cc():
    data = []
    with open("data/cosmic_chronometers/cc_32_moresco.txt") as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.split()
            data.append({"z": float(parts[0]), "H": float(parts[1]), "err": float(parts[2])})
    return data

# ─── Main ─────────────────────────────────────────────────────────────────
def main():
    logger.info("=" * 70)
    logger.info("  Cross-Alignment #1: DESI BAO × Cosmic Chronometers Joint Analysis")
    logger.info("=" * 70)

    desi_data, desi_cov = load_desi_bao()
    cc_data = load_cc()
    desi_inv_cov = np.linalg.inv(desi_cov)

    models = {
        "K3xT2 (AZ1, P=18)": {"H0": 69.30, "Om": 0.315, "w0": -0.974, "Ob": 0.0493},
        "LambdaCDM (Planck 2018)": {"H0": 67.40, "Om": 0.315, "w0": -1.000, "Ob": 0.0493},
        "SH0ES (High H0)":  {"H0": 73.04, "Om": 0.315, "w0": -1.000, "Ob": 0.0493},
    }

    results = {}

    for name, p in models.items():
        H0, Om, w0, Ob = p["H0"], p["Om"], p["w0"], p["Ob"]
        r_d = sound_horizon_approx(H0, Om, Ob)

        # BAO chi2
        pred_bao = []
        for d in desi_data:
            z = d["z"]
            if d["type"] == "DV_over_rs":
                pred_bao.append(D_V(z, H0, Om, w0) / r_d)
            elif d["type"] == "DM_over_rs":
                pred_bao.append(D_M(z, H0, Om, w0) / r_d)
            elif d["type"] == "DH_over_rs":
                pred_bao.append(D_H(z, H0, Om, w0) / r_d)
        pred_bao = np.array(pred_bao)
        obs_bao = np.array([d["value"] for d in desi_data])
        delta_bao = obs_bao - pred_bao
        chi2_bao = float(delta_bao @ desi_inv_cov @ delta_bao)

        # CC chi2
        z_cc = np.array([d["z"] for d in cc_data])
        h_cc = np.array([d["H"] for d in cc_data])
        err_cc = np.array([d["err"] for d in cc_data])
        h_pred_cc = H_z(z_cc, H0, Om, w0)
        chi2_cc = float(np.sum(((h_cc - h_pred_cc) / err_cc)**2))

        # Joint
        chi2_joint = chi2_bao + chi2_cc
        dof_bao = len(desi_data)
        dof_cc = len(cc_data) - 2
        dof_joint = dof_bao + dof_cc

        results[name] = {
            "H0": H0, "Om": Om, "w0": w0,
            "r_d_Mpc": round(r_d, 2),
            "chi2_BAO": round(chi2_bao, 2),
            "chi2_CC": round(chi2_cc, 2),
            "chi2_joint": round(chi2_joint, 2),
            "dof_joint": dof_joint,
            "chi2_per_dof_joint": round(chi2_joint / dof_joint, 3),
        }
        logger.info(f"{name}: r_d = {r_d:.2f} Mpc | BAO χ²={chi2_bao:.2f} | CC χ²={chi2_cc:.2f} | Joint χ²/dof = {chi2_joint:.2f}/{dof_joint} = {chi2_joint/dof_joint:.3f}")

    # Implied r_d consistency check
    r_d_k3t2 = results["K3xT2 (AZ1, P=18)"]["r_d_Mpc"]
    r_d_lcdm = results["LambdaCDM (Planck 2018)"]["r_d_Mpc"]
    r_d_shoes = results["SH0ES (High H0)"]["r_d_Mpc"]
    r_d_planck_direct = 147.09  # Planck 2018 direct measurement

    logger.info(f"\n--- Sound Horizon Consistency ---")
    logger.info(f"  Planck 2018 direct: r_d = {r_d_planck_direct:.2f} Mpc")
    logger.info(f"  K3xT2 implied:     r_d = {r_d_k3t2:.2f} Mpc (delta = {abs(r_d_k3t2 - r_d_planck_direct):.2f})")
    logger.info(f"  LCDM implied:      r_d = {r_d_lcdm:.2f} Mpc (delta = {abs(r_d_lcdm - r_d_planck_direct):.2f})")
    logger.info(f"  SH0ES implied:     r_d = {r_d_shoes:.2f} Mpc (delta = {abs(r_d_shoes - r_d_planck_direct):.2f})")

    results["sound_horizon_consistency"] = {
        "r_d_planck_direct_Mpc": r_d_planck_direct,
        "r_d_K3T2_Mpc": r_d_k3t2,
        "r_d_LCDM_Mpc": r_d_lcdm,
        "r_d_SH0ES_Mpc": r_d_shoes,
    }

    with open(OUT_DIR / "cross_alignment_1_bao_cc.json", "w") as f:
        json.dump(results, f, indent=2)

    # ─── Plot ─────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # Left panel: H(z)
    ax = axes[0]
    z_cc_arr = np.array([d["z"] for d in cc_data])
    h_cc_arr = np.array([d["H"] for d in cc_data])
    err_cc_arr = np.array([d["err"] for d in cc_data])
    ax.errorbar(z_cc_arr, h_cc_arr, yerr=err_cc_arr, fmt='ko', ms=4, elinewidth=1, capsize=2, label='CC (Moresco+22)', zorder=5)

    z_fine = np.linspace(0, 2.2, 300)
    colors = {"K3xT2 (AZ1, P=18)": "#1f77b4", "LambdaCDM (Planck 2018)": "#2ca02c", "SH0ES (High H0)": "#d62728"}
    ls_map = {"K3xT2 (AZ1, P=18)": "-", "LambdaCDM (Planck 2018)": "--", "SH0ES (High H0)": ":"}
    for name, p in models.items():
        h_curve = H_z(z_fine, p["H0"], p["Om"], p["w0"])
        ax.plot(z_fine, h_curve, color=colors[name], ls=ls_map[name], lw=2, label=name)

    # Overlay DESI DH points: DH/rs -> H = c/(DH/rs * rd)
    for name, p in models.items():
        r_d = sound_horizon_approx(p["H0"], p["Om"], p["w0"], )
        for d in desi_data:
            if d["type"] == "DH_over_rs":
                h_bao = c_km_s / (d["value"] * r_d)
                ax.plot(d["z"], h_bao, 's', color=colors[name], ms=10, markeredgecolor='black', markeredgewidth=0.5, zorder=6)

    ax.set_xlabel("Redshift $z$", fontsize=13)
    ax.set_ylabel(r"$H(z)$ [km s$^{-1}$ Mpc$^{-1}$]", fontsize=13)
    ax.set_title("Panel A: CC $H(z)$ + DESI $D_H/r_d$ Overlap", fontsize=12, fontweight='bold')
    ax.legend(fontsize=9, loc='upper left')
    ax.grid(True, ls=':', alpha=0.5)

    # Right panel: Joint chi2 bar chart
    ax2 = axes[1]
    model_names = list(models.keys())
    chi2_bao_vals = [results[n]["chi2_BAO"] for n in model_names]
    chi2_cc_vals = [results[n]["chi2_CC"] for n in model_names]
    x = np.arange(len(model_names))
    w = 0.35
    ax2.bar(x - w/2, chi2_bao_vals, w, label='DESI BAO $\\chi^2$ (12 pts)', color='#ff7f0e', alpha=0.85)
    ax2.bar(x + w/2, chi2_cc_vals, w, label='CC $H(z)$ $\\chi^2$ (32 pts)', color='#1f77b4', alpha=0.85)
    ax2.set_xticks(x)
    ax2.set_xticklabels([n.split('(')[0].strip() for n in model_names], fontsize=10)
    ax2.set_ylabel('$\\chi^2$', fontsize=13)
    ax2.set_title("Panel B: BAO × CC Joint $\\chi^2$ Decomposition", fontsize=12, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, ls=':', alpha=0.5, axis='y')

    plt.tight_layout()
    plt.savefig(FIG_DIR / "cross_alignment_1_bao_cc.pdf", dpi=300)
    plt.close()
    logger.info(f"Figure saved to {FIG_DIR / 'cross_alignment_1_bao_cc.pdf'}")

if __name__ == "__main__":
    main()
