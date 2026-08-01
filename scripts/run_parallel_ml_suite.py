#!/usr/bin/env python3
"""
Master Parallel Execution Suite for Advanced ML Modules
======================================================
Executes:
1. Equivariant Graph Neural Networks (GNNs) for hypergraph continuum limit.
2. Symbolic Regression for Lean 4 formal code generation.
3. Neural ODEs for Picard-Fuchs moduli differential integrations.

All 3 tasks run concurrently using Python multi-threading/multiprocessing.
"""

import concurrent.futures
import json
import logging
import os
import sys
import time
from pathlib import Path

# Ensure src/ is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from ml_modules.equivariant_gnn import train_gnn_on_k4_rewriting
from ml_modules.symbolic_regression import run_symbolic_regression_pipeline
from ml_modules.neural_ode_pf import run_neural_ode_pf_integration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(threadName)s] - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ParallelMLSuite")

def worker_gnn():
    logger.info("⚡ Starting Task 1: Equivariant GNN Hypergraph Learning...")
    start = time.time()
    res = train_gnn_on_k4_rewriting(n_steps=150)
    res["runtime_sec"] = time.time() - start
    logger.info(f"✅ Task 1 Complete ({res['runtime_sec']:.2f}s): λ1={res['k4_predictions']['spectral_radius_lambda1']:.4f}, P={res['k4_predictions']['picard_number']:.2f}")
    return ("GNN", res)

def worker_symbolic():
    logger.info("⚡ Starting Task 2: Symbolic Regression & Lean 4 Theorem Extraction...")
    start = time.time()
    
    # Load a real checkpoint
    import glob
    checkpoint_files = glob.glob("data/checkpoints/*.json")
    if checkpoint_files:
        best_ckpt = max(checkpoint_files) # typically gets the latest generation
        with open(best_ckpt, 'r') as f:
            data = json.load(f)
            cand = data.get("best_candidate", {})
            sample_candidate = {
                "t2_modulus_tau": cand.get("t2_modulus_tau", 0.4999),
                "phenotype": cand.get("phenotype", {"w0": -0.974}),
                "spectral_gap": cand.get("phenotype", {}).get("pta_anisotropy", 0.05) * 100.0
            }
            logger.info(f"Loaded real checkpoint data from {best_ckpt}")
    else:
        sample_candidate = {
            "t2_modulus_tau": 0.4999,
            "phenotype": {"w0": -0.974},
            "spectral_gap": 4.847
        }
        
    res = run_symbolic_regression_pipeline(sample_candidate)
    res["runtime_sec"] = time.time() - start
    logger.info(f"✅ Task 2 Complete ({res['runtime_sec']:.2f}s): Discovered w0={res['discovered_formulas']['w0_formula']}")
    return ("SymbolicRegression", res)

def worker_neural_ode():
    logger.info("⚡ Starting Task 3: Neural ODE Picard-Fuchs Period Integrator...")
    start = time.time()
    
    # Load pf_coeffs from real checkpoint
    import glob
    import json
    checkpoint_files = glob.glob("data/checkpoints/*.json")
    pf_coeffs = (1.0, -12.0, -64.0)
    if checkpoint_files:
        best_ckpt = max(checkpoint_files)
        with open(best_ckpt, 'r') as f:
            data = json.load(f)
            cand = data.get("best_candidate", {})
            coeffs = cand.get("picard_fuchs_coefficients", [])
            if len(coeffs) >= 3:
                pf_coeffs = (float(coeffs[0]), float(coeffs[1]), float(coeffs[2]))
                logger.info(f"Loaded real PF coefficients from {best_ckpt}: {pf_coeffs}")
                
    res = run_neural_ode_pf_integration(n_steps=50, pf_coeffs=pf_coeffs)
    res["runtime_sec"] = time.time() - start
    logger.info(f"✅ Task 3 Complete ({res['runtime_sec']:.2f}s): Period Integral y={res['integrated_period_integral']:.4f} (Target={res['target_period_integral']})")
    return ("NeuralODE", res)

def main():
    total_start = time.time()
    logger.info("═══════════════════════════════════════════════════════════════════")
    logger.info("  Launching Advanced Parallel ML Suite (GNN + Symbolic + Neural ODE)")
    logger.info("═══════════════════════════════════════════════════════════════════")
    
    results = {}
    
    # Execute all 3 workers in parallel threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=3, thread_name_prefix="MLWorker") as executor:
        futures = [
            executor.submit(worker_gnn),
            executor.submit(worker_symbolic),
            executor.submit(worker_neural_ode),
        ]
        
        for future in concurrent.futures.as_completed(futures):
            task_name, task_res = future.result()
            results[task_name] = task_res
            
    total_time = time.time() - total_start
    
    # Output unified diagnostic summary
    Path("outputs/ml_suite").mkdir(parents=True, exist_ok=True)
    summary_path = "outputs/ml_suite/parallel_ml_summary.json"
    
    summary_payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_runtime_seconds": total_time,
        "tasks": results
    }
    
    with open(summary_path, "w") as f:
        json.dump(summary_payload, f, indent=2)
        
    logger.info("═══════════════════════════════════════════════════════════════════")
    logger.info(f"  PARALLEL ML SUITE COMPLETE in {total_time:.2f}s")
    logger.info(f"  Summary Report written to: {summary_path}")
    logger.info("═══════════════════════════════════════════════════════════════════")
    
    print("\n" + "="*60)
    print("  PARALLEL ML SUITE EXECUTION SUMMARY")
    print("="*60)
    print(f"Total Execution Time: {total_time:.2f} seconds")
    print(f"1. GNN Continuous Limit:      λ₁ = {results['GNN']['k4_predictions']['spectral_radius_lambda1']:.4f}, P = {results['GNN']['k4_predictions']['picard_number']:.2f}")
    print(f"2. Symbolic Regression w0:    {results['SymbolicRegression']['discovered_formulas']['w0_formula']}")
    print(f"3. Neural ODE PF Integration: Period = {results['NeuralODE']['integrated_period_integral']:.4f}")
    print("="*60)

if __name__ == "__main__":
    main()
