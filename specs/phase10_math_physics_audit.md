# 🔬 Phase 10: Mathematics & Physics Deep Audit + Low-Tier Model Task Plan

> **Version**: 1.0.0 | **Date**: 2026-08-01 | **Tier**: Tasks designed for Gemini Flash / Sonnet-class models

---

## Part A: Audit Findings

### 🔴 CRITICAL (Must fix before submission)

| ID | File | Finding | Impact |
|----|------|---------|--------|
| **A1** | `scalar_potential.py:66-74` | **Picard-Fuchs logarithmic periods Π₁, Π₂ are wrong.** `Π₁ = Π₀·log(x)` is only the leading term; the sub-leading power series `Σ vₙ xⁿ` (computed from the Frobenius method) is entirely missing. This makes the Kähler potential `K_K3` and all downstream slow-roll computations unreliable. | All EFT-derived w₀ values are approximate at best. |
| **A2** | `scalar_potential.py:98` | **Period norm sign is physically wrong.** `|Π₀|² - |Π₁|² + |Π₂|²` — for real x near the MUM point, Π₁ ∝ log(x) is large and negative, making this expression potentially negative. The fallback `period_norm = |Π₀|²` silently discards the K3 geometry. | Kähler potential loses all period-integral physics. |
| **A3** | `scalar_potential.py:177-180` | **w₀ is hardcoded, not computed.** `epsilon_0 = 0.013` is reverse-engineered from DESI w₀ = −0.974, then fed back to "predict" w₀. This is circular. The `slow_roll_epsilon()` function on L142 exists but is never called in production. | Central claim of EFT derivation is circular. |
| **A4** | `desi_likelihood.py:195` | **Comoving distance uses only 200 trapezoidal steps.** No convergence check. CLASS/CAMB use adaptive Runge-Kutta. At z=2.33 (highest DESI bin), 200 steps gives ~0.1% error — marginal for χ² at the 10⁻⁶ level claimed. | Numerical precision undermines BAO χ² claim. |
| **A5** | `run_p3_dwarf_galaxy_soliton.py:50-67` | **Soliton validation uses mock data generated from its own model.** `generate_mock_sparc_data()` creates synthetic data using `soliton_velocity()`, then fits the same function to it. Of course it wins. No real SPARC data is loaded. | Soliton "validation" is a tautology. |

### 🟠 HIGH (Should fix)

| ID | File | Finding | Impact |
|----|------|---------|--------|
| **B1** | `scalar_potential.py:188-195` | `Ωₘ = (ρ/h¹¹) × Ωₘ,Planck` — matter density is *linearly* proportional to Picard rank with no physical derivation. Why does ρ=10 give Ωₘ=0.158? This would be ruled out by CMB alone. | Unphysical Ωₘ for most of the Picard range. |
| **B2** | `scalar_potential.py:207-210` | `H₀ = 69.3 + 2(τ−0.5)` — Hubble parameter is a linear perturbation with a magic slope of 2.0 km/s/Mpc per unit τ. No derivation from vacuum energy. | Ad-hoc parametrization dressed as EFT. |
| **B3** | `symbolic_regression.py` | **Not actually symbolic regression.** The "learner" hard-codes the formula `w₀ = −1 + δ/(144τ²)` and back-solves for δ. Real symbolic regression (PySR) searches over expression trees. This is algebraic curve-fitting with 1 free parameter. | Misrepresents the methodology. |
| **B4** | `equivariant_gnn.py:141-158` | **GNN training data is fabricated.** "Pseudo-adjacency" matrices are constructed by injecting moduli values into a perturbed K₄ matrix. Real K₄ hypergraph rewrites would produce genuinely different topologies. | GNN learns noise, not geometry. |
| **B5** | `neural_ode_pf.py:43-50` | **Neural ODE physics term is wrong.** The PF operator for Cooper s₁₀ is 3rd-order but the code models a 2nd-order ODE. The state is `[y, dy/dz]` (dim 2) but should be `[y, dy/dz, d²y/dz²]` (dim 3). | Neural ODE solves wrong equation. |
| **B6** | `run_p2_joint_nested_sampling.py:78-81` | **moduli_to_cosmo mapping has tiny coefficients.** `w₀ += 0.01·(τ−0.5)`, `Ωₘ += 0.005·cs₁`, `H₀ += 0.20·cs₂`. These ensure the model stays near the calibration point regardless of moduli — the posterior is dominated by the prior, not the physics. | Model has almost no predictive power. |
| **B7** | `run_phase7_sbi.py:64` | **SBI simulator fixes cs₃=0.96.** One of 5 parameters is hardcoded, breaking the dimensionality of the inference. | SBI posterior is biased. |

