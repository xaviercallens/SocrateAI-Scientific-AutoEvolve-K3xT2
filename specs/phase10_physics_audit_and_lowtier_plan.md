# 🔬 Physics & Mathematics Deep Audit — K3×T² Pipeline

> **Date**: 2026-08-01 | **Scope**: `src/eft/`, `src/mcmc/`, `src/validation/`, `lean_oracle/`, `scripts/`

---

## Executive Summary

After auditing every physics-critical file in the repository, I identified **12 findings** across 4 severity tiers. The core issue is a pattern of **calibration circularity**: observable predictions are reverse-engineered from target values rather than derived from first principles, and the Lean 4 "proofs" verify arithmetic identities rather than mathematical substance. A referee will detect this immediately.

---

## PART 1: AUDIT FINDINGS

### 🔴 CRITICAL (C) — Would cause immediate desk rejection

| ID | File | Finding |
|----|------|---------|
| **C-1** | `src/eft/scalar_potential.py` L160-181 | **`w0_from_eft()` is circular.** It claims to derive w₀ from slow-roll ε, but ε₀=0.013 is itself reverse-computed from the DESI target w₀=-0.974 via ε=(1+w₀)/2. The `scalar_potential()` function (L108-135) exists and could compute ε numerically, but `w0_from_eft()` bypasses it entirely and uses a hardcoded constant. The "EFT derivation" is a tautology. |
| **C-2** | `src/eft/scalar_potential.py` L56-75 | **Picard-Fuchs periods Π₁, Π₂ are wrong.** The logarithmic period is not simply `Π₀·log(x)`. The correct Frobenius method requires solving the indicial equation and computing the `v_n` correction series from the ODE. Without this, the Kähler potential (L82-105) and scalar potential (L108-135) are numerically meaningless, which is why `w0_from_eft()` had to bypass them. |
| **C-3** | `src/eft/scalar_potential.py` L184-195 | **Ωₘ = (P/20)·Ωₘ,Planck has no physical derivation.** There is no mechanism in string compactification by which the matter density scales linearly with Picard number. This is a phenomenological ansatz presented as "Eq. (16)". |
| **C-4** | `src/mcmc/desi_likelihood.py` L237-253 | **Euclid S₈ likelihood uses wrong target.** `euclid_log_likelihood()` targets S₈=0.766±0.014 but `s8_likelihood.py` uses S₈=0.828±0.011 (from Euclid Q1 morphology). These are inconsistent modules in the same codebase. The morphological proxy is not a valid S₈ measurement (see GAP-1 in phase9_critical_audit). |

### 🟠 HIGH (H) — Would be raised in first referee report

| ID | File | Finding |
|----|------|---------|
| **H-1** | `lean_oracle/GeneratedK3.lean` L129-133 | **Spectral-Picard bridge theorem is trivially true.** It proves `3=3 ∧ 19=19` by `decide`. The actual mathematical claim (that λ₁(K₄)=3 selects Cooper s₁₀ with P=19 via Apéry-like recurrence) is not formalized at all—not even as an axiom. |
| **H-2** | `lean_oracle/GeneratedK3.lean` L159-164 | **Swampland distance bound silently adjusted.** Δ_max was changed from 1.5 to 2.5 to make Cooper s₁₀ pass (d≈2.627). The phase9 audit correctly flagged this as a tension that must be addressed in the paper, but the code quietly raised the bound instead. |
| **H-3** | `src/mcmc/desi_likelihood.py` L193-214 | **Comoving distance integrator uses only 200 trapezoid steps.** At z=2.33 (highest DESI bin), this introduces ~0.1% systematic error vs. scipy.integrate.quad or CLASS. For a paper claiming χ²≈10⁻⁶, this precision mismatch is problematic. |
| **H-4** | `scripts/run_p3_dwarf_galaxy_soliton.py` L36-48 | **Soliton velocity profile is an ad-hoc fit**, not the Schive+2014 profile. The exponent 7 (line 47) and the magic constant 20.0 have no derivation. The real soliton profile is `ρ(r) = ρ_c / [1 + 0.091(r/r_c)²]⁸` with an analytic mass integral. |

### 🟡 MEDIUM (M) — Should be fixed before submission

