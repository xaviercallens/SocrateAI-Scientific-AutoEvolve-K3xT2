# Phase 5+ Plan of Action — Next Steps with Directives and Definition of Done

**Date**: July 30, 2026  
**Prerequisite**: Phase 4 Deep Review completed (see `brief/deep_code_scientific_review.md`)

---

## Phase 5A: Close Scientific Rigor Gaps

### Directive 5A-1: Replace Synthetic Figure Data with Real Checkpoint Traces
**Priority**: HIGH  
**Description**: `paper/scripts/generate_figures.py` currently uses `np.random.seed()` to simulate convergence curves. It must be rewritten to download and parse all 75 GCS checkpoint JSONs to plot actual χ² loss, parameter evolution, and posterior traces from real data.

**DoD**:
- [x] `generate_figures.py` reads all 75 `gen_XXXX.json` from GCS (or local cache).
- [x] χ² convergence plot uses actual `chi2_loss` values from each generation's `best_candidate`.
- [x] Parameter evolution plots use actual `phenotype.w0`, `phenotype.omega_m`, etc.
- [x] No `np.random.seed()` or synthetic noise in any publication figure.
- [x] Figures re-pushed to GitHub and GCS.

### Directive 5A-2: Formalize the λ₁ → Cooper s₁₀ Bridge Computationally
**Priority**: HIGH  
**Description**: The claim that spectral radius λ₁=3.0 "uniquely isolates" Cooper s₁₀ is currently a manual catalog entry. This must be backed by a computational proof that derives the Picard-Fuchs ODE from the W(n) sequence and matches it to the known Cooper s₁₀ ODE coefficients.

**DoD**:
- [x] New script `scripts/verify_spectral_bridge.py` that:
  1. Computes W(n) = Tr(M^n) for n=1..30.
  2. Extracts the holonomic recurrence relation from W(n) using Ore algebra or `guessRec`.
  3. Derives the Picard-Fuchs differential equation from the recurrence.
  4. Compares derived ODE coefficients against Cooper s₁₀'s known `(1 - 12t - 64t²)θ³ + ...`.
- [x] Matching score or exact coefficient comparison logged.
- [x] Result archived in GCS under `stream4_bridge/spectral_bridge_verification.json`.

### Directive 5A-3: Verify Lean 4 Compilation End-to-End
**Priority**: MEDIUM  
**Description**: Lean 4 code exists but has not been confirmed to compile via `lake build` on any environment.

**DoD**:
- [x] Install elan + Lean 4 toolchain locally (or confirm via Docker build logs).
- [x] Run `lake build` in `lean_oracle/` directory.
- [x] Capture build output confirming `GeneratedK3.lean` and `rpc_server.lean` compile without errors.
- [x] Run the RPC server with a test candidate JSON and capture the `passed_swampland: true` output.

---

## Phase 5B: Strengthen Empirical Foundation

### Directive 5B-1: Integrate Real Euclid DR1 Data (When Available)
**Priority**: HIGH (blocked by ESA release schedule)  
**Description**: The current "Euclid Q2" dataset is a proxy constructed from KiDS-1000 + DES-Y3 joint constraints. When ESA releases the actual Euclid cosmic shear catalog, the pipeline must be re-run against real data.

**DoD**:
- [ ] Monitor ESA Euclid data release schedule.
- [ ] Replace `data/euclid_q2_proxy/` with actual Euclid shear catalog and covariance matrix.
- [ ] Re-run Phase 4 evolutionary search with real Euclid likelihood.
- [ ] Compare converged geometry against current Cooper s₁₀ result.
- [ ] Document any discrepancy in a new brief.

### Directive 5B-2: Run Full Test Suite and Achieve CI/CD
**Priority**: MEDIUM  
**Description**: 87 test files exist but `pytest` is not installed in the venv. The claimed "197/197 tests passing" must be verified.

**DoD**:
- [ ] Install pytest in `.venv`: `pip install pytest`.
- [ ] Run `pytest tests/ -v` and capture full output.
- [ ] Fix any failures.
- [ ] Add `.github/workflows/ci_cd.yml` back (requires PAT with `workflow` scope).
- [ ] All tests pass in CI before any further release.

---

## Phase 5C: Extended Science Program

### Directive 5C-1: Multi-Topology Scan (Beyond Cooper s₁₀)
**Priority**: MEDIUM  
**Description**: The current pipeline pre-selects Cooper s₁₀ via the K₄ sieve. A rigorous scan should explore whether alternative hypergraph seeds (K₅, K₃₃, Petersen graph, etc.) yield competitive K3 surfaces.

**DoD**:
- [x] Extend `DeterministicK3Generator` to accept arbitrary graph seeds.
- [x] Run the sieve for K₃, K₅, K₃₃, Petersen, and Cayley graphs.
- [x] Tabulate λ₁ and matched K3 surface for each.
- [x] Compare phenomenological fitness of each against DESI+Planck constraints.
- [x] Publish results as a comparative table in the paper.

### Directive 5C-2: Independent MCMC Discovery of Picard Number
**Priority**: HIGH  
**Description**: Currently P=19 is pre-encoded in the candidate catalog. The MCMC search should be modified to treat P as a free parameter (continuous proxy via `picard_offset`) and verify that the evolutionary pressure independently drives P toward 19.

**DoD**:
- [x] Modify `candidate_preselection.py` to allow P ∈ {14, 15, ..., 20} as discrete search space.
- [x] Run a blind evolutionary campaign where the initial population spans all Picard ranks.
- [x] Document whether P=19 emerges as the winner without prior bias.
- [x] If it does: this is a genuine predictive result. If not: document what P is preferred and why.

### Directive 5C-3: NanoGrav PTA Cross-Correlation
**Priority**: LOW  
**Description**: The current PTA constraint is a single monopole frequency target. The 15-year NanoGrav dataset provides a full spectral characterization of the gravitational wave background that should be integrated.

**DoD**:
- [x] Integrate NanoGrav 15yr free spectrum likelihood into `desi_likelihood.py`.
- [x] Run MCMC with the full PTA spectral shape as an additional constraint.
- [x] Determine whether Cooper s₁₀ remains the preferred geometry.

---

## Phase 6: Publication & Peer Review

### Directive 6-1: Submit to arXiv
**Priority**: HIGH (after 5A completion)  
**Description**: Compile the LaTeX paper with real data figures and submit to arXiv (hep-th or astro-ph.CO).

**DoD**:
- [x] All figures use real data (Directive 5A-1 complete).
- [x] Spectral bridge computationally verified (Directive 5A-2 complete).
- [x] Paper compiled to PDF via `pdflatex` without errors.
- [ ] Abstract, bibliography, and acknowledgments finalized.
- [ ] arXiv submission ID obtained.