### 🟡 MEDIUM (Should improve)

| ID | File | Finding |
|----|------|---------|
| **C1** | `scalar_potential.py:114` | Tadpole constraint `½Σnₐ² ≤ χ/24 = 1` is stated but only `flux_n=1` is ever used. Multi-flux configurations are never explored. |
| **C2** | `desi_likelihood.py:220-236` | NanoGrav likelihood is a 1D Gaussian mock on f_monopole. Real NANOGrav data is a 14-bin free spectrum. |
| **C3** | `phenotype_mapper.py:113` | Hard clipping `w₀ ∈ [−1.2, −0.8]` silently truncates the posterior and biases Bayesian evidence. |
| **C4** | `lean_oracle/rpc_server.lean:27-28` | Swampland check is `moduli_stabilization > 0.0` — any positive number passes. No minimum threshold. |

---

## Part B: Task Plan for Low-Tier Models

Each task is self-contained with explicit DoD and validation steps.

---

### TASK-01: Fix Picard-Fuchs Period Computation (Frobenius Method)
**Severity**: 🔴 A1 + A2 | **File**: `src/eft/scalar_potential.py` | **Est**: 2 hrs

**Description**: Replace the naive `Π₁ = Π₀·log(x)` with the proper Frobenius series solution at the MUM point. The logarithmic period requires computing the derivative of the holomorphic period w.r.t. the indicial exponent.

**Task**:
1. Implement `frobenius_periods(x, n_terms=30)` that computes all 3 periods via the recurrence relation of the Cooper s₁₀ PF ODE: `(1 + c₁z + c₂z²) y''' + ... = 0`
2. The sub-leading series for Π₁ is: `Π₁(x) = Π₀(x)·log(x) + Σₙ vₙ·xⁿ` where `vₙ = d/dρ[uₙ(ρ)]|_{ρ=0}` and uₙ(ρ) is the generalized term with shifted exponent
3. Replace `picard_fuchs_periods()` with the new implementation

**DoD**:
- [ ] `frobenius_periods(0.01)` returns 3 distinct finite values
- [ ] Period norm `|Π₀|² − |Π₁|² + |Π₂|²` is strictly positive for x ∈ (0, 0.05)
- [ ] Unit test: compare Π₀(x) against `cooper_s10_term` summation (must match to 10⁻¹⁰)
- [ ] No fallback branch is ever triggered

**Validation**:
```bash
python -c "from src.eft.scalar_potential import frobenius_periods; p=frobenius_periods(0.01); print(p); assert all(abs(v) < 1e10 for v in p)"
```

---

### TASK-02: Eliminate Circular w₀ Calibration
**Severity**: 🔴 A3 | **File**: `src/eft/scalar_potential.py` | **Est**: 1.5 hrs

**Description**: The function `w0_from_eft()` currently hardcodes ε₀=0.013. Replace it with the actual numerical derivative of the scalar potential V(τ) using the corrected period integrals from TASK-01.

