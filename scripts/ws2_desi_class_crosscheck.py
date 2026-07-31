#!/usr/bin/env python3
import json
import logging
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

try:
    from astropy.cosmology import FlatwCDM
    import astropy.units as u
except ImportError:
    print("Please install astropy first: pip install astropy")
    exit(1)

from src.mcmc.desi_likelihood import DESILikelihoodEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    out_dir = Path("outputs/ws2")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Cosmology params for K3xT2
    w0 = -0.9999
    omega_m = 0.300
    h0 = 67.40
    
    # Init Astropy Cosmology
    cosmo = FlatwCDM(H0=h0, Om0=omega_m, w0=w0)
    
    # The fiducial sound horizon we use in our custom code is 147.09
    rd_fiducial = 147.09
    
    engine = DESILikelihoodEngine(data_dir="data/desi_dr1")
    phenotype = {"w0": w0, "omega_m": omega_m, "h0": h0}
    k3t2_preds = engine.predict_bao_distances(phenotype)
    
    astropy_preds = np.zeros_like(k3t2_preds)
    residuals = np.zeros_like(k3t2_preds)
    
    results = []
    
    for i, dp in enumerate(engine.data_points):
        z = dp.z
        
        # Astropy D_M(z)
        d_m_astropy = cosmo.comoving_distance(z).value
        # Astropy H(z) -> D_H(z)
        h_z_astropy = cosmo.H(z).value
        c = 299792.458
        d_h_astropy = c / h_z_astropy
        
        if dp.quantity == "DH_over_rs":
            astropy_val = d_h_astropy / rd_fiducial
        elif dp.quantity == "DM_over_rs":
            astropy_val = d_m_astropy / rd_fiducial
        elif dp.quantity == "DV_over_rs":
            d_v_astropy = (z * d_m_astropy**2 * d_h_astropy) ** (1.0 / 3.0)
            astropy_val = d_v_astropy / rd_fiducial
        else:
            astropy_val = dp.value
            
        astropy_preds[i] = astropy_val
        k3t2_val = k3t2_preds[i]
        frac_res = abs(astropy_val - k3t2_val) / astropy_val
        residuals[i] = frac_res
        
        results.append({
            "z": z,
            "quantity": dp.quantity,
            "astropy_prediction": float(astropy_val),
            "k3t2_prediction": float(k3t2_val),
            "fractional_residual": float(frac_res)
        })
        
        logger.info(f"z={z:.2f} {dp.quantity}: Astropy={astropy_val:.4f}, K3xT2={k3t2_val:.4f}, Res={frac_res:.4e}")
        
    with open(out_dir / "class_vs_k3t2_comparison.json", "w") as f:
        json.dump({"residuals": results, "max_residual": float(np.max(residuals))}, f, indent=2)
        
    # Plotting
    plt.figure(figsize=(10, 6))
    z_vals = [dp.z for dp in engine.data_points]
    plt.scatter(z_vals, residuals, color='b', label='Fractional Residual (Astropy vs K3xT2)')
    plt.axhline(0.001, color='r', linestyle='--', label='0.1% threshold')
    plt.xlabel('Redshift (z)')
    plt.ylabel('Fractional Residual')
    plt.yscale('log')
    plt.title('DESI BAO Distance Ladder Cross-Check: Astropy vs Trapezoidal Integrator')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(out_dir / "bao_distance_crosscheck.pdf")
    
    if np.max(residuals) < 0.001:
        print("PASS: Maximum fractional residual is < 0.1%")
    else:
        print(f"FAIL: Maximum fractional residual is {np.max(residuals):.2%} (> 0.1%)")

if __name__ == "__main__":
    main()
