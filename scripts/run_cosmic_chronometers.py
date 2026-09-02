#!/usr/bin/env python3
"""
Cosmic Chronometers Expansion Test: H(z) Direct Uncalibrated Probe
==================================================================
Tests the Almkvist-Zudilin #1 (P=18) prediction (H0 = 69.3, w0 = -0.974, Om = 0.315)
against 32 real passively evolving Cosmic Chronometer measurements (Moresco et al. 2022).

Unlike BAO (which is degenerate with the sound horizon r_d), Cosmic Chronometers
measure H(z) = -1/(1+z) dz/dt directly via differential stellar population dating.
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

DATA_PATH = Path("data/cosmic_chronometers/cc_32_moresco.txt")
OUT_DIR = Path("outputs/cosmic_chronometers")
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR = Path("paper/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

def hz_model(z, h0, om, w0=-1.0):
    """Computes H(z) for flat w0-cosmology."""
    ol = 1.0 - om
    e2 = om * (1.0 + z)**3 + ol * (1.0 + z)**(3.0 * (1.0 + w0))
    return h0 * np.sqrt(e2)

def main():
    logger.info("Loading 32-point Cosmic Chronometers dataset...")
    data = []
    with open(DATA_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            data.append([float(parts[0]), float(parts[1]), float(parts[2])])
    data = np.array(data)
    z_obs = data[:, 0]
    h_obs = data[:, 1]
    err_obs = data[:, 2]

    logger.info(f"Loaded {len(z_obs)} Cosmic Chronometer measurements from z={z_obs.min()} to z={z_obs.max()}.")

    # Define models
    models = {
        "K3xT2 (AZ1, P=18)": {"h0": 69.30, "om": 0.315, "w0": -0.974, "color": "#1f77b4", "ls": "-"},
        "LambdaCDM (Planck 2018)": {"h0": 67.40, "om": 0.315, "w0": -1.000, "color": "#2ca02c", "ls": "--"},
        "SH0ES (High H0)": {"h0": 73.04, "om": 0.315, "w0": -1.000, "color": "#d62728", "ls": ":"},
    }

    results = {}
    dof = len(z_obs) - 2

    for name, params in models.items():
        h_pred = hz_model(z_obs, params["h0"], params["om"], params["w0"])
        residuals = (h_obs - h_pred) / err_obs
        chi2 = float(np.sum(residuals**2))
        chi2_red = chi2 / dof
        log_lik = float(-0.5 * chi2 - 0.5 * np.sum(np.log(2.0 * np.pi * err_obs**2)))
        results[name] = {
            "params": params,
            "chi2": chi2,
            "chi2_dof": chi2_red,
            "log_likelihood": log_lik,
        }
        logger.info(f"{name}: χ² = {chi2:.2f} (χ²/dof = {chi2_red:.2f}) | log L = {log_lik:.2f}")

    chi2_ref = results["LambdaCDM (Planck 2018)"]["chi2"]
    for name in results:
        results[name]["delta_chi2_vs_lcdm"] = results[name]["chi2"] - chi2_ref
        results[name]["ln_bayes_factor_vs_lcdm"] = -0.5 * results[name]["delta_chi2_vs_lcdm"]

    # Save JSON
    out_json = OUT_DIR / "cosmic_chronometers_summary.json"
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved to {out_json}")

    # Plot
    z_fine = np.linspace(0.0, 2.1, 300)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 7), sharex=True, gridspec_kw={'height_ratios': [2.5, 1]})

    ax1.errorbar(z_obs, h_obs, yerr=err_obs, fmt='o', color='black', ecolor='gray', elinewidth=1.5,
                 capsize=2, markersize=5, label='Cosmic Chronometers (32 pts, Moresco+22)')

    for name, params in models.items():
        h_curve = hz_model(z_fine, params["h0"], params["om"], params["w0"])
        c2 = results[name]["chi2"]
        c2_r = results[name]["chi2_dof"]
        lbl = f"{name} [$\\chi^2_\\nu = {c2_r:.2f}$]"
        ax1.plot(z_fine, h_curve, color=params["color"], linestyle=params["ls"], lw=2, label=lbl)

    ax1.set_ylabel(r"$H(z)$ [km s$^{-1}$ Mpc$^{-1}$]", fontsize=13)
    ax1.set_title("Direct Uncalibrated Expansion Rate: Cosmic Chronometers vs Models", fontsize=14, fontweight="bold")
    ax1.legend(loc="upper left", frameon=True, fontsize=10)
    ax1.grid(True, linestyle=":", alpha=0.6)

    # Residuals
    for name, params in models.items():
        h_pred = hz_model(z_obs, params["h0"], params["om"], params["w0"])
        pull = (h_obs - h_pred) / err_obs
        ax2.plot(z_obs, pull, 'o', color=params["color"], markersize=4, label=name)
        ax2.plot(z_fine, np.zeros_like(z_fine), 'k--', lw=0.8)

    ax2.axhline(0, color='black', linestyle='--', lw=1)
    ax2.set_xlabel("Redshift $z$", fontsize=13)
    ax2.set_ylabel(r"Pull $(H_{\rm obs} - H_{\rm th})/\sigma$", fontsize=11)
    ax2.set_ylim(-3.0, 3.0)
    ax2.grid(True, linestyle=":", alpha=0.6)

    plt.tight_layout()
    out_pdf = FIG_DIR / "cosmic_chronometers_expansion.pdf"
    plt.savefig(out_pdf, dpi=300)
    plt.close()
    logger.info(f"Figure saved to {out_pdf}")

if __name__ == "__main__":
    main()
