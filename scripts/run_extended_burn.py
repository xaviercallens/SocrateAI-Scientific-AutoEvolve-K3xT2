"""
Extended Deep Burn — Generations 151-300
Picks up from gen-150 GCS checkpoint and continues.
Writes live status to outputs/local_deep_burn/burn_monitor.json
for easy real-time monitoring.
"""
import os
import sys
import time
import json
import logging
import datetime

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.makedirs("./outputs/local_deep_burn", exist_ok=True)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.run_phase2_physical_k3_t2 import (
    execute_phase2, mutate_continuous_k3, evaluate_k3_physical
)
from utils.mlops_logger import EvolutionCheckpoint
from integration.lean_client import LeanOracleClient

# --- Logging setup ---
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
fh = logging.FileHandler("./outputs/local_deep_burn/extended_burn.log")
fh.setFormatter(log_formatter)
root_logger.addHandler(fh)
sh = logging.StreamHandler()
sh.setFormatter(log_formatter)
root_logger.addHandler(sh)

MONITOR_FILE = "./outputs/local_deep_burn/burn_monitor.json"
TARGET_GENS  = 300
POP_SIZE     = 40

def write_monitor(gen, total_gens, best, start_time, all_best_chi2):
    elapsed = time.time() - start_time
    eta_sec = (elapsed / max(1, gen)) * (total_gens - gen)
    status = {
        "timestamp":       datetime.datetime.utcnow().isoformat() + "Z",
        "status":          "🔥 RUNNING",
        "generation":      gen,
        "total_gens":      total_gens,
        "progress_pct":    round(100 * gen / total_gens, 1),
        "elapsed_min":     round(elapsed / 60, 2),
        "eta_min":         round(eta_sec / 60, 2),
        "best_candidate":  best.get("candidate_id", "—"),
        "best_chi2":       best.get("chi2_loss", 9999),
        "best_fitness":    best.get("likelihood", {}).get("fitness", 0),
        "phenotype": {
            "w0":              best.get("phenotype", {}).get("w0", None),
            "omega_m":         best.get("phenotype", {}).get("omega_m", None),
            "h0":              best.get("phenotype", {}).get("h0", None),
            "s8":              best.get("phenotype", {}).get("s8_gradient", None),
            "pta_f_monopole":  best.get("phenotype", {}).get("pta_f_monopole", None),
        },
        "picard_number":   best.get("picard_number", None),
        "lean4_status":    best.get("formal_reason", "—"),
        "gcs_checkpoint":  f"gs://socrateai-datalake-gen-lang-client-0625573011/checkpoints/run_20260729_074350_gen_{gen:04d}.json",
        "convergence_history_last10": all_best_chi2[-10:],
    }
    with open(MONITOR_FILE, "w") as f:
        json.dump(status, f, indent=2)


if __name__ == "__main__":
    logging.info("=" * 60)
    logging.info("🔥 EXTENDED DEEP BURN — Gens 151→300 (pop=40)")
    logging.info("=" * 60)

    seed_path    = "./configs/cooper_seeds.json"
    binary_path  = "./test_lean_oracle/.lake/build/bin/rpc_server"
    if not os.path.exists(binary_path):
        binary_path = "./lean_oracle/.lake/build/bin/rpc_server"

    lean_oracle  = LeanOracleClient(binary_path)
    ckpt         = EvolutionCheckpoint()
    start_time   = time.time()
    all_best_chi2 = []

    # Resume from latest checkpoint (gen 150)
    latest_state = ckpt.load_latest_checkpoint()
    if latest_state:
        start_gen    = latest_state["generation"] + 1
        population   = latest_state["population"]
        best_overall = latest_state["best_candidate"]
        logging.info(f"✅ Resumed from GCS checkpoint gen={latest_state['generation']}. Starting at gen={start_gen}.")
    else:
        logging.warning("No checkpoint found — starting fresh from seeds.")
        with open(seed_path) as f:
            data = json.load(f)
        population   = data.get("generation_0_seeds", data)
        best_overall = None
        start_gen    = 1

    for gen in range(start_gen, TARGET_GENS + 1):
        time.sleep(0.4)

        # TIER 1: Mutation
        mutated = []
        for parent in population:
            for _ in range(POP_SIZE // max(1, len(population))):
                mutated.append(mutate_continuous_k3(parent, gen, len(mutated)))

        # TIER 2: Lean 4 Swampland Gate
        survivors = []
        verdicts = lean_oracle.batch_evaluate(mutated)
        for cand, verdict in zip(mutated, verdicts):
            if verdict.get("passed_swampland", False):
                cand["formal_reason"] = verdict.get("formal_reason", "")
                survivors.append(cand)

        logging.info(f"Gen {gen:3d}/{TARGET_GENS} | Lean4 survivors: {len(survivors)}/{len(mutated)}")

        if not survivors:
            logging.warning("Population collapsed — reverting to seeds.")
            with open(seed_path) as f:
                population = json.load(f)["generation_0_seeds"]
            continue

        # TIER 3: Physical MCMC Evaluation
        evaluated = evaluate_k3_physical(survivors)
        evaluated.sort(key=lambda x: x.get("chi2_loss", 9999.9))
        gen_best  = evaluated[0]

        if best_overall is None or gen_best["chi2_loss"] < best_overall["chi2_loss"]:
            best_overall = gen_best.copy()

        all_best_chi2.append(round(best_overall["chi2_loss"], 8))

        logging.info(
            f"  ↳ Best χ²={gen_best['chi2_loss']:.2e} | "
            f"w₀={gen_best['phenotype']['w0']:.5f} | "
            f"Ωm={gen_best['phenotype']['omega_m']:.3f} | "
            f"S₈={gen_best['phenotype'].get('s8_gradient',0):.3f} | "
            f"f_PTA={gen_best['phenotype'].get('pta_f_monopole',0):.3e} Hz | "
            f"P={gen_best.get('picard_number','?')}"
        )

        # Select elites
        population = evaluated[:5]
        if best_overall["candidate_id"] not in [p["candidate_id"] for p in population]:
            population[0] = best_overall.copy()

        # Checkpoint
        ckpt.save_generation(gen, population, best_overall)

        # Write live monitor file
        write_monitor(gen, TARGET_GENS, best_overall, start_time, all_best_chi2)

    lean_oracle.close()
    elapsed_h = (time.time() - start_time) / 3600

    # Final monitor snapshot
    if best_overall:
        best_overall["_status"] = "COMPLETE"
    write_monitor(TARGET_GENS, TARGET_GENS, best_overall or {}, start_time, all_best_chi2)

    logging.info("=" * 60)
    logging.info("🏁 EXTENDED BURN COMPLETE")
    logging.info(f"   Runtime : {elapsed_h:.3f} h")
    logging.info(f"   Best χ² : {best_overall['chi2_loss']:.6e}")
    logging.info(f"   Candidate: {best_overall['candidate_id']}")
    logging.info(f"   P(Picard): {best_overall.get('picard_number')}")
    logging.info("=" * 60)
    logging.info(json.dumps(best_overall, indent=2))
