# Claude Sonnet Execution Pipeline (Phase 9)

**Date**: 2026-07-31  
**Project**: K3×T² Cosmological Model Validation

This document is the execution manifest for the Claude Sonnet model to finalize the remaining workstreams of Phase 9. You (Claude Sonnet) are taking over after Antigravity has completed WS1, WS2, WS3, WS5, and WS7.

## Current State

The following workstreams have been executed and the results have been documented in the `outputs/` directory:
- **WS1 (KiDS S8 Cross-Val)**: FAILED. High tension ($\approx 14\sigma$) between K3×T² prediction ($S_8 = 0.830$) and KiDS-1000 data ($S_8 \approx 0.760$). Documented in `outputs/ws1/FAIL_REPORT.md`.
- **WS2 (DESI BAO Cross-Check)**: PASSED. Sub-0.1% residuals against `classy`.
- **WS3 (NANOGrav Spectral Shape)**: FAILED. Strong evidence against the topological bump at 24.18 nHz ($\ln\mathcal{B} \approx -51.58$). Documented in `outputs/ws3/FAIL_REPORT.md`.
- **WS5 (Unbiased Bayesian Evidence)**: PASSED. Train/Test split cross-validation showed $\ln\mathcal{Z} \approx 14.42$, confirming no Occam penalty for the non-degenerate parameters.
- **WS7 (5D Fisher Information Matrix)**: FAILED (Degenerate). Exact Fisher Information Matrix calculation shows zero curvature for the angular parameters ($\theta_{cs}, \phi_{cs}$) and the discrete Picard offset, confirming the previously suspected spherical degeneracy. Documented in `outputs/ws7/FISHER_REPORT.md`.

## Tasks for Claude Sonnet

You must execute the remaining workstreams exactly as specified below.

### 1. Execute WS6: Euclid Q1 Photometric Redshift Distribution Analysis
**Objective**: Validate the Euclid Q1 data and compare the $n(z)$ distribution.
**Steps**:
1. Read the `MER_FINAL_CATALOG` FITS files from `gs://socrateai-datalake-gen-lang-client-0625573011/euclid_q1/tile_*`.
2. Write a script `scripts/ws6_euclid_photo_z.py` to extract `PHOT_Z_MEDIAN` and build a histogram.
3. Compare the observed $dN/dz$ against the K3×T² volume element $dV/dz d\Omega$.
4. Check the `s8_joint_means.txt` and `s8_joint_covariance.txt` in `data/euclid_q1/` to perform an independent clustering audit.
5. Create `outputs/ws6/n_z_distribution.pdf` and `outputs/ws6/dndz_chi2.json`.

### 2. Execute WS4: Lean 4 Formal Proof Hardening
**Objective**: Replace the vacuous runtime `#eval` checks with strict Lean 4 mathematical proofs.
**Steps**:
1. Open `lean_oracle/GeneratedK3.lean`.
2. Implement **Theorem 1 (Picard Bound)** using `omega`.
3. Implement **Theorem 2 (Euler Characteristic)**.
4. Implement **Theorem 3 (Hodge Symmetry)**.
5. Formalize **Theorem 4 (Spectral-Picard Bridge)** proving that the specific adjacency matrix corresponds to Picard rank 19.
6. Verify all proofs compile via `lake build` in the `lean_oracle/` directory.

### 3. Deploy the GCP Web Dashboard
**Objective**: Deploy the FastAPI backend and React frontend dashboard to Google Cloud Run to allow peer-review access.
**Steps**:
1. Review the architecture specification in `specs/phase9_dashboard_specification.md`.
2. Scaffold the FastAPI backend and the React frontend in the `dashboard/` directory.
3. Add the `Dockerfile` and `cloudbuild.yaml`.
4. Deploy the service to GCP using `gcloud run deploy`.

## Definition of Done for Claude
- `outputs/ws6/dndz_chi2.json` exists.
- `lean_oracle/GeneratedK3.lean` contains no `sorry` and builds successfully.
- The Cloud Run service URL is active and correctly visualizes the outputs of WS1-WS7.
