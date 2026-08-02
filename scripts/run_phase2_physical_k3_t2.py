import os
import sys
import json
import logging
import time
import random
import math

# Ensure src/ and pipeline/ are in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'pipeline', 'antigravity_compute')))

from utils.mlops_logger import EvolutionCheckpoint
from integration.lean_client import LeanOracleClient
from alpha_evolve.phenotype_mapper import map_k3_to_cosmology
from mcmc.jwst_likelihood import compute_jwst_fdm_likelihood

# Import the actual TPU Dispatcher
try:
    from cobaya_tpu_dispatcher import dispatch_to_tpu
except ImportError:
    logging.warning("Could not import dispatch_to_tpu. Ensure cobaya_tpu_dispatcher.py is available.")
    dispatch_to_tpu = None

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Continuous Genetic Operator ---
def mutate_continuous_k3(candidate: dict, gen: int, cand_idx: int) -> dict:
    child = candidate.copy()
    base_id = candidate.get('candidate_id', 'cand').split('_g')[0]
    child["candidate_id"] = f"{base_id}_g{gen}_{cand_idx}"
    
    child["t2_modulus_tau"] = child.get("t2_modulus_tau", 0.5) + random.uniform(-0.02, 0.02)
    cs = child.get("complex_structure", [1.0, 1.0, 1.0])
    child["complex_structure"] = [val + random.uniform(-0.05, 0.05) for val in cs]
    if random.random() > 0.85:
        child["picard_number"] = child.get("picard_number", 19) + random.choice([-1, 1])
    return child

# --- Tier 3: Physical Evaluator ---
def evaluate_k3_physical(candidates: list) -> list:
    """
    Tier 3: The Empirical Ground-Truth Evaluator.
    Maps K3 topologies to cosmological parameters and runs exact MCMC likelihoods via TPU.
    """
    for cand in candidates:
        cand["phenotype"] = map_k3_to_cosmology(cand)
        
    logger.info(f"Dispatching {len(candidates)} Lean-verified geometries to Antigravity TPU...")
    
    if dispatch_to_tpu:
        try:
            evaluated_candidates = dispatch_to_tpu(candidates) 
        except Exception as e:
            logger.error(f"TPU Dispatch failed: {e}")
            for c in candidates: c["chi2_loss"] = 9999.9
            return candidates
    else:
        # Mock fallback if TPU link is broken
        logger.warning("Running with Simulated TPU Mock due to missing dispatch_to_tpu binding.")
        evaluated_candidates = candidates
        for c in evaluated_candidates:
            phenotype = c["phenotype"]
            w0_err = abs(phenotype["w0"] - (-1.0))
            om_err = abs(phenotype["omega_m"] - 0.3)
            c["likelihood"] = {"chi2": (w0_err * 10) + (om_err * 20) + random.uniform(0.001, 0.01)}

    for cand in evaluated_candidates:
        likelihood = cand.get("likelihood", {})
        base_chi2 = likelihood.get("chi2", cand.get("chi2_loss", 9999.9))
        
        # Add JWST High-z FDM constraints (Phase 5)
        pheno = cand.get("phenotype", {})
        jwst_ll = compute_jwst_fdm_likelihood(
            omega_m=pheno.get("omega_m", 0.3),
            gamma_gap=pheno.get("pta_spectral_index", 4.333)
        )
        
        # log-likelihood to chi2 mapping: chi2 = -2 * log(L)
        jwst_chi2 = -2.0 * jwst_ll
        
        cand["chi2_loss"] = base_chi2 + jwst_chi2
        
    return evaluated_candidates