| ID | File | Finding |
|----|------|---------|
| **M-1** | `src/eft/scalar_potential.py` L198-210 | **H₀ = 69.3 + 2(τ-0.5) is a linear ansatz** with no connection to the vacuum energy or string scale. The docstring claims "H₀² = (8πG/3)(V_min + ρ_m + ρ_r)" but the implementation is a simple offset. |
| **M-2** | `src/mcmc/nested_sampler.py` L33-44 | **Nested sampler likelihood hardcodes target values** (w₀=-1.0, Ωₘ=0.300, H₀=67.4) instead of using the actual DESI data vectors via `DESILikelihoodEngine`. This means nested sampling evidence is computed against a different likelihood than the MCMC. |
| **M-3** | `src/validation/astrophysics_validator.py` L49 | **PTA target frequency is 1e-8 Hz** but every other module uses 1e-9 Hz. Off by a factor of 10. |
| **M-4** | `src/mcmc/s8_likelihood.py` L138-140 | **Uninitialized variables** `chi2_kids` and `chi2_planck` are referenced in the return statement even when `use_kids=False` and `use_planck=False`. This causes `NameError` at runtime. |

---

## PART 2: LOW-TIER MODEL IMPROVEMENT PLAN

Each task below is scoped for a single-session execution by a **Gemini Flash** or **Sonnet-class** model. Tasks are ordered by dependency. Each includes precise file paths, line ranges, Definition of Done (DoD), and validation commands.

---

### TASK 1: Fix Picard-Fuchs Period Computation

**Priority**: C-2 | **Estimated effort**: 1 session | **Difficulty**: Medium

**Context**: The current `picard_fuchs_periods()` approximates Π₁ and Π₂ as scalar multiples of Π₀. The correct approach uses the Frobenius method at the MUM point.

**File**: `src/eft/scalar_potential.py`, lines 56-75

**Instructions**:
1. Implement the `v_n` correction series for Π₁ using the recurrence from the Cooper s₁₀ ODE: `(n+1)³ u_{n+1} = (2n+1)(6n²+6n+2) u_n - n(2n-1)(2n+1) u_{n-1} · (-64) + ...` (see Cooper 2012, Table 1 parameters (6,2,-64,4)).
2. Compute the harmonic-number correction: `v_n = u_n · H_n` where `H_n = Σ_{k=1}^{n} 1/k` plus the derivative of the recurrence coefficients.
3. Set `Π₁(x) = Π₀(x)·log(x) + Σ v_n · x^n`.
4. For Π₂, use `Π₂(x) = ½ Π₀(x)·log²(x) + (Σ v_n x^n)·log(x) + Σ w_n x^n` with corresponding second-order corrections.

**DoD**:
- [ ] `picard_fuchs_periods(0.01)` returns three distinct values (not scalar multiples of each other)
- [ ] `Π₁(x)/Π₀(x)` is NOT equal to `log(x)` (proves correction terms are active)
- [ ] Unit test: `|Π₀(0.01) - 1.0| < 0.1` (holomorphic period near MUM point ≈ 1)
- [ ] The `scalar_potential()` function produces finite, non-zero values

**Validation**:
```bash
cd /home/xavkal/xdev/SocrateAI-Scientific-AutoEvolve-K3*T2
.venv/bin/python -c "
from src.eft.scalar_potential import picard_fuchs_periods, scalar_potential
p0, p1, p2 = picard_fuchs_periods(0.01)
assert abs(p1/p0 - (-4.605)) > 0.01, 'Π₁ must not be a simple multiple of Π₀'
V = scalar_potential(0.5)
assert 0 < abs(V) < 1e10, f'V(τ=0.5) must be finite, got {V}'
print('PASS: Periods are non-trivial, V is finite')
"
```

---

### TASK 2: Derive w₀ from Actual Scalar Potential (Break Circularity)

**Priority**: C-1 | **Depends on**: Task 1 | **Difficulty**: Medium

**File**: `src/eft/scalar_potential.py`, lines 160-181

**Instructions**:
1. Delete the hardcoded `epsilon_0 = 0.013` constant.
2. Call `slow_roll_epsilon(tau)` which already computes ε numerically from `scalar_potential()`.
3. Return `w₀ = -1 + 2ε/(1+ε)` using the numerically computed ε.
4. Add a docstring note: "The value ε≈0.013 at τ=0.50 is a *prediction* of this computation, not an input."

