#!/usr/bin/env python3
import json
import logging
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def model_hc(f, A, gamma, f_yr=3.16e-8):
    """
    Standard characteristic strain: h_c(f) = A * (f / f_yr)^((3 - gamma) / 2)
    """
    return A * (f / f_yr)**((3.0 - gamma) / 2.0)

def k3t2_hc(f, A, gamma=4.847, f_yr=3.16e-8, bump_freq=24.18e-9, bump_amp=3e-15, bump_width=1e-9):
    """
    K3xT2 model: baseline with gamma=4.847 plus a Gaussian bump.
    """
    base = model_hc(f, A, gamma, f_yr)
    bump = bump_amp * np.exp(-0.5 * ((f - bump_freq) / bump_width)**2)
    return base + bump

def main():
    out_dir = Path("outputs/ws3")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Load NANOGrav data
    with open("data/nanograv/input.json") as f:
        data = json.load(f)
        
    freqs = np.array(data["frequencies_hz"])
    h_c_data = np.array(data["data_strain"])
    h_c_err = np.array(data["data_errors"])
    
    # We will fit the overall amplitude A for both models
    # SMBHB model has gamma = 13/3 ~ 4.333
    gamma_smbhb = 13.0 / 3.0
    A_smbhb = 2.4e-15  # typical 15-yr amplitude at f_yr
    
    # K3xT2 has gamma = 4.847
    gamma_k3t2 = 4.847
    A_k3t2 = 1.8e-15
    bump_freq = 24.18e-9
    bump_amp = 2e-15
    bump_width = 2e-9
    
    # Simple grid search for A for SMBHB
    A_grid = np.linspace(1e-15, 5e-15, 1000)
    chi2_smbhb = []
    for A in A_grid:
        h_c = model_hc(freqs, A, gamma_smbhb)
        chi2 = np.sum(((h_c - h_c_data) / h_c_err)**2)
        chi2_smbhb.append(chi2)
    
    chi2_smbhb = np.array(chi2_smbhb)
    best_A_smbhb = A_grid[np.argmin(chi2_smbhb)]
    min_chi2_smbhb = np.min(chi2_smbhb)
    
    # Grid search for A for K3xT2
    chi2_k3t2 = []
    for A in A_grid:
        h_c = k3t2_hc(freqs, A, gamma_k3t2, bump_freq=bump_freq, bump_amp=bump_amp, bump_width=bump_width)
        chi2 = np.sum(((h_c - h_c_data) / h_c_err)**2)
        chi2_k3t2.append(chi2)
        
    chi2_k3t2 = np.array(chi2_k3t2)
    best_A_k3t2 = A_grid[np.argmin(chi2_k3t2)]
    min_chi2_k3t2 = np.min(chi2_k3t2)
    
    # Compute Bayes factor from chi2 difference (assuming flat priors)
    delta_chi2 = min_chi2_smbhb - min_chi2_k3t2
    ln_B = 0.5 * delta_chi2
    
    logger.info(f"SMBHB (gamma={gamma_smbhb:.3f}): best A={best_A_smbhb:.2e}, chi2={min_chi2_smbhb:.2f}")
    logger.info(f"K3xT2 (gamma={gamma_k3t2:.3f}): best A={best_A_k3t2:.2e}, chi2={min_chi2_k3t2:.2f}")
    logger.info(f"Delta chi2: {delta_chi2:.2f} (positive favors K3xT2)")
    logger.info(f"ln(Bayes Factor): {ln_B:.2f}")
    
    # Plotting
    f_dense = np.logspace(-9, -7, 500)
    
    plt.figure(figsize=(10, 6))
    plt.errorbar(freqs * 1e9, h_c_data, yerr=h_c_err, fmt='o', color='black', label='NANOGrav 15-yr Free Spectrum')
    plt.plot(f_dense * 1e9, model_hc(f_dense, best_A_smbhb, gamma_smbhb), 'b--', label=f'SMBHB ($\gamma=13/3$)')
    plt.plot(f_dense * 1e9, k3t2_hc(f_dense, best_A_k3t2, gamma_k3t2, bump_freq=bump_freq, bump_amp=bump_amp, bump_width=bump_width), 'r-', label=f'K3xT2 ($\gamma=4.847$ + bump)')
    
    plt.axvline(bump_freq * 1e9, color='gray', linestyle=':', alpha=0.5, label='24.18 nHz Resonance')
    plt.xscale('log')
    plt.yscale('log')
    plt.xlabel('Frequency (nHz)')
    plt.ylabel('Characteristic Strain $h_c$')
    plt.title('NANOGrav 15-Year Spectral Shape Test')
    plt.legend()
    plt.grid(True, which="both", ls="-", alpha=0.2)
    plt.tight_layout()
    plt.savefig(out_dir / "nanograv_spectral_fit.pdf")
    
    # Save JSON output
    results = {
        "best_A_smbhb": float(best_A_smbhb),
        "min_chi2_smbhb": float(min_chi2_smbhb),
        "best_A_k3t2": float(best_A_k3t2),
        "min_chi2_k3t2": float(min_chi2_k3t2),
        "delta_chi2": float(delta_chi2),
        "ln_B": float(ln_B),
        "bump_freq": float(bump_freq),
        "pass": bool(ln_B > 0)
    }
    
    with open(out_dir / "bayes_factor.json", "w") as f:
        json.dump(results, f, indent=2)
        
    if ln_B > 0:
        print(f"PASS: ln B = {ln_B:.2f} (Favors K3xT2)")
    else:
        print(f"FAIL: ln B = {ln_B:.2f} (Favors SMBHB)")

if __name__ == "__main__":
    main()