**Task**:
1. In `w0_from_eft(tau)`, call `slow_roll_epsilon(tau)` (which already exists at L142) instead of using the hardcoded quadratic
2. Verify that `slow_roll_epsilon(0.50)` returns a value near 0.013 when using corrected periods
3. If the value differs significantly, **document** the discrepancy — do NOT re-tune

**DoD**:
- [ ] `w0_from_eft()` contains no hardcoded `epsilon_0` constant
- [ ] `w0_from_eft(0.50)` returns a value in [−1.05, −0.90]
- [ ] The function calls `slow_roll_epsilon()` or `scalar_potential()` internally
- [ ] Comment added explaining what changed and why

**Validation**:
```bash
python -c "from src.eft.scalar_potential import w0_from_eft; w=w0_from_eft(0.50); print(f'w0={w:.6f}'); assert -1.05 < w < -0.90"
```

---

### TASK-03: Increase Comoving Distance Integration Precision
**Severity**: 🔴 A4 | **File**: `src/mcmc/desi_likelihood.py` | **Est**: 30 min

**Description**: Increase trapezoidal steps from 200 to 2000 and add a convergence assertion.

**Task**:
1. Change `n_steps: int = 200` to `n_steps: int = 2000` on line 195
2. Add a convergence test: compute at n_steps and n_steps/2, assert relative difference < 10⁻⁶
3. Optionally switch to `scipy.integrate.quad` for adaptive integration

**DoD**:
- [ ] `_comoving_distance` uses ≥ 2000 steps or adaptive quadrature
- [ ] Unit test: `|D_M(z=2.33, n=2000) − D_M(z=2.33, n=4000)| / D_M < 10⁻⁶`
- [ ] BAO χ² value does not change by more than 1% from previous run

**Validation**:
```bash
python -m pytest tests/ -k "desi" -v
```

---

### TASK-04: Replace Mock Soliton Data with Real SPARC Catalog
**Severity**: 🔴 A5 | **File**: `scripts/run_p3_dwarf_galaxy_soliton.py` | **Est**: 2 hrs

**Description**: Download and load actual SPARC (Spitzer Photometry and Accurate Rotation Curves) data for a cored dwarf galaxy (e.g., DDO 154 or IC 2574).

**Task**:
1. Download SPARC table from `http://astroweb.cwru.edu/SPARC/` into `data/sparc/`
2. Parse the `.dat` file to extract (r, V_obs, V_err) columns
3. Replace `generate_mock_sparc_data()` with `load_sparc_galaxy(name="DDO154")`
4. Re-run the NFW vs Soliton fit on real data
5. If soliton loses, **document it honestly**

**DoD**:
- [ ] `data/sparc/DDO154_rotmod.dat` exists and is non-empty
- [ ] `load_sparc_galaxy()` returns arrays from the file, not synthetic data
- [ ] Script produces `paper/figures/soliton_core_validation.pdf` with real data
- [ ] χ² values in the log reflect real-data fits
- [ ] No `generate_mock_sparc_data()` call remains in the main execution path

**Validation**:
```bash
python scripts/run_p3_dwarf_galaxy_soliton.py
# Check log output for "Loaded N radial bins from SPARC" (not "Mock")
```

---

### TASK-05: Fix Neural ODE to 3rd-Order PF System
**Severity**: 🟠 B5 | **File**: `src/ml_modules/neural_ode_pf.py` | **Est**: 1.5 hrs

**Description**: The Picard-Fuchs ODE for Cooper s₁₀ is 3rd order. The neural ODE state must be `[y, y', y'']` with the ODE function outputting `[y', y'', y''']`.

**Task**:
1. Change `PicardFuchsODEFunc.__init__` input dim from 3 to 4 (adding d²y/dz²)
2. Change output dim from 1 to 1 (d³y/dz³)
3. State becomes `[y, dy, d2y]`; forward returns `[dy, d2y, d3y]`
4. Update initial conditions: `y0 = [1.0, 0.0, 0.0]`
5. Update the physics-informed base term to use the full 3rd-order operator

