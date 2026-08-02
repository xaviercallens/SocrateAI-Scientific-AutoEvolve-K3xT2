"""
Local Dry Run Script for Phase 0 MVP
====================================
Runs local dry run utilizing:
1. Local NVIDIA Tesla T4 GPU (cuda:0).
2. Local 500 GB storage mount (/mnt/disks/disk-socrateai-local-1/hypergraph_logs).
3. Global Cost Monitoring (< $100 budget guardrails & real-time telemetry).
4. Wolfram Engine Rate Limiter (token bucket rate management).
5. PyTorch Hadamard Tensor Masking M_{t+1} = (M_t^2 + M_t) * T up to N=20 iterations.
"""

import os
import sys
import time
import json
import torch
import numpy as np
import networkx as nx
from pathlib import Path

from hypergraph.cost_monitoring import GlobalCostMonitor
from hypergraph.rate_limiter import WolframRateLimiter, rate_limited
from hypergraph.phase0_tensor_masking import (
    create_k4_oligon_seed,
    generate_topological_mask,
    canonical_graph_hash,
)

# 500 GB Second Disk Log Mount Path
STORAGE_MOUNT_PATH = Path("/mnt/disks/disk-socrateai-local-1/hypergraph_logs")


def run_local_dry_run(
    max_steps: int = 20,
    max_budget_usd: float = 100.0,
    wolfram_rpm: int = 10,
) -> dict:
    """Executes a local dry run of the Phase 0 MVP with cost monitoring and rate limiting.

    Args:
        max_steps (int, optional): The maximum number of iterations to run. Defaults to 20.
        max_budget_usd (float, optional): The maximum budget for the dry run. Defaults to 100.0.
        wolfram_rpm (int, optional): The allowed Wolfram Engine API requests per minute. Defaults to 10.

    Returns:
        dict: A summary report of the dry run execution.
    """
    print("=================================================================")
    print("🚀 Starting Local Dry Run: Phase 0 MVP Tensor Masking & Throttling")
    print("=================================================================")

    # 1. Initialize Cost Monitor targeting 500GB disk mount
    cost_monitor = GlobalCostMonitor(
        region="us-central1",
        vcpus=4,
        ram_gb=15.0,
        gpus=1,
        disk_gb=500.0,
        max_budget_usd=max_budget_usd,
        storage_dir=STORAGE_MOUNT_PATH,
    )

    # 2. Initialize Wolfram API Rate Limiter
    wolfram_limiter = WolframRateLimiter(max_requests_per_minute=wolfram_rpm)

    @rate_limited(wolfram_limiter)
    def mock_wolfram_rule_query(rule_id: str):
        """Simulates rate-limited call to Wolfram Engine for rule verification."""
        return {"status": "VALID", "rule": rule_id, "timestamp": time.time()}

    # 3. Check Local GPU Availability
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    gpu_name = torch.cuda.get_device_name(
        0) if torch.cuda.is_available() else "CPU Mode"
    print(f"🖥️ Execution Hardware: {gpu_name} ({device})")
    print(f"📁 Log Storage Directory: {cost_monitor.storage_dir}")
    print(
        f"💰 Hourly Burn Rate Estimate: ${cost_monitor.total_hourly_burn_rate:.4f} / hr")

    # 4. Initialize K4 Oligon Seed Matrix on GPU
    M_t = create_k4_oligon_seed(vacuum_size=12).to(device)
    seen_hashes = set()
    history = []

    # Query Wolfram Engine for initial seed rule verification (rate-limited)
    mock_wolfram_rule_query("RULE_K4_OLIGON_SPLIT")

    initial_hash = canonical_graph_hash(M_t)
    seen_hashes.add(initial_hash)

    start_time = time.time()

    for step in range(1, max_steps + 1):
        # Enforce budget guardrails
        if not cost_monitor.enforce_budget_guardrails():
            print("Budget guardrail triggered. Stopping dry run gracefully.")
            break

        # Periodic Wolfram rule lookup under rate-limiter
        if step % 5 == 0:
            mock_wolfram_rule_query(f"RULE_STEP_{step}_VERIFY")

        # Execute PyTorch Hadamard rewrite step: M_{t+1} = (M_t^2 + M_t) (o) T
        from hypergraph.masking import hypergraph_step
        M_next = hypergraph_step(M_t, generate_topological_mask(M_t))

        # Local canonical graph hashing
        curr_hash = canonical_graph_hash(M_next)
        is_pruned = curr_hash in seen_hashes
        if not is_pruned:
            seen_hashes.add(curr_hash)

        # VRAM Memory Check
        if device.startswith("cuda"):
            vram_mb = torch.cuda.max_memory_allocated() / (1024 * 1024)
        else:
            vram_mb = 0.0

        non_zero_edges = torch.count_nonzero(M_next > 0.01).item()
        unmasked_sum = M_next_unmasked.sum().item()
        masked_sum = M_next.sum().item()

        step_metrics = {
            "step": step,
            "edges": non_zero_edges,
            "unmasked_sum": round(unmasked_sum, 2),
            "masked_sum": round(masked_sum, 2),
            "vram_mb": round(vram_mb, 2),
            "hash": curr_hash,
            "is_pruned": is_pruned,
        }

        history.append(step_metrics)

        # Log cost telemetry to 500GB disk
        cost_log_path = cost_monitor.log_telemetry(step_info=step_metrics)

        # Save snapshot of state on 500GB disk every 5 steps
        if step % 5 == 0 or step == max_steps:
            snapshot_file = cost_monitor.storage_dir / \
                f"snapshot_step_{step}.pt"
            torch.save(M_next.cpu(), snapshot_file)

        print(
            f"Step {step:2d}/{max_steps} | Edges: {non_zero_edges:3d} | Masked Sum: {masked_sum:8.2f} | Unmasked Sum: {unmasked_sum:10.2f} | VRAM: {vram_mb:6.1f} MB | Hash: {curr_hash[:8]} | Pruned: {is_pruned}")

        M_t = M_next

    total_elapsed = time.time() - start_time
    cost_summary = cost_monitor.calculate_current_cost()

    summary_report = {
        "status": "COMPLETED",
        "total_steps": len(history),
        "total_time_seconds": round(
            total_elapsed,
            3),
        "unique_isomorphic_hashes": len(seen_hashes),
        "hardware_used": gpu_name,
        "disk_log_mount": str(
            cost_monitor.storage_dir),
        "wolfram_queries_issued": wolfram_limiter.total_queries_issued,
        "wolfram_total_wait_sec": round(
            wolfram_limiter.total_throttle_wait_sec,
            3),
        "cost_summary": cost_summary,
    }

    # Save final report to 500GB storage disk
    final_report_file = cost_monitor.storage_dir / "dry_run_final_report.json"
    with open(final_report_file, "w") as f:
        json.dump(summary_report, f, indent=2)

    print("\n=================================================================")
    print("✅ LOCAL DRY RUN SUCCESSFULLY COMPLETED!")
    print(f"📊 Report Saved to 500GB Mount: {final_report_file}")
    print(
        f"💰 Total Estimated Dry Run Cost: ${cost_summary['total_cost_usd']:.6f} USD")
    print(
        f"⚡ Unique Isomorphic States: {len(seen_hashes)} | Wolfram Queries: {wolfram_limiter.total_queries_issued}")
    print("=================================================================")

    return summary_report


if __name__ == "__main__":
    run_local_dry_run(max_steps=20)