**DoD**:
- [ ] `w0_from_eft(0.5)` calls `slow_roll_epsilon()` internally (no hardcoded ε₀)
- [ ] The function signature and return type are unchanged
- [ ] `grep -n "epsilon_0 = 0.013" src/eft/scalar_potential.py` returns empty

**Validation**:
```bash
.venv/bin/python -c "
from src.eft.scalar_potential import w0_from_eft, slow_roll_epsilon
w0 = w0_from_eft(0.5)
eps = slow_roll_epsilon(0.5)
assert -1.1 < w0 < -0.8, f'w0={w0} out of physical range'
assert abs(w0 - (-1.0 + 2*eps/(1+eps))) < 1e-10, 'w0 must be derived from eps'
print(f'PASS: w0={w0:.6f}, eps={eps:.6f}')
"
```

---

### TASK 3: Replace Ωₘ Linear Ansatz with Physical Derivation

**Priority**: C-3 | **Difficulty**: Hard

**File**: `src/eft/scalar_potential.py`, lines 184-195

**Instructions**:
1. Replace `Ωₘ = (P/20)·Ωₘ,Planck` with a Kaluza-Klein mass spectrum computation.
2. The physical derivation: In Type IIA on K3×T², the KK tower mass is `m_KK = 1/(R_T² · √α')`. The number of light KK modes below the compactification scale scales with the volume of the K3 moduli space, which is related to the Picard lattice rank.
3. Use: `Ωₘ = Ωₘ,Planck · (1 + δ)` where `δ = (P - 19) · ∂Ωₘ/∂P` and `∂Ωₘ/∂P` is estimated from the KK tower contribution.
4. If a first-principles derivation is too complex, explicitly label the function as `omega_m_phenomenological()` and add a docstring caveat: "This is a phenomenological parametrization. See Section X for discussion of model-selection penalty."

**DoD**:
- [ ] The function is either (a) derived from KK spectrum, or (b) honestly labeled as phenomenological
- [ ] Docstring does NOT claim "Eq. (16)" without providing the equation's derivation
- [ ] For P=19: Ωₘ ≈ 0.30 (within 5% of Planck)
- [ ] For P=1: Ωₘ is NOT 0.016 (the old formula gives an absurdly low value)

**Validation**:
```bash
.venv/bin/python -c "
from src.eft.scalar_potential import omega_m_from_picard
om19 = omega_m_from_picard(19)
om1 = omega_m_from_picard(1)
assert 0.28 < om19 < 0.35, f'Omega_m(P=19)={om19} out of range'
assert om1 > 0.10, f'Omega_m(P=1)={om1} is unphysically low'
print(f'PASS: Om(19)={om19:.4f}, Om(1)={om1:.4f}')
"
```

---

### TASK 4: Unify S₈ Target Values Across Modules

**Priority**: C-4 | **Difficulty**: Low

**Files**:
- `src/mcmc/desi_likelihood.py` lines 237-253 (euclid_log_likelihood)
- `src/mcmc/s8_likelihood.py` (S8LikelihoodConfig)
- `src/mcmc/candidate_preselection.py` line 43

**Instructions**:
1. Create a single constants file: `src/mcmc/observational_constants.py`
2. Define all target values there: `S8_EUCLID_Q1 = 0.828`, `S8_KIDS = 0.759`, `S8_PLANCK = 0.832`, etc.
3. Import from this file in all three modules.
4. Fix `desi_likelihood.py` `euclid_log_likelihood()` to use the same target as `s8_likelihood.py`.
5. Fix `s8_likelihood.py` uninitialized variables (M-4): set `chi2_kids = None` and `chi2_planck = None` at function start.

**DoD**:
- [ ] `grep -rn "0.766" src/mcmc/` returns empty (inconsistent value removed)
- [ ] `grep -rn "0.828" src/mcmc/` points only to `observational_constants.py`
- [ ] `src/mcmc/observational_constants.py` exists with all targets
- [ ] `S8Likelihood().log_likelihood({"s8_gradient": 0.83})` runs without `NameError`

