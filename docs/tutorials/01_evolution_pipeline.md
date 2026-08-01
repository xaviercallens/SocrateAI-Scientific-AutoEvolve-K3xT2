# Tutorial: The K3×T² Evolutionary Pipeline

This tutorial demonstrates how to run the multi-tiered K3×T² geometric evolution pipeline.

## 1. Environment Setup

First, ensure your virtual environment is active and all required dependencies are installed:

```bash
pip install -r requirements.txt
```

Verify that the Data Lake has been correctly staged:
```bash
python verify_datalake.py
```

## 2. Launching Phase 1: Continuous Evolution

Phase 1 explores the continuous complex structure moduli space. It relies on the Lean 4 Swampland Gatekeeper (`rpc_server`) to prune mathematically impossible geometries.

```bash
# Build the Lean 4 oracle daemon
cd lean_oracle && lake build && cd ..

# Execute Phase 1
python scripts/run_phase1_k3_t2_evolution.py
```

You should see logs detailing the generation-by-generation progression. The globally optimal candidate is evaluated based on its mock $\chi^2$ loss.

## 3. Launching Phase 2: Physical MCMC

Once Phase 1 stabilizes the topology, Phase 2 evaluates the geometries against the real DESI BAO, Euclid, and NANOGrav likelihoods using the `DESILikelihoodEngine`.

```bash
python scripts/run_phase2_physical_k3_t2.py
```

## 4. Deep Burn

To continue evolution beyond 150 generations, use the Extended Deep Burn script. It will automatically load the latest GCS-backed JSON checkpoint via `EvolutionCheckpoint`.

```bash
python scripts/run_extended_burn.py
```
Monitor the live status at `outputs/local_deep_burn/burn_monitor.json`.