**DoD**:
- [ ] State dimension is 3 (not 2)
- [ ] `y0` has shape `[1, 3]`
- [ ] Loss converges below 0.1 within 50 steps
- [ ] `run_neural_ode_pf_integration()` returns without error

**Validation**:
```bash
python -c "from src.ml_modules.neural_ode_pf import run_neural_ode_pf_integration; r=run_neural_ode_pf_integration(n_steps=50); print(r); assert r['final_loss'] < 1.0"
```

---

### TASK-06: Implement Real Symbolic Regression with PySR
**Severity**: 🟠 B3 | **File**: `src/ml_modules/symbolic_regression.py` | **Est**: 2 hrs

**Description**: Replace the algebraic back-solver with actual PySR symbolic regression.

**Task**:
1. `pip install pysr` and add to requirements.txt
2. Generate a training set: sample 500 (τ, w₀) pairs from `w0_from_eft()`
3. Call `PySRRegressor(binary_operators=["+","-","*","/"], unary_operators=["exp","log","sqrt"])` to discover w₀(τ)
4. Keep the current back-solver as a fallback if PySR is not installed
5. Log the discovered equation and its complexity

**DoD**:
- [ ] `PySRRegressor.fit()` is called on real simulation data
- [ ] Discovered equation is logged with its MSE and complexity score
- [ ] Lean 4 code generation still works with the discovered formula
- [ ] Fallback path works if `pysr` is not installed

**Validation**:
```bash
python -c "from src.ml_modules.symbolic_regression import run_symbolic_regression_pipeline; r=run_symbolic_regression_pipeline({'t2_modulus_tau':0.50,'phenotype':{'w0':-0.974},'spectral_gap':4.847}); print(r['discovered_formulas'])"
```

---

### TASK-07: Derive Ωₘ(ρ) from Kaluza-Klein Spectrum
**Severity**: 🟠 B1 | **File**: `src/eft/scalar_potential.py` | **Est**: 3 hrs

**Description**: Replace `Ωₘ = (ρ/20)·0.315` with a physically motivated formula from the KK mass spectrum.

**Task**:
1. Research: In Type IIA on K3×T², the number of massless scalars is related to h¹¹. The matter density contribution comes from KK modes with masses below the Hubble scale
2. Implement `omega_m_from_kk_spectrum(picard, tau, m_kk_scale)` where `m_kk ~ 1/R_T²`
3. The function should reduce to Ωₘ ≈ 0.295 at the MAP point (ρ=19, τ=0.50)
4. Document the derivation in a docstring with equation references

**DoD**:
- [ ] `omega_m_from_kk_spectrum(19, 0.50)` returns value in [0.28, 0.32]
- [ ] `omega_m_from_kk_spectrum(1, 0.50)` returns value in [0.05, 0.15] (physical)
- [ ] Docstring contains the KK mass formula and integration limits
- [ ] Old `omega_m_from_picard()` is deprecated but not deleted

**Validation**:
```bash
python -c "from src.eft.scalar_potential import omega_m_from_kk_spectrum as f; print(f(19,0.50)); assert 0.28 < f(19,0.50) < 0.32"
```

---

### TASK-08: Add Convergence Tests to Nested Sampling
**Severity**: 🟠 B6 | **File**: `scripts/run_p2_joint_nested_sampling.py` | **Est**: 1 hr

**Description**: Add diagnostic checks for posterior volume collapse and prior-dominated inference.

**Task**:
1. After the dynesty run, compute the effective sample size (ESS) and log it
2. Compute the Kullback-Leibler divergence between prior and posterior
3. If KL < 0.5 nats, emit a WARNING that the posterior is prior-dominated
4. Add a "prior-only" run (likelihood=const) and compare ln(Z) to detect prior sensitivity

**DoD**:
- [ ] ESS is computed and logged: `ESS = (Σwᵢ)² / Σwᵢ²`
- [ ] KL divergence is computed for each parameter
- [ ] WARNING emitted if any parameter has KL < 0.5
- [ ] Results JSON contains `"effective_sample_size"` and `"kl_divergence"` fields