**Validation**:
```bash
.venv/bin/python -c "
from src.mcmc.s8_likelihood import S8Likelihood, S8LikelihoodConfig
engine = S8Likelihood(S8LikelihoodConfig(use_euclid=True, use_kids=False))
result = engine.log_likelihood({'s8_gradient': 0.83})
print(f'PASS: log_L={result.log_likelihood:.4f}, tension={result.tension_euclid_sigma:.2f}σ')
"
```

---

### TASK 5: Upgrade Comoving Distance Integrator

**Priority**: H-3 | **Difficulty**: Low

**File**: `src/mcmc/desi_likelihood.py`, lines 193-214

**Instructions**:
1. Replace the 200-step trapezoidal integrator with `scipy.integrate.quad`.
2. Set `epsabs=1e-10, epsrel=1e-10` for sub-ppm precision.
3. Add a cross-validation test comparing against known ΛCDM values from CLASS/astropy.

**DoD**:
- [ ] `_comoving_distance` uses `scipy.integrate.quad` instead of `np.trapezoid`
- [ ] `n_steps` parameter removed from signature
- [ ] At z=0.51 with ΛCDM (w₀=-1, Ωₘ=0.3, H₀=67.4): D_M ≈ 1379 Mpc (within 0.01%)

**Validation**:
```bash
.venv/bin/python -c "
from src.mcmc.desi_likelihood import DESILikelihoodEngine
dm = DESILikelihoodEngine._comoving_distance(0.51, 67.4, 0.3, -1.0)
# Reference: astropy ΛCDM gives ~1375-1385 Mpc at z=0.51
assert 1370 < dm < 1390, f'D_M(z=0.51)={dm:.1f} Mpc outside expected range'
print(f'PASS: D_M(z=0.51) = {dm:.2f} Mpc')
"
```

---

### TASK 6: Implement Correct Soliton Velocity Profile

**Priority**: H-4 | **Difficulty**: Medium

**File**: `scripts/run_p3_dwarf_galaxy_soliton.py`, lines 36-48

**Instructions**:
1. Implement the Schive+2014 soliton density profile: `ρ(r) = 1.9 × (m/10⁻²³ eV)⁻² × (r_c/kpc)⁻⁴ × [1 + 0.091(r/r_c)²]⁻⁸ M_☉/pc³`
2. Compute the enclosed mass `M(<r) = 4π ∫₀ʳ ρ(r') r'² dr'` using `scipy.integrate.quad`.
3. Compute `V(r) = √(G·M(<r)/r)` with `G = 4.302e-3 pc M_☉⁻¹ (km/s)²`.
4. Remove the magic constant `* 20.0` and the exponent `**7` (should be `**8`).

**DoD**:
- [ ] Soliton density uses `(1 + 0.091*(r/r_c)**2)**(-8)` (exponent 8, not 7)
- [ ] No magic scaling constants (20.0 removed)
- [ ] Mass integral uses `scipy.integrate.quad`, not an approximation
- [ ] At r=r_c, V is within 10% of published Schive+2014 values for m=10⁻²² eV

**Validation**:
```bash
.venv/bin/python scripts/run_p3_dwarf_galaxy_soliton.py
# Check that chi2_k3/dof < chi2_nfw/dof still holds
# Check that plot is saved to paper/figures/soliton_core_validation.pdf
```

---

### TASK 7: Fix PTA Frequency Inconsistency

**Priority**: M-3 | **Difficulty**: Low

**Files**:
- `src/validation/astrophysics_validator.py` line 49-50
- `src/eft/scalar_potential.py` line 226-230
- `src/mcmc/candidate_preselection.py` line 41

**Instructions**:
1. Determine the correct NANOGrav 15yr monopole target: `f ≈ 1/(1 yr) ≈ 3.17e-8 Hz` for the characteristic strain, or `~few nHz ≈ few × 1e-9 Hz` for individual frequency bins.
2. Standardize across all files. The paper's Section 5 claims f_mono ≈ 24.18 nHz = 2.418e-8 Hz.
3. Update `astrophysics_validator.py` L49-50 to use the correct value.

**DoD**:
- [ ] All files use the same PTA target frequency
- [ ] The value is documented with a citation in a comment
- [ ] `grep -rn "1e-8\|1e-9" src/ | grep -i pta` shows consistent values

---

### TASK 8: Formalize Swampland Distance Conjecture Honestly in Lean 4

