# K3×T² Experimental Validation Implementation Plan

**Version:** 1.0  
**Date:** 2026-07-31  
**Target Executors:** Gemini 3.6 Flash (High), Gemini 3.1 Pro  
**Repository:** `SocrateAI-Scientific-AutoEvolve-K3xT2`

---

## Overview

This document defines **5 independent experimental validation tests** that must be implemented against real observational data already present in the project's data lake. Each test is self-contained, has explicit inputs/outputs, and can be executed by a low-tier model without requiring prior context about the theoretical framework.

All tests share the same MAP cosmology from the 300-generation Deep Burn:

```python
MAP_COSMOLOGY = {
    "w0": -0.99992,
    "Omega_m": 0.300,
    "H0": 67.40,       # km/s/Mpc
    "S8": 0.830,
    "sigma8": 0.830,    # since S8 = sigma8 * sqrt(Omega_m/0.3)
    "Omega_b_h2": 0.02237,
    "r_s": 147.05,      # Mpc, sound horizon at drag
}
```

---

## Experiment 1: DESI BAO χ² Redshift Evolution Test

### Purpose
Test whether the K3×T² MAP cosmology fits the DESI 2024 BAO distance measurements better or worse than standard ΛCDM.

### Input Data
- `data/desi_dr1/desi_2024_gaussian_bao_ALL_GCcomb_mean.txt` — 12 BAO measurements at 7 redshift bins (z=0.295 to z=2.33). Format: `[z] [value] [quantity_type]` where quantity_type is `DM_over_rs`, `DH_over_rs`, or `DV_over_rs`.
- `data/desi_dr1/desi_2024_gaussian_bao_ALL_GCcomb_cov.txt` — 12×12 covariance matrix (space-separated floats, no header).

### Implementation Steps

1. **Parse the data files.** Load the 12 mean values into a numpy array. Load the 12×12 covariance matrix. Verify shape `(12,)` and `(12, 12)`.

2. **Implement a flat wCDM distance calculator.** For a given `(Omega_m, H0, w0)`:
   - Compute `E(z) = sqrt(Omega_m * (1+z)^3 + (1-Omega_m) * (1+z)^(3*(1+w0)))` 
   - Comoving distance: `D_M(z) = (c/H0) * integral_0^z dz'/E(z')` using `numpy.trapz` with ≥1000 steps.
   - Hubble distance: `D_H(z) = c / (H0 * E(z))`
   - Volume-averaged distance: `D_V(z) = (z * D_M^2 * D_H)^(1/3)`
   - Divide each by `r_s = 147.05` to get `DM_over_rs`, `DH_over_rs`, `DV_over_rs`.

3. **Compute χ² for three models:**
   - K3×T² MAP: `(Omega_m=0.300, H0=67.40, w0=-0.99992)`
   - ΛCDM Planck: `(Omega_m=0.315, H0=67.36, w0=-1.0)`
   - w0waCDM DESI bestfit: `(Omega_m=0.295, H0=67.97, w0=-0.55, wa=-1.32)` — for w0waCDM, use `E(z)^2 = Omega_m*(1+z)^3 + Omega_de * a^(-3*(1+w0+wa)) * exp(-3*wa*(1-a))` where `a=1/(1+z)`.
   - For each: `chi2 = (data - theory)^T @ cov_inv @ (data - theory)`

4. **Report per-bin pull** = `(data_i - theory_i) / sqrt(cov_ii)` for each of the 12 measurements.

5. **Report high-z diagnostic:** Compute χ² restricted to bins with z > 1.3 only (using the corresponding sub-block of the covariance).

### Output File
`outputs/phase8/desi_bao_chi2_test.json` with keys:
```json
{
  "models": {
    "K3xT2": {"chi2": ..., "chi2_per_dof": ...},
    "LCDM": {"chi2": ..., "chi2_per_dof": ...},
    "w0waCDM": {"chi2": ..., "chi2_per_dof": ...}
  },
  "delta_chi2_k3t2_vs_lcdm": ...,
  "per_bin_pulls_k3t2": [...],
  "high_z_chi2_k3t2": ...,
  "high_z_chi2_lcdm": ...
}
```

### Definition of Done (DoD)
- [ ] Script runs without errors: `python3 scripts/run_p1_desi_bao_test.py`
- [ ] Output JSON exists at `outputs/phase8/desi_bao_chi2_test.json`
- [ ] All three model χ² values are finite positive numbers
- [ ] Per-bin pulls are all within ±5σ (sanity check)
- [ ] χ²/dof is between 0.1 and 10 for all models (sanity check)

### Validation
- Cross-check: at z=0.510, DM_over_rs should be ~13.62. For ΛCDM with (0.315, 67.36), the theory should produce a value within 2% of this.
- The K3×T² and ΛCDM χ² values should be *similar* (since w0≈-1 in both). If Δχ² > 20, there is likely a bug in the distance calculator.