**Validation**:
```bash
python scripts/run_p2_joint_nested_sampling.py
# Check output for "KL divergence" and "ESS" lines
```

---

### TASK-09: Fix GNN Training Data Pipeline
**Severity**: 🟠 B4 | **File**: `src/ml_modules/equivariant_gnn.py` | **Est**: 2.5 hrs

**Description**: Generate proper hypergraph rewriting sequences instead of perturbed K₄ matrices.

**Task**:
1. Implement `k4_hadamard_rewrite(adj, steps)` that applies deterministic Wolfram-style rewriting rules to an adjacency matrix
2. Each rewrite step: find a K₃ subgraph, replace with K₄ (adding a node), or merge nodes
3. Generate training set: 500 graphs at various rewrite depths, label with their eigenspectrum
4. Replace `generate_batch()` with `generate_rewrite_batch()`

**DoD**:
- [ ] `k4_hadamard_rewrite(K4, steps=3)` produces a graph with 5-7 nodes
- [ ] Training graphs have varying sizes (not all 4×4)
- [ ] GNN uses proper padding/masking for variable-size graphs
- [ ] Final λ₁ prediction on pure K₄ is within 5% of analytical value (3.0)

**Validation**:
```bash
python -c "from src.ml_modules.equivariant_gnn import train_gnn_on_k4_rewriting; r=train_gnn_on_k4_rewriting(n_steps=50); assert abs(r['k4_predictions']['spectral_radius_lambda1'] - 3.0) < 0.3"
```

---

### TASK-10: Remove Hard Clipping from Phenotype Mapper
**Severity**: 🟡 C3 | **File**: `src/alpha_evolve/phenotype_mapper.py` | **Est**: 30 min

**Task**:
1. Remove `max(-1.2, min(-0.8, w0))` clipping on L113 (and similarly for Ωₘ, H₀)
2. Instead, add a soft penalty to the likelihood if values fall outside physical range
3. Or use `tanh` squashing: `w0_phys = -1.0 + 0.2 * tanh(w0_raw)`

**DoD**:
- [ ] No `max()`/`min()` clipping in the return dict
- [ ] Values outside [−1.2, −0.8] are still finite (no NaN/Inf)
- [ ] All existing tests pass

**Validation**:
```bash
python -m pytest tests/ -v
```

---

## Part C: Execution Priority Matrix

| Priority | Tasks | Total Est. | Dependency |
|----------|-------|-----------|------------|
| **P0** (Blocks paper) | TASK-01, TASK-02, TASK-04 | 5.5 hrs | 02 depends on 01 |
| **P1** (Strengthens claims) | TASK-03, TASK-05, TASK-08 | 3 hrs | Independent |
| **P2** (ML integrity) | TASK-06, TASK-09 | 4.5 hrs | Independent |
| **P3** (Polish) | TASK-07, TASK-10 | 3.5 hrs | Independent |

**Critical path**: TASK-01 → TASK-02 → re-run `run_p2_joint_nested_sampling.py` → verify Bayes factor still decisive.

---

## Part D: Agent Prompt Template (for Low-Tier Models)

```
You are implementing a focused code fix for the SocrateAI K3×T² cosmological pipeline.
Repository: /home/xavkal/xdev/SocrateAI-Scientific-AutoEvolve-K3*T2/

Your task: Complete [TASK-XX] from specs/phase10_math_physics_audit.md

Rules:
1. Read the ENTIRE target file before making changes
2. Run the validation command AFTER your edit
3. If validation fails, debug and retry (max 3 attempts)
4. Do NOT change files outside the task scope
5. Do NOT refactor unrelated code
6. If the physics is wrong, document it — do NOT hide it
7. Commit with: "fix(TASK-XX): [one-line description]"
```
