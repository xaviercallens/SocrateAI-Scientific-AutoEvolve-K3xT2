#!/usr/bin/env python3
"""
Phase 8: Next-Generation GW Projections (SKA / LISA)
=====================================================
Directive 8-3: Generates the frequency-resolved strain spectrum
comparing the standard Supermassive Black Hole Binary (SMBHB) background
against the K4 Oligon topological defect model (Cooper s10).

Projects NANOGrav 15-year, SKA, and LISA sensitivity curves.
"""

import logging
import os
from pathlib import Path
import numpy as np

# Configure matplotlib for headless generation
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def compute_smbhb_spectrum(freqs: np.ndarray) -> np.ndarray:
    """
    Standard Lambda-CDM SMBHB stochastic background.
    Strain h_c(f) = A_yr * (f / 1yr^-1)^(-2/3)
    """
    f_yr = 1.0 / (365.25 * 24 * 3600)  # ~3.17e-8 Hz
    A_yr = 2.4e-15  # NANOGrav 15-year amplitude
    return A_yr * (freqs / f_yr)**(-2/3)


def compute_oligon_spectrum(freqs: np.ndarray) -> np.ndarray:
    """
    K4 Oligon (K3xT2) topological defect background.
    Features a steepened spectral index (gamma = 4.847) 
    and a Compton resonance peak at ~24.18 nHz.
    """
    f_yr = 1.0 / (365.25 * 24 * 3600)
    A_oligon = 1.8e-15
    
    # K4 Oligon spectral index (alpha = (3 - gamma)/2)
    # gamma = 4.847 -> alpha = -0.9235 (steeper than -2/3 = -0.666)
    alpha = (3.0 - 4.847) / 2.0
    
    base_strain = A_oligon * (freqs / f_yr)**alpha
    
    # Add Compton resonance bump at 24.18 nHz
    f_res = 24.18e-9
    width = 3.0e-9
    resonance = 0.5 * base_strain * np.exp(-0.5 * ((freqs - f_res) / width)**2)
    
    return base_strain + resonance


def plot_gw_projections(output_path: str):
    """Plot the GW strain spectra and detector sensitivities."""
    
    # Frequency range: 1 nHz to 100 nHz (PTA band)
    freqs_pta = np.logspace(-9, -7, 500)
    
    h_smbhb = compute_smbhb_spectrum(freqs_pta)
    h_oligon = compute_oligon_spectrum(freqs_pta)
    
    # Detector sensitivities (approximate characteristic strain limits)
    # NANOGrav 15-year (current)
    sens_nanograv = 3e-15 * np.ones_like(freqs_pta) * (freqs_pta / 1e-8)**0.5
    
    # SKA (projected 10x improvement in PTA band)
    sens_ska = sens_nanograv / 10.0
    
    # LISA (higher frequency band, we'll plot a portion just to show it's off to the right)
    freqs_lisa = np.logspace(-5, -1, 100)
    sens_lisa = 1e-20 * (freqs_lisa / 1e-2)**(-2/3) + 1e-21 * (freqs_lisa / 1e-2)**2
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot models
    ax.loglog(freqs_pta, h_smbhb, 'k--', linewidth=2, label=r'Standard SMBHB ($\Lambda$CDM)')
    ax.loglog(freqs_pta, h_oligon, 'b-', linewidth=2.5, label=r'K$_4$ Oligon Topological ($K3 \times T^2$)')
    
    # Highlight the resonance
    f_res = 24.18e-9
    ax.axvline(f_res, color='r', linestyle=':', alpha=0.5, label='Compton Resonance (24.18 nHz)')
    
    # Plot sensitivities
    ax.fill_between(freqs_pta, sens_nanograv, 1e-12, color='gray', alpha=0.2, label='NANOGrav 15yr Noise Floor')
    ax.fill_between(freqs_pta, sens_ska, sens_nanograv, color='green', alpha=0.1, label='Projected SKA Sensitivity')
    
    ax.set_xlim(1e-9, 1e-7)
    ax.set_ylim(1e-16, 1e-13)
    
    ax.set_xlabel('Frequency [Hz]', fontsize=14)
    ax.set_ylabel(r'Characteristic Strain $h_c(f)$', fontsize=14)
    ax.set_title('Next-Generation GW Projections: Falsifying the K$_4$ Oligon', fontsize=15)
    
    ax.legend(loc='upper right', framealpha=0.9)
    ax.grid(True, which='both', linestyle='--', alpha=0.5)
    
    plt.tight_layout()
    fig.savefig(output_path, dpi=300)
    logger.info(f"GW projection plot saved to {output_path}")


def main():
    logger.info("═══════════════════════════════════════════════════════")
    logger.info("  Phase 8-3: GW Sensitivity Projections (SKA / LISA)")
    logger.info("═══════════════════════════════════════════════════════")
    
    out_dir = Path("paper/figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    plot_path = out_dir / "gw_ska_projections.pdf"
    plot_gw_projections(str(plot_path))
    
    logger.info("Done.")

if __name__ == "__main__":
    main()