---

## Experiment 2: Real FIM Curvature at τ=0.50

### Purpose
Replace the tautological synthetic FIM with a computation using the real DESI BAO likelihood.

### Implementation Steps

1. **Define a mapping from the 5D moduli `(tau, cs_1, cs_2, cs_3, picard_offset)` to cosmological parameters:**
   ```python
   w0 = -1.0 + 0.01 * (tau - 0.50)
   Omega_m = 0.300 + 0.005 * cs_1
   H0 = 67.40 + 0.2 * cs_2
   ```
   (cs_3 and picard_offset contribute at sub-percent level; add `0.001*cs_3` to Omega_m and `0.05*p_off` to H0.)

2. **Evaluate the DESI BAO log-likelihood** (same χ² as Experiment 1, but as `-0.5 * chi2`) at the MAP point `(0.50, -0.5178, -1.5592, 1.6371, -0.4929)`.

3. **Use `numdifftools.Hessian`** with `step=1e-4` to compute the full 5×5 Hessian of the negative log-likelihood at the MAP point.

4. **Compute eigenvalues** of the Hessian via `numpy.linalg.eigvalsh`. All eigenvalues positive → local maximum confirmed.

5. **Extract Fisher Information along tau:** `F_tau = H[0,0]`. Cramér-Rao bound: `sigma_tau >= 1/sqrt(F_tau)`.

### Output File
`outputs/phase8/fisher_curvature_results_real.json`

### DoD
- [ ] Script runs without errors
- [ ] Hessian is a 5×5 matrix with all finite values
- [ ] Eigenvalue analysis completes (all values printed)
- [ ] Fisher Information along tau is reported
- [ ] Output JSON saved

### Validation
- The Hessian should be approximately diagonal (off-diagonal terms small relative to diagonal) because the BAO measurements at different redshifts are mostly independent.
- `F_tau` should be positive but modest (not 100.0 — that was the synthetic artifact).

---

## Experiment 3: KiDS-1000 B-Mode Null Test

### Purpose
Test whether real KiDS-1000 cosmic shear B-modes are consistent with zero, or show evidence of parity violation from topological defects.

### Input Data
- `data/euclid_q2/kids1000_bandpowers_EE.json` — Contains `bandpowers_EE`, `bandpowers_BB`, `sigma_EE` arrays, each shape `(8, 5)` = 8 ell-bins × 5 tomographic bins.

### Implementation Steps

1. **Load the JSON.** Extract `bandpowers_BB` and `sigma_EE` as numpy arrays.

2. **Global null test:** Compute `chi2_null = sum((BB_ij / sigma_ij)^2)` over all 40 data points. Compare against χ²(40 dof).

3. **Per-ell B/E ratio:** For each of the 8 ell-bins, compute `mean(|BB|) / mean(EE)` averaged over tomographic bins.

4. **Tomographic correlation:** Compute `numpy.corrcoef(BB.T)` — a 5×5 matrix. If B-modes are from noise, cross-tomo correlations should be ~0. If from systematics or physics, they'll be correlated.

5. **Report p-value** using `scipy.stats.chi2.sf(chi2_null, 40)`.

### Output File
`outputs/phase8/kids_bmode_null_test.json`

### DoD
- [ ] Script runs without errors
- [ ] χ²/dof reported and is between 0.1 and 5.0
- [ ] B/E ratios reported for all 8 ell-bins
- [ ] Tomographic correlation matrix is 5×5
- [ ] Output JSON saved

### Validation
- Expected result: B-modes consistent with zero (χ²/dof ≈ 1). This is the standard ΛCDM prediction.
- BB/EE ratios should be < 0.1 in all bins (B-modes are much smaller than E-modes).
- A B/E ratio > 0.3 at any ell-bin would indicate a serious problem (likely systematic, not Oligon physics).

---

## Experiment 4: KiDS×DESI Joint S8 Tension Diagnostic

### Purpose
Test whether the K3×T² prediction (S8=0.830) is consistent with the published weak lensing S8 measurements from multiple surveys.

### Input Data
- `data/euclid_q2/s8_joint_means.txt` — Row vector: `[KiDS-1000, DES-Y3, KiDS-Legacy, Planck]` = `[0.759, 0.776, 0.776, 0.832]`
- `data/euclid_q2/s8_joint_covariance.txt` — 4×4 diagonal covariance matrix.
- `data/euclid_q2/s8_wl_measurements.json` — Full metadata for each survey.

### Implementation Steps

1. **Load the 4 S8 measurements** and the 4×4 covariance matrix.

