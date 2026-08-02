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

import numpy as np

def compute_jwst_fdm_likelihood(omega_m: float, gamma_gap: float, m_fdm_ev: float = 1e-22) -> float:
    """
    Computes a mock Gaussian likelihood for the FDM model based on JWST
    high-z luminous galaxy density constraints.
    
    Args:
        omega_m: Matter density parameter (derived from K3 Picard rank)
        gamma_gap: Spectral mass gap of the topological vacuum
        m_fdm_ev: FDM particle mass in eV (standard benchmark ~10^-22 eV)
        
    Returns:
        float: log-likelihood penalty for the configuration.
    """
    # JWST requires a sufficiently early onset of structure formation.
    # If m_fdm is too light (< 1e-22), structure is too suppressed.
    # We map the topological mass gap gamma to a physical mass scale proxy:
    # m_fdm_proxy ~ 1e-22 * (gamma_gap / 4.847)^2
    
    m_fdm_proxy = 1e-22 * (gamma_gap / 4.847)**2
    
    # JWST constraint (approximate lower bound from 2024 surveys):
    # m_FDM > 3e-22 eV to produce enough z~10 massive galaxies.
    target_m_fdm = 3e-22
    
    # We penalize configurations that yield FDM masses below the JWST threshold.
    if m_fdm_proxy >= target_m_fdm:
        likelihood_m = 0.0 # Pass
    else:
        # Sharp half-Gaussian penalty
        sigma_m = 0.5e-22
        likelihood_m = -0.5 * ((m_fdm_proxy - target_m_fdm) / sigma_m)**2
        
    # Omega_m consistency with high-z structure growth (requires ~0.3)
    target_omega_m = 0.315
    sigma_omega = 0.015
    likelihood_omega = -0.5 * ((omega_m - target_omega_m) / sigma_omega)**2
    
    return float(likelihood_m + likelihood_omega)

if __name__ == "__main__":
    # Test with standard K3xT2 stable vacuum parameters
    # picard = 19 -> omega_m ~ 0.295, gamma ~ 4.847
    ll = compute_jwst_fdm_likelihood(omega_m=0.295, gamma_gap=4.847)
    print(f"JWST High-z Log-Likelihood for tau=0.50, P=19: {ll:.4f}")
