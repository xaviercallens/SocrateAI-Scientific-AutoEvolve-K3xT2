# 🔬 Phase 11: Scientific Rigor & Deep Physics Audit
> **Version**: 1.0.0 | **Date**: 2026-08-03 | **Target**: Preparation for High-Tier Peer Review (e.g., PRL, JCAP)

---

## Part A: Deep Scientific Gaps Identified

While Phase 10 stabilized the numerical implementation of the Picard-Fuchs periods and removed tautological ML data, a deep physics audit reveals several "phenomenological bridges" that still rely on algebraic proxies rather than first-principles string theory derivations. If submitted in its current state, reviewers will likely reject the paper on the grounds of arbitrary parametrizations.

### 🔴 CRITICAL GAPS (Must fix for physical validity)

| ID | Component | Scientific Finding | Impact |
|----|-----------|--------------------|--------|
| **11.A1** | `scalar_potential.py` | **Missing String-Scale Normalization:** The F-term potential $V = e^K(\vert DW \vert^2 - 3\vert W \vert^2)$ is computed using dimensionless period integrals. To represent physical vacuum energy density ($\Lambda \sim 10^{-122} M_{Pl}^4$), it must be multiplied by $(M_s/M_{Pl})^4 \approx g_s^2 (\alpha')^2 / \text{Vol}(K3 \times T^2)$. Without this, the slow-roll $\epsilon$ is arbitrary. | The entire derivation of $w_0$ from EFT is scale-free and cannot be quantitatively trusted. |
| **11.A2** | `jwst_likelihood.py` | **Algebraic FDM Mass Proxy:** The mapping from the topological mass gap $\gamma$ to the physical axion/FDM mass is implemented as `m_fdm = 1e-22 * (gamma / 4.847)**2`. This is an ad-hoc algebraic fit. The true string axion mass is $m_a^2 \sim \Lambda^4 / f_a^2$, where the decay constant $f_a$ depends on the cycle volumes. | JWST likelihood constraints are effectively decoupled from the actual string geometry. |

### 🟠 HIGH-PRIORITY GAPS (Required for observational rigor)

| ID | Component | Scientific Finding | Impact |
|----|-----------|--------------------|--------|
| **11.B1** | `s8_likelihood.py` | **Simple Gaussian S8 Constraint:** The current Euclid likelihood just evaluates a 1D Gaussian against $S_8 = 0.830$. A true Stage-IV weak lensing analysis requires calculating the cosmic shear angular power spectrum $C_\ell^{\gamma\gamma}$ from the non-linear matter power spectrum $P_{NL}(k,z)$. | Reduces the Euclid forecast to a trivial prior rather than a real tomographic constraint. |
| **11.B2** | `scalar_potential.py` | **Ignored Flux Landscape:** The tadpole constraint $\frac{1}{2} \sum n_a^2 \le \frac{\chi}{24} = 1$ allows for multiple flux configurations, but the code hardcodes `flux_n = 1`. | Misses potential discrete vacua that might provide better cosmological fits. |

---

## Part B: Improvement Plan & Remediation Steps

### TASK 11-01: String-Scale Normalization of the F-Term Potential
**Target**: `src/eft/scalar_potential.py`
**Remediation**:
1. Implement the K3 volume function: $\text{Vol}(K3) = \int J \wedge J$, driven by the Kähler moduli.
2. Define the string coupling $g_s \approx 0.1$ and the Planck mass relation.
3. Multiply the final scalar potential $V(\tau)$ by $V_0 = \frac{g_s^2}{4 \pi \text{Vol}(K3 \times T^2)^3}$.
**Validation**:
```bash
# V(tau=0.5) must now evaluate to O(10^-120) in Planck units
python -c "from src.eft.scalar_potential import scalar_potential; V = scalar_potential(0.5); print(V); assert V < 1e-100"
```

### TASK 11-02: First-Principles Axion Mass (FDM) Derivation
**Target**: `src/mcmc/jwst_likelihood.py` & `src/eft/scalar_potential.py`
**Remediation**:
1. Remove the hardcoded quadratic fit in `jwst_likelihood.py`.
2. Compute the axion decay constant $f_a = M_{Pl} / \sqrt{\text{Vol}_{cycle}}$ where $\text{Vol}_{cycle}$ is tied to the K3 Picard lattice.
3. Calculate $m_a^2 = \frac{\Lambda_{QCD}^4}{f_a^2} e^{-S_{inst}}$ using the instanton action $S_{inst} = 2\pi \tau_2$.
**Validation**:
```bash
# Check that the mass computation responds exponentially to the T2 modulus tau
python -m pytest tests/ -k "test_fdm_mass_scaling" -v
```

### TASK 11-03: Integrate Boltzmann Solver (PyCCL / CAMB) for Euclid
**Target**: `src/mcmc/s8_likelihood.py`
**Remediation**:
1. Add `pyccl` (Core Cosmology Library) to the dependency stack.
2. Initialize a CCL cosmology using the candidate's $\{\Omega_m, h, w_0\}$.
3. Compute the non-linear matter power spectrum and integrate it over the official Euclid Q1 $n(z)$ source distributions to obtain $C_\ell^{\gamma\gamma}$.
4. Replace the 1D Gaussian with a full $\chi^2$ over the shear multipoles.
**Validation**:
```bash
# Likelihood must now take > 100ms due to CCL integration, and return a robust chi2
python -c "from src.mcmc.s8_likelihood import S8Likelihood; ell = S8Likelihood(); print(ell.log_likelihood({'omega_m': 0.3, 'w0': -0.95, 'h0': 67}))"
```

### TASK 11-04: Discrete Flux Landscape MCMC
**Target**: `scripts/run_p2_joint_nested_sampling.py`
**Remediation**:
1. Expand the MCMC parameter space to include discrete flux integers $n_1, n_2, n_3$.
2. Implement a rejection sampling prior that enforces $n_1^2 + n_2^2 + n_3^2 \le 2$.
3. Pass the flux vector into `scalar_potential(tau, flux_vec=...)`.
**Validation**:
```bash
# Run dynesty and verify that the posterior successfully marginalized over the discrete flux states
python scripts/run_p2_joint_nested_sampling.py --test-flux-sampling
```

---

## Part C: Execution Strategy

These fixes elevate the codebase from an "applied machine learning" pipeline to a **stringent theoretical physics framework**. 

*   **Step 1**: Execute TASK 11-01 immediately. If the potential drops to $10^{-120}$, the finite-difference derivative in `slow_roll_epsilon` will suffer catastrophic cancellation (floating point limits). We will need to implement arbitrary-precision arithmetic (`mpmath`) or analytical derivatives.
*   **Step 2**: Integrate `pyccl` (TASK 11-03). This will significantly slow down the nested sampling, requiring the use of the GCP distributed coordinator.
*   **Step 3**: Re-run the full 150-generation Deep Burn to re-optimize the $K_4$ hypergraph against the newly rigorous physics likelihoods.