2. **Compute χ² for K3×T² prediction (S8=0.830):**
   ```python
   s8_data = [0.759, 0.776, 0.776, 0.832]
   s8_prediction = 0.830  # K3xT2
   residuals = s8_data - s8_prediction
   chi2 = residuals @ cov_inv @ residuals
   ```

3. **Compute χ² for ΛCDM Planck prediction (S8=0.832)** and for **the weighted mean of the WL surveys**.

4. **Compute the S8 tension:** What is the combined tension between the K3×T² prediction and the WL surveys (KiDS, DES, KiDS-Legacy)?
   ```python
   # WL-only (first 3 surveys)
   wl_mean = weighted_mean(s8_data[:3], cov[:3,:3])
   tension_sigma = abs(0.830 - wl_mean) / error_of_wl_mean
   ```

5. **Report:** Does K3×T² worsen or resolve the S8 tension?

### Output File
`outputs/phase8/s8_tension_diagnostic.json`

### DoD
- [ ] Script runs without errors
- [ ] χ² values for K3×T² and ΛCDM are both reported
- [ ] Tension in sigma between K3×T² and WL-only mean is reported
- [ ] Verdict string: "worsens tension" / "same as LCDM" / "partially resolves" / "fully resolves"
- [ ] Output JSON saved

### Validation
- K3×T² predicts S8=0.830, Planck says 0.832, KiDS says 0.759. The K3×T² prediction is ~3σ from KiDS, same as Planck. So the expected verdict is **"same as LCDM — does not resolve the S8 tension"**. If your script reports "fully resolves", there is a bug.

---

## Experiment 5: Euclid Q1 S8 Provenance Clarification

### Purpose
Fix the manuscript claim that S8=0.828±0.011 was "measured from Euclid Q1 data". The Q1 MER catalogs contain galaxy positions and fluxes, not shear measurements. This test clarifies what the Euclid Q1 data actually constrains.

### Implementation Steps

1. **Load the Euclid Q1 catalogs** using `astropy.io.fits` from `data/euclid_q1/tile_*/`.

2. **Report what columns actually exist** in the FITS tables. Print column names from `hdul[1].columns`.

3. **Compute the angular galaxy clustering** w(θ) from the existing script (this part is already correct).

4. **Fit a simple power-law** `w(θ) = A_w * θ^(-δ)` to the measured w(θ). Report `A_w` and `δ`.

5. **Estimate Ωm from clustering amplitude** using the Limber approximation: `A_w ∝ b_g^2 * σ_8^2 * Ωm`. Marginalize over galaxy bias `b_g ∈ [0.5, 3.0]` and report the Ωm posterior.

6. **Update the manuscript text** in `paper/sections/04_results.tex` to replace the current S8 claim with:
   ```latex
   The Euclid Q1 galaxy angular clustering analysis yields a power-law 
   slope $\delta = ...$ and amplitude $A_w = ...$, consistent with the 
   $K_3 \times T^2$ predicted matter clustering at Picard number $P=19$. 
   The $S_8 = 0.828 \pm 0.011$ constraint is derived from Planck 2018 
   CMB primary anisotropy data and is quoted here as an external 
   consistency benchmark, not as an independent Euclid weak lensing measurement.
   ```

### DoD
- [ ] FITS column names printed (should NOT contain `e1`, `e2`, `GAMMA1`, `GAMMA2`)
- [ ] w(θ) power-law fit produces finite `A_w` and `δ`
- [ ] Manuscript text updated with transparent provenance
- [ ] No claim of "independent Euclid S8 measurement" remains in any `.tex` file

### Validation
- The FITS catalogs should contain `RIGHT_ASCENSION`, `DECLINATION`, and flux columns — NOT ellipticity/shear columns. If shear columns ARE present, the provenance concern is moot and a real S8 measurement may be possible.
- The power-law slope δ should be approximately 0.7–0.9 (consistent with standard galaxy clustering).

---

## Execution Order

```
P0 (must do first):
  → Experiment 2 (Real FIM)
  → Experiment 5 (S8 Provenance)

P1 (highest scientific value):
  → Experiment 1 (DESI BAO χ²)

P2 (additional evidence):
  → Experiment 3 (B-mode null test)
  → Experiment 4 (S8 tension diagnostic)
```

Each experiment is independent and can be run in any order within its priority tier.

---

## File Naming Convention

All scripts go in `scripts/`:
- `run_p1_desi_bao_test.py`
- `run_p0_fisher_real.py`
- `run_p2_kids_bmode_test.py`
- `run_p2_s8_tension_test.py`
- `run_p0_euclid_provenance.py`

All outputs go in `outputs/phase8/`:
- `desi_bao_chi2_test.json`
- `fisher_curvature_results_real.json`
- `kids_bmode_null_test.json`
- `s8_tension_diagnostic.json`
- `euclid_q1_column_audit.json`
