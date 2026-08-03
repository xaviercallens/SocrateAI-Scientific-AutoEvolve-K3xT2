"""
Phenotype Mapper for AlphaEvolve K3×T² — EFT-Derived (v3.0)
=============================================================
Translates K3×T² abstract moduli into cosmological parameters
and falsifiable observational signatures.

VERSION HISTORY:
    v1.0 — Ad-hoc linear ansätze (rejected by peer review)
    v2.0 — IMP-01: Complex structure degeneracy-breaking via
           spherical decomposition (θ, φ) → anisotropic signatures
    v3.0 — EFT-derived: All cosmological observables computed from
           the Type IIA scalar potential V(τ, φ) via the Cooper s₁₀
           Picard-Fuchs periods (Section 3b of the paper)

PEER REVIEW RESPONSE:
    The v1.0/v2.0 mapper contained tuned linear coefficients:
        w_0 = -0.9745 + 0.01 * (tau - 0.5)
        omega_m = 0.2954 + 0.02 * (19 - picard) + ...
    with no derivation from the compactification geometry. This was
    correctly identified as a "black box" by the reviewer. The v3.0
    mapper delegates to src.eft.scalar_potential, which computes V(τ)
    from the Picard-Fuchs ODE and derives w₀ from the slow-roll
    parameter ε = (V'/V)² M²_Pl / 2. See the paper's Section 3b
    (Effective Field Theory from K3×T² Compactification) for the
    mathematical derivation.
"""

import math
import sys
import os

# Add parent to path for src.eft import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from eft.scalar_potential import map_k3_to_cosmology_eft
except ImportError as e:
    raise RuntimeError(
        "CRITICAL AUDIT FAILURE (TASK 12-02): EFT scalar potential module could not be loaded. "
        "The legacy ad-hoc phenotype mapper (v1.0/v2.0) has been permanently removed "
        "due to scientific invalidity (algebraic contrivance). You must ensure "
        "'src.eft.scalar_potential' is in your PYTHONPATH."
    ) from e


def map_k3_to_cosmology(candidate: dict) -> dict:
    """
    Translates the abstract K3×T² moduli into effective cosmological
    parameters, using the EFT-derived scalar potential.

    Parameters
    ----------
    candidate : dict
        Must contain:
            picard_number       (int)   Picard number of the K3 surface [1–20]
            t2_modulus_tau      (float) T² complex structure modulus τ ∈ (0, 1.5)
            complex_structure   (list)  3-vector [cs_1, cs_2, cs_3] in ℝ³

    Returns
    -------
    dict
        Cosmological + astrophysical observables with EFT provenance.
    """
    return map_k3_to_cosmology_eft(candidate)
