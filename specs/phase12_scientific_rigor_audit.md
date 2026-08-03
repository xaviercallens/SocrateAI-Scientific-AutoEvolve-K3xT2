# 🔬 Phase 12: Scientific Rigor & Deep Physics Audit
> **Version**: 1.0.0 | **Date**: 2026-08-03 | **Target**: Full Elimination of Bayesian and Architectural Inconsistencies

---

## Part A: Deep Scientific Gaps Identified

Following the successful implementation of the Phase 11 First-Principles physics derivations (String Scale Normalization, FDM Mass, and PyCCL Boltzmann integration), a deeper architectural audit reveals severe flaws in the Bayesian likelihood composition and Simulation-Based Inference (SBI) pipelines. If uncorrected, these issues will artificially inflate the Bayesian evidence and invalidate the machine learning surrogate models.

### 🔴 CRITICAL GAPS (Must fix for statistical validity)

| ID | Component | Scientific Finding | Impact |
|----|-----------|--------------------|--------|
| **12.A1** | `desi_likelihood.py` | **Bayesian Double Counting:** The `DESILikelihoodEngine` internally computes and adds both the NanoGrav (PTA) and Euclid (Weak Lensing) likelihoods. However, `run_p2_joint_nested_sampling.py` explicitly adds its own rigorous versions of these likelihoods. | Double-counts the Euclid and PTA constraints. This artificially narrows the posterior width and fatally corrupts the Bayesian Evidence ($\ln \mathcal{Z}$). |
| **12.A2** | `phenotype_mapper.py` & `run_phase7_sbi.py` | **Legacy Non-EFT Mapping Active:** `run_phase7_sbi.py` calls the old `map_k3_to_cosmology` which falls back to the deprecated v1.0 ad-hoc linear ansätze (explicitly noted as rejected in peer review), bypassing the rigorous `scalar_potential` mappings entirely. | The SBI Normalizing Flow is training on fake, algebraically-contrived physics rather than the true K3×T² Effective Field Theory. |

### 🟠 HIGH-PRIORITY GAPS (Required for ML convergence)

| ID | Component | Scientific Finding | Impact |
|----|-----------|--------------------|--------|
| **12.B1** | `run_phase7_sbi.py` | **SBI Convergence Failure:** The Masked Autoregressive Flow (MAF) is trained on only $N=2000$ forward simulations across a 5-dimensional parameter space. | Density estimation via MAF in 5D requires $\mathcal{O}(10^5)$ samples. The current posterior will be severely under-dispersed and mathematically invalid. |

---

## Part B: Improvement Plan & Remediation Steps

### TASK 12-01: Eradicate Likelihood Double-Counting
**Target**: `src/mcmc/desi_likelihood.py`
**Remediation**:
1. Remove `nanograv_log_likelihood` and `euclid_log_likelihood` methods entirely from the `DESILikelihoodEngine`.
2. Update `log_likelihood` to return strictly the DESI BAO $\chi^2$ and normalisation.
3. Ensure the return object `DESILikelihoodResult` correctly reports `ndof` based solely on the BAO measurements (12).
**Validation**:
```bash
# Verify the DESI engine no longer returns Euclid/PTA likelihoods
python -c "from src.mcmc.desi_likelihood import DESILikelihoodEngine; eng=DESILikelihoodEngine(); res=eng.log_likelihood({'w0': -1.0, 'omega_m': 0.3, 'h0': 67}); assert res.ndof == 12"
```

### TASK 12-02: Force Strict EFT Provenance
**Target**: `src/alpha_evolve/phenotype_mapper.py`
**Remediation**:
1. Delete the "Fallback: simplified EFT formulae" completely.
2. If `map_k3_to_cosmology_eft` fails to import, raise a fatal `RuntimeError` rather than silently continuing with unphysical ansätze.
3. Update `scripts/run_phase7_sbi.py` to ensure it passes the full 10D parameters (or at least `picard_number` and `tau` correctly formatted) to the EFT mapper.
**Validation**:
```bash
# The legacy fallback must not exist; mapping must strictly route to EFT
grep -q "Fallback: simplified EFT formulae" src/alpha_evolve/phenotype_mapper.py && echo "FAIL" || echo "PASS"
```

### TASK 12-03: SBI Scale & Validation Rigor
**Target**: `scripts/run_phase7_sbi.py`
**Remediation**:
1. Increase `num_simulations` from $2,000$ to $100,000$ for robust density estimation.
2. Ensure the SBI target observations match the actual DESI DR1 means.
3. (Optional but recommended): Utilize GCP/Vertex AI for this script since $10^5$ simulations of the EFT mapping will be computationally heavy.
**Validation**:
```bash
# Verify the SBI simulation count is physically appropriate
grep -q "num_simulations = 100000" scripts/run_phase7_sbi.py && echo "PASS" || echo "FAIL"
```

---

## Part C: Execution Strategy

These fixes ensure that the rigorous physics implemented in Phase 11 actually propagates through the entire statistical and machine learning pipeline without corruption.
1. Execute **Task 12-01** immediately to salvage the integrity of the Bayesian nested sampling.
2. Execute **Task 12-02 & 12-03** to realign the Simulation-Based Inference models.
