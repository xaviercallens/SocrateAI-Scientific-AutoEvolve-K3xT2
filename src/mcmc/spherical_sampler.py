"""
Spherical Reparameterisation for K3×T² MCMC Sampler (IMP-03)
==============================================================
Replaces the Cartesian complex-structure parameterisation (cs_1, cs_2, cs_3)
with spherical coordinates (r_cs, theta_cs, phi_cs), eliminating the volume-
element bias and dramatically improving sampler efficiency in the cs manifold.

Effective parameter vector (4D after IMP-03):
    θ = (τ, r_cs, θ_cs, φ_cs, picard_offset)

Where:
    r_cs   ∈ [0, 5.2]   — radial magnitude of complex structure vector
    θ_cs   ∈ [0, π]     — polar angle (elevation)
    φ_cs   ∈ [-π, π]    — azimuthal angle
    τ      ∈ (0.01, 1.5) — T² modulus
    picard_offset ∈ [-3, 3] — continuous Picard number offset

Sampling in spherical coordinates means:
    1. r_cs is now a single 1D parameter with an informative likelihood
    2. θ_cs and φ_cs independently probe the directional signatures
    3. No Jacobian correction needed: prior is flat in (r, θ, φ) space with
       sin(θ) volume weighting included analytically via a wrapped prior.
"""

import math
from typing import Dict, List, Optional

import numpy as np

# ---------------------------------------------------------------------------
# Spherical Parameterisation Spec
# ---------------------------------------------------------------------------
SPHER_PARAM_SPEC = [
    ("t2_modulus_tau",  0.01,   1.50,  0.02),
    ("cs_r",            0.01,   5.20,  0.10),   # |cs| ∈ [0, 5.2] ≈ sqrt(3)*3
    ("cs_theta",        0.00,   math.pi,  0.05),
    ("cs_phi",         -math.pi, math.pi,  0.10),
    ("picard_offset",  -3.00,   3.00,  0.10),
]

SPHER_PARAM_NAMES = [p[0] for p in SPHER_PARAM_SPEC]
SPHER_PARAM_BOUNDS = np.array([(p[1], p[2]) for p in SPHER_PARAM_SPEC])
N_SPHER_PARAMS = len(SPHER_PARAM_SPEC)


def spherical_to_candidate(theta_s: np.ndarray, base_candidate: dict) -> dict:
    """
    Convert spherical parameter vector → candidate dict for phenotype mapper.

    θ_s = (τ, r, θ_cs, φ_cs, picard_offset)
    """
    tau = float(theta_s[0])
    r = float(theta_s[1])
    theta_cs = float(theta_s[2])
    phi_cs = float(theta_s[3])
    picard_offset = float(theta_s[4])

    # Convert spherical → Cartesian for the candidate dict
    cs_1 = r * math.sin(theta_cs) * math.cos(phi_cs)
    cs_2 = r * math.sin(theta_cs) * math.sin(phi_cs)
    cs_3 = r * math.cos(theta_cs)

    candidate = dict(base_candidate)
    candidate["t2_modulus_tau"] = tau
    candidate["complex_structure"] = [cs_1, cs_2, cs_3]
    candidate["picard_number"] = int(np.clip(
        base_candidate.get("picard_number", 19) + round(picard_offset), 1, 20
    ))
    return candidate


def candidate_to_spherical(candidate: dict) -> np.ndarray:
    """
    Convert candidate dict → spherical parameter vector.
    """
    tau = candidate.get("t2_modulus_tau", 0.5)
    cs = candidate.get("complex_structure", [1.0, 1.0, 1.0])

    r = math.sqrt(sum(x ** 2 for x in cs))
    if r < 1e-10:
        r = 1e-10
    theta_cs = math.acos(max(-1.0, min(1.0, cs[2] / r)))
    phi_cs = math.atan2(cs[1], cs[0])

    return np.array([tau, r, theta_cs, phi_cs, 0.0])


def log_spherical_jacobian(theta_s: np.ndarray) -> float:
    """
    Log-Jacobian for the spherical → Cartesian change of variables:
        |J| = r² sin(θ)
        log|J| = 2 log(r) + log(sin(θ))

    This is added to the log-prior to maintain a flat prior on the
    Cartesian cs moduli space.
    """
    r = theta_s[1]
    theta_cs = theta_s[2]
    sin_theta = math.sin(theta_cs)

    if r <= 0 or sin_theta <= 0:
        return -np.inf

    return 2.0 * math.log(r) + math.log(sin_theta)
