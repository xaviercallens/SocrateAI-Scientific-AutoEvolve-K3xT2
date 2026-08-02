import sys
import os
import json
import logging

# Ensure src/ and pipeline/ are in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from scripts.run_phase2_physical_k3_t2 import evaluate_k3_physical

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def benchmark_cooper_sequences():
    """
    Evaluates known Cooper / Apéry-like K3 topological sequences 
    against the new comprehensive Phase 5 pipeline (including JWST + PTA constraints)
    to find the most probable geometric vacuum.
    """
    logger.info("Initializing K3 Sequence Benchmark (Phase 5)...")
    
    # Baseline Cooper sequences (s7, s10, s22, etc.)
    # Picard ranks and stabilizations are approximate from prior literature / exploration
    sequences_to_test = [
        {
            "candidate_id": "cooper_s7",
            "sequence_type": "Apéry-like",
            "picard_number": 19,
            "t2_modulus_tau": 0.50,
            "complex_structure": [1.0, 1.0, 1.0]
        },
        {
            "candidate_id": "cooper_s8",
            "sequence_type": "Apéry-like",
            "picard_number": 17,
            "t2_modulus_tau": 0.55,
            "complex_structure": [0.8, 0.5, 0.5]
        },
        {
            "candidate_id": "cooper_s9",
            "sequence_type": "Apéry-like",
            "picard_number": 18,
            "t2_modulus_tau": 0.52,
            "complex_structure": [0.9, 0.8, 0.7]
        },
        {
            "candidate_id": "cooper_s10",
            "sequence_type": "Apéry-like",
            "picard_number": 19, 
            "t2_modulus_tau": 0.50,
            "complex_structure": [1.0, 0.0, 0.0]
        },
        {
            "candidate_id": "cooper_s11",
            "sequence_type": "Apéry-like",
            "picard_number": 19,
            "t2_modulus_tau": 0.48,
            "complex_structure": [0.5, 0.5, 1.0]
        },
        {
            "candidate_id": "cooper_s22",
            "sequence_type": "Apéry-like",
            "picard_number": 20, 
            "t2_modulus_tau": 0.45,
            "complex_structure": [1.0, -1.0, 0.0]
        },
        # --- NEW STRATEGIC PLAN SEQUENCES ---
        {
            "candidate_id": "apery_zeta3",
            "sequence_type": "Apéry Class (Rank 1)",
            "picard_number": 19,
            "t2_modulus_tau": 0.48,
            "complex_structure": [1.0, 1.0, 0.5]
        },
        {
            "candidate_id": "apery_zeta2",
            "sequence_type": "Apéry Class (Rank 1)",
            "picard_number": 19,
            "t2_modulus_tau": 0.49,
            "complex_structure": [0.8, 1.2, 0.2]
        },
        {
            "candidate_id": "domb_rank2",
            "sequence_type": "Domb Class (Rank 2)",
            "picard_number": 19,
            "t2_modulus_tau": 0.47,
            "complex_structure": [0.9, 0.9, 0.9]
        },
        {
            "candidate_id": "cy_209_almkvist",
            "sequence_type": "CY Class (Rank 3)",
            "picard_number": 20,
            "t2_modulus_tau": 0.44,
            "complex_structure": [1.0, -0.5, 0.5]
        },
        {
            "candidate_id": "cy_195_almkvist",
            "sequence_type": "CY Class (Rank 3)",
            "picard_number": 20,
            "t2_modulus_tau": 0.42,
            "complex_structure": [0.5, -0.5, -0.5]
        },
        {
            "candidate_id": "zagier_case_e",
            "sequence_type": "Sporadic (Medium)",
            "picard_number": 18,
            "t2_modulus_tau": 0.55,
            "complex_structure": [0.7, 0.7, 0.0]
        },
        {
            "candidate_id": "zagier_case_h",
            "sequence_type": "Sporadic (Medium)",
            "picard_number": 18,
            "t2_modulus_tau": 0.58,
            "complex_structure": [0.3, 0.3, 0.3]
        }
    ]

    # Evaluate all sequences via the Phase 2 Physical MCMC Tier
    # (This includes the new JWST likelihood and scalar potential EFT constraints)
    evaluated_seqs = evaluate_k3_physical(sequences_to_test)
    
    # Sort by the final Chi^2 Loss (lowest is most probable)
    evaluated_seqs.sort(key=lambda x: x.get("chi2_loss", 9999.9))
    
    # Generate Output Table
    print("\n" + "="*95)
    print(" K3xT2 TOPOLOGICAL SEQUENCE BENCHMARK REPORT (PHASE 5)")
    print("="*95)
    print(f"{'Rank':<6} | {'Sequence':<12} | {'Picard (P)':<10} | {'Tau':<6} | {'Omega_m':<8} | {'S_8':<6} | {'m_FDM (eV)':<12} | {'Total Chi2':<10}")
    print("-" * 95)
    
    for rank, seq in enumerate(evaluated_seqs):
        pheno = seq.get("phenotype", {})
        gamma = pheno.get("pta_spectral_index", 4.333)
        m_fdm = 1e-22 * (gamma / 4.847)**2
        
        rank_str = f"#{rank+1}"
        seq_id = seq['candidate_id']
        picard = seq['picard_number']
        tau = f"{seq['t2_modulus_tau']:.3f}"
        omega = f"{pheno.get('omega_m', 0):.3f}"
        s8 = f"{pheno.get('s8_gradient', 0):.3f}"
        mfdm_str = f"{m_fdm:.2e}"
        chi2 = f"{seq.get('chi2_loss', 9999.9):.3f}"
        
        print(f"{rank_str:<6} | {seq_id:<12} | {picard:<10} | {tau:<6} | {omega:<8} | {s8:<6} | {mfdm_str:<12} | {chi2:<10}")
        
    print("="*95 + "\n")
    
    # Save results
    os.makedirs("./artifacts", exist_ok=True)
    with open("./artifacts/sequence_benchmark_results.json", "w") as f:
        json.dump(evaluated_seqs, f, indent=2)
        
    logger.info("Benchmark complete. Results saved to ./artifacts/sequence_benchmark_results.json")

if __name__ == "__main__":
    benchmark_cooper_sequences()
