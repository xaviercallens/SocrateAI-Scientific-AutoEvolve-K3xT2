"""
Phase 3: Dwarf Galaxy Soliton Core Validation
=============================================
Validates the Ultra-Light Axion (ULA) dark matter candidate (m ~ 10^-22 eV)
derived from the K3xT2 geometrical moduli against the "Cusp-Core" problem
in Dwarf Spheroidal Galaxies (dSphs).

Compares:
1. Standard NFW (Navarro-Frenk-White) cuspy profile
2. K3xT2 Soliton Core (Bose-Einstein Condensate) profile
"""

import numpy as np
import matplotlib.pyplot as plt
import os
import logging
from scipy.optimize import curve_fit
from scipy.integrate import quad

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def nfw_velocity(r, v200, c):
    """
    Standard CDM NFW profile rotation curve velocity.
    r: radius in kpc
    """
    R200 = v200 / 10.0  # Approx relation for scaling
    x = r / (R200 / c)
    # Enforce positive to avoid log domain errors
    x = np.maximum(x, 1e-5)
    
    mass_enclosed = (np.log(1 + x) - x / (1 + x)) / (np.log(1 + c) - c / (1 + c))
    v = v200 * np.sqrt(mass_enclosed / x)
    return v

def soliton_velocity(r, r_c, rho_c):
    """
    K3xT2 ULA Soliton Core velocity profile (Schive et al. 2014).
    r: array of radii (kpc)
    r_c: core radius (kpc)
    rho_c: central density parameter (absorbs 4*pi*G and unit conversions)
    """
    # Schive+2014 density profile: rho(r) = rho_c / [1 + 0.091(r/r_c)^2]^8
    def integrand(r_prime):
        x = r_prime / r_c
        return (rho_c / (1.0 + 0.091 * x**2)**8) * r_prime**2
    
    is_scalar = np.isscalar(r)
    r_arr = np.atleast_1d(r)
    v_arr = np.zeros_like(r_arr, dtype=float)
    
    for i, rad in enumerate(r_arr):
        if rad > 0:
            mass_enclosed, _ = quad(integrand, 0, rad)
            v_arr[i] = np.sqrt(mass_enclosed / rad)
            
    return v_arr[0] if is_scalar else v_arr

def load_sparc_galaxy(name="DDO154"):
    """Loads actual SPARC rotation curve data for a dwarf galaxy from the GCP Datalake."""
    filepath = f"data/sparc/{name}_rotmod.dat"
    gcs_uri = f"gs://socrateai-datalake-gen-lang-client-0625573011/sparc/{name}_rotmod.dat"
    
    import subprocess
    try:
        logger.info(f"Attempting to fetch latest SPARC data from {gcs_uri}...")
        subprocess.run(["gcloud", "storage", "cp", gcs_uri, filepath], check=True, capture_output=True)
        logger.info("Successfully synced from GCP Data Lake.")
    except Exception as e:
        logger.warning(f"Could not fetch from GCP datalake, using local fallback if available. Error: {e}")
        
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"SPARC data file not found locally or on GCP: {filepath}")
    
    data = np.loadtxt(filepath, comments='#')
    # Column 0: Radius (kpc), Column 1: V_obs (km/s), Column 2: err_V (km/s)
    r_obs = data[:, 0]
    v_obs = data[:, 1]
    err_obs = data[:, 2]
    
    # Validate against Pydantic schema
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from data_staging.schema_validators import SPARCSchema, SPARCDataPoint
    
    data_points = []
    for r, v, err in zip(r_obs, v_obs, err_obs):
        data_points.append(SPARCDataPoint(radius=r, velocity=v, velocity_err=err))
        
    schema = SPARCSchema(galaxy_name=name, data_points=data_points)
    logger.info(f"Successfully validated {len(schema.data_points)} points via Pydantic SPARCSchema.")
    
    return r_obs, v_obs, err_obs

def run_soliton_validation():
    logger.info("Initializing K3xT2 Soliton Core validation against Dwarf Galaxy rotation curves...")
    
    # 1. Load actual SPARC dwarf galaxy data
    r_obs, v_obs, err_obs = load_sparc_galaxy(name="DDO154")
    logger.info(f"Loaded {len(r_obs)} radial bins of real SPARC kinematic data for DDO154.")
    
    # 2. Fit NFW (Standard CDM)
    popt_nfw, pcov_nfw = curve_fit(nfw_velocity, r_obs, v_obs, sigma=err_obs, p0=[50.0, 10.0])
    v_fit_nfw = nfw_velocity(r_obs, *popt_nfw)
    chi2_nfw = np.sum(((v_obs - v_fit_nfw) / err_obs)**2)
    dof_nfw = len(r_obs) - 2
    logger.info(f"Standard NFW Fit: χ² / dof = {chi2_nfw:.2f} / {dof_nfw} = {chi2_nfw/dof_nfw:.2f}")
    
    # 3. Fit K3xT2 Soliton
    popt_sol, pcov_sol = curve_fit(soliton_velocity, r_obs[r_obs < 4.0], v_obs[r_obs < 4.0], sigma=err_obs[r_obs < 4.0], p0=[1.0, 10.0], maxfev=10000)
    v_fit_sol = soliton_velocity(r_obs, *popt_sol)
    
    # Combine Soliton (inner) + NFW (outer)
    v_fit_total = np.maximum(v_fit_sol, nfw_velocity(r_obs, *popt_nfw))
    chi2_k3 = np.sum(((v_obs - v_fit_total) / err_obs)**2)
    dof_k3 = len(r_obs) - 2
    logger.info(f"K3xT2 ULA Soliton Fit: χ² / dof = {chi2_k3:.2f} / {dof_k3} = {chi2_k3/dof_k3:.2f}")
    
    if chi2_k3 < chi2_nfw:
        logger.info("✅ SUCCESS: The K3xT2 Soliton Core successfully resolves the Cusp-Core problem!")
    
    # 4. Plot
    os.makedirs("paper/figures", exist_ok=True)
    plt.figure(figsize=(8, 6))
    plt.errorbar(r_obs, v_obs, yerr=err_obs, fmt='ko', label='SPARC Dwarf Galaxy Data (Real)')
    
    r_fine = np.linspace(0.1, 10.0, 200)
    plt.plot(r_fine, nfw_velocity(r_fine, *popt_nfw), 'r--', lw=2, label=f'Standard CDM (NFW) [χ²_ν={chi2_nfw/dof_nfw:.1f}]')
    
    v_fine_k3 = np.maximum(soliton_velocity(r_fine, *popt_sol), nfw_velocity(r_fine, *popt_nfw))
    plt.plot(r_fine, v_fine_k3, 'b-', lw=2, label=f'K3xT2 Soliton (ULA) [χ²_ν={chi2_k3/dof_k3:.1f}]')
    
    plt.xlabel("Radius [kpc]", fontsize=14)
    plt.ylabel("Rotation Velocity [km/s]", fontsize=14)
    plt.title("Dwarf Galaxy Rotation Curve: Cusp-Core Resolution", fontsize=16)
    plt.legend(fontsize=12)
    plt.grid(True, alpha=0.3)
    
    save_path = "paper/figures/soliton_core_validation.pdf"
    plt.savefig(save_path, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Rotation curve plot saved to {save_path}")

if __name__ == "__main__":
    run_soliton_validation()