def execute_phase2(generations: int = 75, pop_size: int = 40):
    logger.info(f"Initializing Phase 2: Dual-Scale K3xT2 Physical Compute Evolution (Generations={generations}, PopSize={pop_size})")
    
    seed_path = "./configs/cooper_seeds.json"
    if not os.path.exists(seed_path):
        os.makedirs(os.path.dirname(seed_path), exist_ok=True)
        seeds = {
          "generation_0_seeds": [
            {"candidate_id": "cooper_s11", "picard_number": 19, "moduli_stabilization": 0.85, "complex_structure": [0.5, 0.5, 1.0], "t2_modulus_tau": 0.48},
            {"candidate_id": "cooper_s10", "picard_number": 19, "moduli_stabilization": 0.60, "complex_structure": [1.0, 0.0, 0.0], "t2_modulus_tau": 0.50},
            {"candidate_id": "cooper_s7", "picard_number": 19, "moduli_stabilization": 0.45, "complex_structure": [1.0, 1.0, 1.0], "t2_modulus_tau": 0.50}
          ]
        }
        with open(seed_path, 'w') as f:
            json.dump(seeds, f, indent=2)

    with open(seed_path, 'r') as f:
        data = json.load(f)
        if isinstance(data, dict):
            population = data.get("generation_0_seeds", data.get("seeds", []))
        else:
            population = data

    normalized_pop = []
    for idx, s in enumerate(population):
        cand = dict(s)
        if "candidate_id" not in cand:
            cand["candidate_id"] = cand.get("name", f"cooper_s{idx}").lower()
        if "picard_number" not in cand:
            cand["picard_number"] = cand.get("hodge_numbers", {}).get("h21", 19)
        if "moduli_stabilization" not in cand:
            cand["moduli_stabilization"] = 0.75
        if "complex_structure" not in cand:
            cand["complex_structure"] = cand.get("picard_fuchs_coefficients", [1.0, 1.0, 1.0])[:3]
        if "t2_modulus_tau" not in cand:
            cand["t2_modulus_tau"] = cand.get("complex_structure_tau", [0.5, 0.5])[0]
        normalized_pop.append(cand)
    population = normalized_pop
        
    binary_path = "./test_lean_oracle/.lake/build/bin/rpc_server"
    if not os.path.exists(binary_path):
        binary_path = "./lean_oracle/.lake/build/bin/rpc_server"

    lean_oracle = LeanOracleClient(binary_path)
    
    GENERATIONS = generations
    POP_SIZE = pop_size
    best_overall = None
    
    ckpt = EvolutionCheckpoint()
    start_gen = 1
    
    # Check for existing checkpoint
    latest_state = ckpt.load_latest_checkpoint()
    if latest_state:
        start_gen = latest_state["generation"] + 1
        population = latest_state["population"]
        best_overall = latest_state["best_candidate"]
        logger.info(f"Resumed from generation {start_gen-1}. Starting at generation {start_gen}.")
    
    start_time = time.time()
    
    for gen in range(start_gen, GENERATIONS + 1):
        time.sleep(0.5)  # Artificial delay for stress test interruption
        logger.info(f"--- Generation {gen}/{GENERATIONS} ---")
        
        # TIER 1: Mutation
        mutated_pop = []
        for parent in population:
            for _ in range(int(POP_SIZE / len(population))):
                mutated_pop.append(mutate_continuous_k3(parent, gen, len(mutated_pop)))
                
        # TIER 2: Lean 4 Gatekeeper (Symbolic Filter)
        tier2_survivors = []
        verdicts = lean_oracle.batch_evaluate(mutated_pop)
        for cand, verdict in zip(mutated_pop, verdicts):
            if verdict.get("passed_swampland", False):
                cand["formal_reason"] = verdict.get("formal_reason", "")
                tier2_survivors.append(cand)
        
        logger.info(f"Tier 2 (Lean 4) Survivors: {len(tier2_survivors)}/{len(mutated_pop)}")
        
        if not tier2_survivors:
            logger.warning("Population collapsed at Tier 2! Reverting to seeds.")
            with open(seed_path, 'r') as f:
                population = json.load(f)["generation_0_seeds"]
            continue
            
        # TIER 3: Empirical GPU Validation (Physical MCMC)
        evaluated_pop = evaluate_k3_physical(tier2_survivors)
        evaluated_pop.sort(key=lambda x: x.get("chi2_loss", 9999.9))
        
        gen_best = evaluated_pop[0]
        if best_overall is None or gen_best["chi2_loss"] < best_overall["chi2_loss"]:
            best_overall = gen_best.copy()
            
        logger.info(f"Gen {gen} Best Chi2: {gen_best['chi2_loss']:.4f} | Phenotype: w0={gen_best['phenotype']['w0']:.3f}, Om={gen_best['phenotype']['omega_m']:.3f} | PTA Freq: {gen_best['phenotype'].get('pta_f_monopole', 0):.2e} Hz | S_8: {gen_best['phenotype'].get('s8_gradient', 0):.3f}")
        
        # Select parents for next gen
        population = evaluated_pop[:5]
        
        # Re-inject global best to prevent regression
        if best_overall["candidate_id"] not in [p["candidate_id"] for p in population]:
            population[0] = best_overall.copy()

        # MLOps Checkpoint
        ckpt.save_generation(gen, population, best_overall)

    lean_oracle.close()
    
    elapsed = time.time() - start_time
    logger.info("========================================")
    logger.info("PHASE 2 PHYSICAL EVOLUTION COMPLETE")
    logger.info(f"Total Time: {elapsed:.2f}s")
    logger.info("Global Optimal Physical Candidate:")
    logger.info(json.dumps(best_overall, indent=2))
    logger.info("========================================")

if __name__ == "__main__":
    execute_phase2()
