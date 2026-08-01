# Contributing to SocrateAI-Scientific-AutoEvolve-K3xT2

Thank you for your interest in contributing to the **AlphaEvolve K3×T²** cosmological discovery framework! This repository bridges algebraic geometry (K3 surfaces), machine learning (MCMC & GNNs), and formal mathematics (Lean 4) to resolve tensions in modern cosmology (e.g., $S_8$, Hubble, Cusp-Core).

## 🚀 Getting Started

### 1. Environment Setup
We use Python 3.11+. We highly recommend using a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Required Toolchains
- **Lean 4**: Ensure you have `elan` and `lean` installed to compile the `lean_oracle`.
- **GCP Auth**: If you plan to run the TPU dispatchers or access the Data Lake, authenticate via `gcloud auth application-default login`.
- **Redis (Optional but Recommended)**: For testing the distributed orchestrator locally, run `redis-server` on `localhost:6379`.

### 3. Repository Structure
- `core/`: Agent orchestration and cost tracking logic.
- `src/alpha_evolve/`: The core evolutionary algorithms, genetic operators, and phenotype mappers.
- `src/integration/`: Connectors to Lean 4 RPC and cross-repo validation.
- `src/mcmc/`: Likelihood modules (DESI BAO, NANOGrav, Euclid).
- `scripts/`: Entry points for various evolutionary phases (e.g., `run_phase1_k3_t2_evolution.py`).
- `lean_oracle/`: The Lean 4 formal verification daemon.

## 🧪 Scientific Validation & Testing
Any changes that modify the `phenotype_mapper.py` or likelihood engines **must** pass the core cosmological consistency checks.
- Run `python verify_datalake.py` to ensure local data tensors are intact.
- Verify Lean 4 proofs by building the oracle: `cd lean_oracle && lake build`.

## 📝 Pull Request Process
1. **Branch Naming**: Use `feat/`, `fix/`, or `science/` prefixes.
2. **Data Integrity**: Ensure `.github/workflows/data_validation.yml` passes on your branch.
3. **Peer Review**: Provide mathematical context for any changes made to `src/mcmc/` or `src/eft/` modules. We enforce rigorous derivations (cf. Section 3 of our paper).

## 📊 Code Style
- Use `black` for formatting and `flake8` for linting.
- Add Google-style docstrings to all new Python functions.
- Keep Lean 4 formalizations heavily commented for readers unfamiliar with dependent type theory.
