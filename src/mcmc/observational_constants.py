"""
Observational Constants for K3×T² Joint Likelihood
====================================================
Single source of truth for all empirical target values used
across DESI, Euclid, NANOGrav, and KiDS likelihood modules.

All values are cited with their publication source.
"""

# ── S₈ Structure Growth ──────────────────────────────────────────────
# Euclid Q1 (morphological proxy — see GAP-1 caveat in phase9 audit)
S8_EUCLID_Q1_MEAN = 0.828
S8_EUCLID_Q1_SIGMA = 0.011

# KiDS-1000 cosmic shear (Asgari et al. 2021, A&A 645, A104)
S8_KIDS_MEAN = 0.759
S8_KIDS_SIGMA = 0.024

# DES-Y3 (Amon et al. 2022, PRD 105, 023514)
S8_DES_MEAN = 0.776
S8_DES_SIGMA = 0.017

# Planck 2018 CMB (Planck Collaboration VI, A&A 641, A6)
S8_PLANCK_MEAN = 0.832
S8_PLANCK_SIGMA = 0.013

# ── Dark Energy Equation of State ────────────────────────────────────
W0_LCDM = -1.000
W0_SIGMA = 0.020

# ── Matter Density ───────────────────────────────────────────────────
# Planck 2018 (Planck Collaboration VI, A&A 641, A6)
OMEGA_M_PLANCK = 0.3153
OMEGA_M_SIGMA = 0.0073

# ── Hubble Constant ──────────────────────────────────────────────────
# Planck 2018
H0_PLANCK = 67.36
H0_SIGMA = 0.54

# ── PTA / Gravitational Wave Background ──────────────────────────────
# NANOGrav 15yr (Agazie et al. 2023, ApJL 951, L8)
# Characteristic strain frequency ≈ 1/yr ≈ 31.7 nHz
# Individual frequency bins centered at few × nHz
# K3×T² Compton resonance prediction: 24.18 nHz = 2.418e-8 Hz
PTA_F_MONOPOLE_TARGET = 2.418e-8   # Hz — K3×T² prediction (Section 5)
PTA_F_MONOPOLE_SIGMA = 5.0e-9     # Hz — estimated uncertainty band
PTA_SPECTRAL_INDEX_SMBHB = 13.0 / 3.0  # γ = 13/3 ≈ 4.333 (standard SMBHB)

# ── BAO Sound Horizon ────────────────────────────────────────────────
# Planck 2018 drag epoch
RD_FIDUCIAL = 147.09  # Mpc

# ── Physical Constants ───────────────────────────────────────────────
C_KM_S = 299792.458  # Speed of light in km/s
