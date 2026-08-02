"""
JWST High-z Constraints for Fuzzy Dark Matter
=============================================
Computes the likelihood of K3xT2 geometric Dark Matter predictions
against James Webb Space Telescope (JWST) high-z galaxy formation data.

Fuzzy Dark Matter (FDM) / Soliton Core models suppress small-scale
structure formation. JWST's discovery of massive galaxies at z > 10
provides a strict lower bound on the FDM mass scale m_FDM, and strongly
constrains the allowed values of Omega_m and the K3 spectral gap gamma.
"""

import math
import logging
import numpy as np
from typing import Dict, Any

logger = logging.getLogger(__name__)

class JWSTLikelihoodEngine:
    """
    JWST High-z Constraints Likelihood Engine for Fuzzy Dark Matter (FDM).
    
    Evaluates the likelihood of the K3xT2 geometric Dark Matter predictions
    against James Webb Space Telescope (JWST) high-z galaxy formation data.
    Fuzzy Dark Matter (FDM) suppresses small-scale structure formation, 
    but JWST's discovery of massive galaxies at z > 10 provides a strict 
    lower bound on the FDM mass scale m_FDM.
    """
    def __init__(self, target_m_fdm: float = 3e-22, sigma_m: float = 0.5e-22, target_omega_m: float = 0.315, sigma_omega: float = 0.015):
        self.target_m_fdm = target_m_fdm
        self.sigma_m = sigma_m
        self.target_omega_m = target_omega_m
        self.sigma_omega = sigma_omega
        logger.info(f"Initialized JWSTLikelihoodEngine with target m_FDM >= {self.target_m_fdm:e} eV")

    def __call__(self, theta: np.ndarray, cosmo: Dict[str, float], gamma_gap: float = 4.847) -> float:
        """
        Computes the log-likelihood for the FDM model based on JWST constraints.
        
        Args:
            theta: The raw MCMC parameter array (tau, cs1, cs2, cs3, poff, inst_A, inst_a).
            cosmo: Dictionary containing derived cosmology (must contain 'Omega_m').
            gamma_gap: Spectral mass gap of the topological vacuum (K3 property).
            
        Returns:
            float: Log-likelihood penalty.
        """
        omega_m = cosmo.get("Omega_m", 0.300)
        
        # We map the topological mass gap gamma to a physical mass scale proxy:
        # m_fdm_proxy ~ 1e-22 * (gamma_gap / 4.847)^2
        # (This implies a scaling from the string scale to the eV scale for the soliton)
        m_fdm_proxy = 1e-22 * (gamma_gap / 4.847)**2
        
        # We penalize configurations that yield FDM masses below the JWST threshold.
        # If m_FDM >= 3e-22 eV, structure is NOT suppressed at z~10, so it matches JWST.
        if m_fdm_proxy >= self.target_m_fdm:
            likelihood_m = 0.0
        else:
            likelihood_m = -0.5 * ((m_fdm_proxy - self.target_m_fdm) / self.sigma_m)**2
            
        # Omega_m consistency with high-z structure growth (requires ~0.3)
        likelihood_omega = -0.5 * ((omega_m - self.target_omega_m) / self.sigma_omega)**2
        
        ll_total = likelihood_m + likelihood_omega
        
        # Return 0 if exactly 0.0, else float
        return float(ll_total)

# Legacy alias for backwards compatibility if needed
def compute_jwst_fdm_likelihood(omega_m: float, gamma_gap: float, m_fdm_ev: float = 1e-22) -> float:
    engine = JWSTLikelihoodEngine()
    return engine(np.zeros(7), {"Omega_m": omega_m}, gamma_gap=gamma_gap)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = JWSTLikelihoodEngine()
    ll = engine(np.zeros(7), {"Omega_m": 0.295}, gamma_gap=4.847)
    print(f"JWST High-z Log-Likelihood for tau=0.50, P=19: {ll:.4f}")
