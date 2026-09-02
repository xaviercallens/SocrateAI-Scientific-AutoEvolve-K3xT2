#!/usr/bin/env python3
"""
Cross-Alignment #2: Euclid Q1 S8 × KiDS-1000 Tomographic C_l^EE Cross-Calibration
===================================================================================
Tests whether the Almkvist-Zudilin #1 (P=18) prediction S8 = 0.8318 can
simultaneously explain:
  - The Euclid Q1 galaxy clustering S8 = 0.831 ± 0.006
  - The KiDS-1000 bandpower EE spectrum (8 ell-bins × 5 tomo bins)
  - The legacy S8 posterior ladder: KiDS-1000 (0.759), DES-Y3 (0.776), KiDS-Legacy (0.776), Planck (0.832)

The critical discriminant: If K3xT2 correctly predicts S8 at the Planck/Euclid value,
then the KiDS-1000 deficit must arise from systematic calibration rather than physics.
We compute the per-survey tension in sigma and produce a whisker plot.
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
    logger.info("  Cross-Alignment #2: Euclid Q1 S8 × KiDS-1000 EE Cross-Calibration")
    logger.info("=" * 70)

    # Load KiDS-1000 bandpower data
    with open("data/euclid_q2/kids1000_bandpowers_EE.json") as f:
        kids_bp = json.load(f)
    ell_centres = np.array(kids_bp["ell_centres"])
    bp_EE = np.array(kids_bp["bandpowers_EE"])
    sigma_EE = np.array(kids_bp["sigma_EE"])
    n_ell, n_tomo = bp_EE.shape
    logger.info(f"Loaded KiDS-1000 EE bandpowers: {n_ell} ell-bins × {n_tomo} tomo bins")

    # Load multi-survey S8 measurements
    with open("data/euclid_q2/s8_wl_measurements.json") as f:
        s8_surveys = json.load(f)

    s8_means = np.loadtxt("data/euclid_q2/s8_joint_means.txt", comments='#')
    s8_cov = np.loadtxt("data/euclid_q2/s8_joint_covariance.txt", comments='#')
    s8_sigmas = np.sqrt(np.diag(s8_cov))
    survey_names = ["KiDS-1000", "DES-Y3", "KiDS-Legacy", "Planck"]

    # K3xT2 prediction
    s8_k3t2 = 0.8318

    # Euclid Q1 empirical
    s8_euclid = 0.831
    s8_euclid_err = 0.006

    # Compute per-survey tension with K3xT2
    logger.info(f"\n--- Per-Survey S8 Tension with K3xT2 (S8 = {s8_k3t2}) ---")
    tensions = {}
    for i, name in enumerate(survey_names):
        delta = abs(s8_means[i] - s8_k3t2)
        sigma_tension = delta / s8_sigmas[i]
        tensions[name] = {
            "s8_mean": float(s8_means[i]),
            "s8_sigma": float(s8_sigmas[i]),
            "delta_s8": float(delta),
            "tension_sigma": round(float(sigma_tension), 2),
        }
        logger.info(f"  {name}: S8 = {s8_means[i]:.3f} ± {s8_sigmas[i]:.3f} → Δ = {delta:.3f} ({sigma_tension:.1f}σ)")

    # Euclid Q1
    delta_euclid = abs(s8_euclid - s8_k3t2)
    sigma_euclid = delta_euclid / s8_euclid_err
    tensions["Euclid-Q1"] = {
        "s8_mean": s8_euclid, "s8_sigma": s8_euclid_err,
        "delta_s8": float(delta_euclid), "tension_sigma": round(float(sigma_euclid), 2),
    }
    logger.info(f"  Euclid-Q1: S8 = {s8_euclid} ± {s8_euclid_err} → Δ = {delta_euclid:.4f} ({sigma_euclid:.1f}σ)")

    # KiDS-1000 bandpower scaling analysis
    # Under Limber approximation, C_l^EE scales as (S8)^2.5
    # What rescaling of KiDS fiducial (S8=0.759) to K3xT2 (S8=0.8318) predicts?
    s8_kids_fid = 0.759
    scaling = (s8_k3t2 / s8_kids_fid)**2.5
    bp_rescaled = bp_EE * scaling
    chi2_rescaled = float(np.sum(((bp_EE - bp_rescaled) / sigma_EE)**2))
    logger.info(f"\n--- KiDS-1000 Bandpower Rescaling ---")
    logger.info(f"  Scaling factor (S8=0.832/0.759)^2.5 = {scaling:.4f}")
    logger.info(f"  Mean fractional shift per bin: {np.mean(np.abs(bp_rescaled - bp_EE) / bp_EE)*100:.1f}%")
    logger.info(f"  This shift exceeds KiDS-1000 sigma in {np.sum(np.abs(bp_rescaled - bp_EE) > sigma_EE)}/{n_ell*n_tomo} bins")

    # Joint S8 chi2 vector: all surveys vs K3xT2
    s8_vec = np.append(s8_means, s8_euclid)
    s8_cov_ext = np.zeros((5, 5))
    s8_cov_ext[:4, :4] = s8_cov
    s8_cov_ext[4, 4] = s8_euclid_err**2
    s8_pred_vec = np.full(5, s8_k3t2)
    delta_vec = s8_vec - s8_pred_vec
    chi2_joint_s8 = float(delta_vec @ np.linalg.inv(s8_cov_ext) @ delta_vec)
    logger.info(f"\n--- Joint 5-Survey S8 Chi2 vs K3xT2 ---")
    logger.info(f"  χ²(S8 = 0.8318) = {chi2_joint_s8:.2f} (5 surveys, 5 dof)")
    logger.info(f"  χ²/dof = {chi2_joint_s8/5:.3f}")

    results = {
        "k3t2_prediction": s8_k3t2,
        "per_survey_tensions": tensions,
        "kids_bandpower_scaling_factor": round(scaling, 4),
        "joint_chi2_5surveys": round(chi2_joint_s8, 2),
        "joint_chi2_per_dof": round(chi2_joint_s8 / 5, 3),
    }
    with open(OUT_DIR / "cross_alignment_2_s8_ladder.json", "w") as f:
        json.dump(results, f, indent=2)

    # ─── Plot: S8 Whisker + Bandpower Comparison ──────────────────────────
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    # Left: S8 whisker
    all_names = list(tensions.keys())
    all_means = [tensions[n]["s8_mean"] for n in all_names]
    all_errs = [tensions[n]["s8_sigma"] for n in all_names]
    all_tensions = [tensions[n]["tension_sigma"] for n in all_names]
    y_pos = np.arange(len(all_names))
    colors = ['#d62728' if t > 3 else '#ff7f0e' if t > 1 else '#2ca02c' for t in all_tensions]

    ax1.errorbar(all_means, y_pos, xerr=all_errs, fmt='o', color='black', ecolor='gray',
                 elinewidth=2, capsize=4, ms=8, zorder=5)
    for i, (m, c) in enumerate(zip(all_means, colors)):
        ax1.plot(m, y_pos[i], 'o', color=c, ms=10, zorder=6)

    ax1.axvline(s8_k3t2, color='#1f77b4', ls='-', lw=2.5, label=f'$K_3 \\times T^2$ ($S_8 = {s8_k3t2}$)')
    ax1.axvspan(s8_k3t2 - 0.013, s8_k3t2 + 0.013, alpha=0.15, color='#1f77b4')
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(all_names, fontsize=11)
    ax1.set_xlabel("$S_8 \\equiv \\sigma_8 \\sqrt{\\Omega_m / 0.3}$", fontsize=13)
    ax1.set_title("Panel A: $S_8$ Ladder — Multi-Survey Consistency", fontsize=12, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, ls=':', alpha=0.5, axis='x')

    for i, (n, t) in enumerate(zip(all_names, all_tensions)):
        ax1.annotate(f"{t:.1f}σ", xy=(all_means[i] + all_errs[i] + 0.005, y_pos[i]),
                     fontsize=10, fontweight='bold', color=colors[i], va='center')

    # Right: KiDS-1000 bandpower EE per tomo bin (averaged) vs rescaled
    ax2.set_xlabel("Multipole $\\ell$", fontsize=13)
    ax2.set_ylabel("$C_\\ell^{EE}$ (arb. units)", fontsize=13)
    tomo_colors = plt.cm.viridis(np.linspace(0.1, 0.9, n_tomo))
    for t in range(n_tomo):
        ax2.errorbar(ell_centres, bp_EE[:, t], yerr=sigma_EE[:, t], fmt='o-', ms=4,
                     color=tomo_colors[t], alpha=0.6, label=f'KiDS Tomo {t+1}' if t < 3 else None)
        ax2.plot(ell_centres, bp_rescaled[:, t], 's--', ms=3, color=tomo_colors[t], alpha=0.9)

    ax2.plot([], [], 'ks--', ms=3, label='K3xT2 rescaled (S8=0.832)')
    ax2.set_xscale('log')
    ax2.set_yscale('log')
    ax2.set_title("Panel B: KiDS-1000 $C_\\ell^{EE}$ vs K3×T² Rescaled", fontsize=12, fontweight='bold')
    ax2.legend(fontsize=9)
    ax2.grid(True, ls=':', alpha=0.5)

    plt.tight_layout()
    plt.savefig(FIG_DIR / "cross_alignment_2_s8_ladder.pdf", dpi=300)
    plt.close()
    logger.info(f"Figure saved to {FIG_DIR / 'cross_alignment_2_s8_ladder.pdf'}")

if __name__ == "__main__":
    main()
