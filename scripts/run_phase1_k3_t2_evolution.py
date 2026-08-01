import os
import sys
import json
import logging
import time
import random

# Ensure src/ is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from integration.lean_client import LeanOracleClient

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Continuous Genetic Operator ---
def mutate_continuous_k3(candidate: dict, gen: int, cand_idx: int) -> dict:
    """Mutates continuous T2 moduli and complex structures for K3xT2."""
    child = candidate.copy()
    base_id = candidate.get('candidate_id', 'cand').split('_g')[0]
    child["candidate_id"] = f"{base_id}_g{gen}_{cand_idx}"
    
    # Mutate T2 Modulus (Continuous)
    if "t2_modulus_tau" not in child:
        child["t2_modulus_tau"] = 0.5
    child["t2_modulus_tau"] += random.uniform(-0.05, 0.05)
    
    # Mutate Complex Structure (Continuous Vector)
    if "complex_structure" not in child:
        child["complex_structure"] = [1.0, 1.0, 1.0]
    child["complex_structure"] = [
        val + random.uniform(-0.1, 0.1) for val in child["complex_structure"]
    ]
    
    # Occasionally mutate Picard Number (Integer constraints)
    if "picard_number" not in child:
        child["picard_number"] = 19
    if random.random() > 0.8:
        child["picard_number"] += random.choice([-1, 1])
        
    return child

# --- Mock Physical Evaluator (Pre-TPU Integration) ---
def evaluate_k3_phenotype(candidates: list) -> list:
    """Mocks the Antigravity TPU evaluating PTA frequencies and Euclid S_8."""
    target_picard = 19
    target_tau = 0.50
    
    for cand in candidates:
        p_diff = abs(cand.get("picard_number", 19) - target_picard)
        t_diff = abs(cand.get("t2_modulus_tau", 0.5) - target_tau)
        
        # Simplified Phase 1 Chi-Square fitness
        cand["chi2_loss"] = p_diff + (t_diff * 10)
    return candidates

def execute_phase1():
    logger.info("Initializing Phase 1: Dual-Scale K3xT2 Evolution Engine")
    
    # 1. Load or Generate Gen 0 Cooper Seeds
    seed_path = "./configs/cooper_seeds.json"
    if not os.path.exists(seed_path):
        os.makedirs(os.path.dirname(seed_path), exist_ok=True)
        seeds = {
          "generation_0_seeds": [
            {"candidate_id": "cooper_s7", "picard_number": 19, "moduli_stabilization": 0.85, "complex_structure": [1.0, -0.5, 0.25], "t2_modulus_tau": 0.6},
            {"candidate_id": "cooper_s10", "picard_number": 18, "moduli_stabilization": 0.60, "complex_structure": [0.8, -0.2, 0.1], "t2_modulus_tau": 0.7},
            {"candidate_id": "cooper_s22", "picard_number": 20, "moduli_stabilization": 0.45, "complex_structure": [0.5, 0.0, 0.0], "t2_modulus_tau": 0.4}
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

    # Normalize candidate seed fields if loaded from generic seeds
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
        
    # 2. Boot the Lean 4 Symbolic Gatekeeper
    binary_path = "./test_lean_oracle/.lake/build/bin/rpc_server"
    if not os.path.exists(binary_path):
        binary_path = "./lean_oracle/.lake/build/bin/rpc_server"

    if not os.path.exists(binary_path):
         logger.error(f"Lean binary not found at {binary_path}. Did you compile it?")
         return

    lean_oracle = LeanOracleClient(binary_path)
    
    GENERATIONS = 25
    POP_SIZE = 60
    best_overall = None
    
    start_time = time.time()
    
    for gen in range(1, GENERATIONS + 1):
        logger.info(f"--- Generation {gen}/{GENERATIONS} ---")
        
        # TIER 1: Mutation (Continuous Expansion)
        mutated_pop = []
        for parent in population:
            for i in range(int(POP_SIZE / len(population))):
                mutated_pop.append(mutate_continuous_k3(parent, gen, len(mutated_pop)))
                
        # TIER 2: Lean 4 Gatekeeper (Batch Mode)
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
            
        # TIER 3: Empirical GPU Validation (Mocked)
        evaluated_pop = evaluate_k3_phenotype(tier2_survivors)
        evaluated_pop.sort(key=lambda x: x["chi2_loss"])
        
        # Global Elitism Hard-Bypass (Fix applied from Phase 0)
        gen_best = evaluated_pop[0]
        if best_overall is None or gen_best["chi2_loss"] < best_overall["chi2_loss"]:
            best_overall = gen_best.copy()
            
        logger.info(f"Gen {gen} Best Chi2: {gen_best['chi2_loss']:.4f} | Topology: P={gen_best.get('picard_number')}, Tau={gen_best.get('t2_modulus_tau', 0):.4f}")
        
        # Select parents for next gen
        population = evaluated_pop[:10]
        
        # Re-inject global best to prevent regression
        if best_overall["candidate_id"] not in [p["candidate_id"] for p in population]:
            population[0] = best_overall.copy()

    lean_oracle.close()
    
    elapsed = time.time() - start_time
    logger.info("========================================")
    logger.info("PHASE 1 EVOLUTION COMPLETE")
    logger.info(f"Total Time: {elapsed:.2f}s")
    logger.info("Global Optimal K3xT2 Candidate:")
    logger.info(json.dumps(best_overall, indent=2))
    logger.info("========================================")

if __name__ == "__main__":
    execute_phase1()