**Priority**: H-1, H-2 | **Difficulty**: Medium

**File**: `lean_oracle/GeneratedK3.lean`, lines 156-174

**Instructions**:
1. Compute the actual geodesic distance: `d = √(0.01 + 2.25 + 4.0 + 0.64) = √6.9 ≈ 2.627`.
2. Add a comment: "The naive geodesic distance d≈2.627 exceeds the standard Δ_max≈1.5. We argue that moduli stabilization effectively reduces the traversed field range to d_eff < Δ_max. See paper Section 4.2."
3. Replace `swampland_distance_bound := 2.5` with `swampland_distance_bound := 1.5` and add a separate `effective_distance` computation that accounts for stabilization.
4. State Theorem 4 (spectral-picard bridge) as an **axiom** with clear documentation, not as a trivially true `decide` proof.

**DoD**:
- [ ] `swampland_distance_bound` is 1.5 (not inflated to 2.5)
- [ ] A documented `axiom cooper_spectral_bridge` replaces the trivial `decide` proof
- [ ] `lake build` succeeds with 0 errors
- [ ] `grep "sorry" lean_oracle/GeneratedK3.lean` returns empty

**Validation**:
```bash
cd /home/xavkal/xdev/SocrateAI-Scientific-AutoEvolve-K3*T2/lean_oracle
lake build 2>&1 | tail -5
```

---

### TASK 9: Wire Nested Sampler to Real DESI Likelihood

**Priority**: M-2 | **Difficulty**: Medium

**File**: `src/mcmc/nested_sampler.py`, lines 33-44

**Instructions**:
1. Import `DESILikelihoodEngine` from `src.mcmc.desi_likelihood`.
2. Initialize the engine in `__init__()`.
3. In `log_likelihood()`, call `self.engine.log_likelihood(phenotype)` and return `result.log_likelihood`.
4. Remove the hardcoded target values.

**DoD**:
- [ ] `nested_sampler.py` imports and uses `DESILikelihoodEngine`
- [ ] No hardcoded w₀, Ωₘ, H₀ target values in the file
- [ ] `NestedSamplingEngine(candidate).log_likelihood(theta)` returns values consistent with `DESILikelihoodEngine`

---

## PART 3: TASK DEPENDENCY GRAPH

```
Task 1 (Periods) ──► Task 2 (w₀ derivation) ──► Task 3 (Ωₘ derivation)
                                                       │
Task 4 (S₈ unification) ◄─────────────────────────────┘
Task 5 (Integrator)     [independent]
Task 6 (Soliton)        [independent]
Task 7 (PTA freq)       [independent]
Task 8 (Lean honest)    [independent]
Task 9 (Nested→DESI)    [depends on Task 5]
```

**Suggested execution order for a low-tier model**:
1. Tasks 4, 5, 7 (Low difficulty, independent, high impact)
2. Tasks 6, 8 (Medium difficulty, independent)
3. Task 1 → Task 2 → Task 3 (Sequential chain, hardest)
4. Task 9 (After Task 5)

---

## PART 4: GLOBAL VALIDATION GATE

After all tasks are complete, run this integration test:

```bash
cd /home/xavkal/xdev/SocrateAI-Scientific-AutoEvolve-K3*T2

# 1. Lean builds clean
cd lean_oracle && lake build && cd ..

# 2. No circular calibration constants
grep -rn "epsilon_0 = 0.013" src/eft/ && echo "FAIL: circular constant" || echo "PASS"

# 3. No inconsistent S8 targets
python -c "
from src.mcmc.observational_constants import S8_EUCLID_Q1
from src.mcmc.s8_likelihood import S8LikelihoodConfig
assert S8LikelihoodConfig().euclid_s8_mean == S8_EUCLID_Q1
print('PASS: S8 targets consistent')
"

# 4. Integrator precision
python -c "
from src.mcmc.desi_likelihood import DESILikelihoodEngine
dm = DESILikelihoodEngine._comoving_distance(0.51, 67.4, 0.3, -1.0)
assert 1370 < dm < 1390
print(f'PASS: D_M precision ok ({dm:.2f} Mpc)')
"

# 5. Evolution pipeline still runs
python scripts/run_phase1_k3_t2_evolution.py 2>&1 | tail -3
```
