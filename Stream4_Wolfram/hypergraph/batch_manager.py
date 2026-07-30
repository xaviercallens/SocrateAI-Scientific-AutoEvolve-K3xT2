"""
Batch Simulation Manager for Long-Running Hypergraph Runs
==========================================================
Executes timed batch runs (e.g., 1-hour continuous simulation), storing full state
checkpoints, graph spectra, topological invariants, and cost metrics to the 500 GB storage mount.
"""

import sys
import time
import json
import torch
import numpy as np
from pathlib import Path

from hypergraph.cost_monitoring import GlobalCostMonitor
from hypergraph.rate_limiter import WolframRateLimiter, rate_limited
from hypergraph.phase0_tensor_masking import (
    create_k4_oligon_seed,
    generate_topological_mask,
    canonical_graph_hash,
)

BATCH_STORAGE_DIR = Path(
    "/mnt/disks/disk-socrateai-local-1/hypergraph_logs/batch_runs")


class BatchManager:
    def __init__(
        self,
        duration_seconds: float = 3600.0,  # 1 hour default
        vacuum_size: int = 16,
        max_budget_usd: float = 100.0,
        snapshot_interval_steps: int = 5,
        storage_dir: Path = BATCH_STORAGE_DIR,
    ):
        """Initializes the BatchManager for long-running simulations.

        Args:
            duration_seconds (float, optional): Duration to run the batch. Defaults to 3600.0.
            vacuum_size (int, optional): Size of the vacuum lattice ring. Defaults to 16.
            max_budget_usd (float, optional): Max execution budget in USD. Defaults to 100.0.
            snapshot_interval_steps (int, optional): Interval for state checkpoints. Defaults to 5.
            storage_dir (Path, optional): Directory to store logs and states. Defaults to BATCH_STORAGE_DIR.
        """
        self.duration_seconds = duration_seconds
        self.vacuum_size = vacuum_size
        self.max_budget_usd = max_budget_usd
        self.snapshot_interval_steps = snapshot_interval_steps
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.cost_monitor = GlobalCostMonitor(
            disk_gb=500.0,
            max_budget_usd=max_budget_usd,
            storage_dir=self.storage_dir,
        )
        self.wolfram_limiter = WolframRateLimiter(max_requests_per_minute=10)

        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.seen_hashes: set[str] = set()
        self.step_history: list[dict] = []

    def compute_graph_spectrum(self, M_t: torch.Tensor) -> list:
        """Computes top eigenvalues of the adjacency matrix for continuum limit spectral analysis."""
        adj_np = M_t.cpu().detach().numpy()
        eigenvalues = np.linalg.eigvalsh(adj_np)
        # Return sorted top 8 real eigenvalues
        top_eigs = np.sort(eigenvalues)[::-1][:8]
        return [round(float(e), 4) for e in top_eigs]

    def run_batch(self) -> dict:
        """Runs the long-duration batch simulation.

        Returns:
            dict: The final status summary of the batch run.
        """
        print(f"=================================================================")
        print(f"🚀 Launching Hypergraph Batch Manager")
        print(
            f"Target Duration: {self.duration_seconds / 60.0:.1f} minutes ({self.duration_seconds:.0f} seconds)")
        print(f"Device: {self.device} | Storage Dir: {self.storage_dir}")
        print(f"=================================================================")

        start_time = time.time()
        end_time = start_time + self.duration_seconds

        M_t = create_k4_oligon_seed(
            vacuum_size=self.vacuum_size).to(
            self.device)
        initial_hash = canonical_graph_hash(M_t)
        self.seen_hashes.add(initial_hash)

        step = 0
        while time.time() < end_time:
            step += 1
            now = time.time()
            elapsed = now - start_time
            remaining_time = max(0.0, end_time - now)

            # Check budget guardrails
            if not self.cost_monitor.enforce_budget_guardrails():
                print("⚠️ Budget guardrail exceeded. Ending batch run early.")
                break

            # Perform Hadamard rewrite: M_{t+1} = (M_t^2 + M_t) * T
            T = generate_topological_mask(M_t)
            M_sq = torch.matmul(M_t, M_t)
            M_next_unmasked = M_sq + M_t
            M_next = M_next_unmasked * T
            M_next = torch.clamp(M_next, 0.0, 100.0)

            # Graph metrics & spectrum
            curr_hash = canonical_graph_hash(M_next)
            is_pruned = curr_hash in self.seen_hashes
            if not is_pruned:
                self.seen_hashes.add(curr_hash)

            top_eigs = self.compute_graph_spectrum(M_next)
            non_zero_edges = torch.count_nonzero(M_next > 0.01).item()
            masked_sum = M_next.sum().item()
            unmasked_sum = M_next_unmasked.sum().item()

            vram_mb = (
                torch.cuda.max_memory_allocated() / (1024 * 1024)
                if self.device.startswith("cuda")
                else 0.0
            )

            step_record = {
                "step": step,
                "elapsed_sec": round(elapsed, 2),
                "remaining_sec": round(remaining_time, 2),
                "non_zero_edges": non_zero_edges,
                "masked_sum": round(masked_sum, 2),
                "unmasked_sum": round(unmasked_sum, 2),
                "top_eigenvalues": top_eigs,
                "vram_mb": round(vram_mb, 2),
                "hash": curr_hash,
                "is_pruned": is_pruned,
            }
            self.step_history.append(step_record)

            # Save checkpoint & update batch status JSON on disk
            if step % self.snapshot_interval_steps == 0 or remaining_time <= 0:
                checkpoint_file = self.storage_dir / \
                    f"checkpoint_step_{step}.pt"
                torch.save(M_next.cpu(), checkpoint_file)

            status_payload = {
                "status": "RUNNING" if remaining_time > 0 else "FINISHED",
                "current_step": step,
                "elapsed_seconds": round(
                    elapsed,
                    2),
                "duration_seconds": self.duration_seconds,
                "progress_pct": round(
                    (elapsed / self.duration_seconds) * 100.0,
                    1),
                "unique_hashes": len(
                    self.seen_hashes),
                "latest_step_record": step_record,
                "cost_summary": self.cost_monitor.calculate_current_cost(),
            }

            with open(self.storage_dir / "batch_status.json", "w") as f:
                json.dump(status_payload, f, indent=2)

            print(
                f"Step {step:4d} | Elapsed: {elapsed:6.1f}s / {self.duration_seconds:.0f}s | "
                f"Edges: {non_zero_edges:3d} | Masked Sum: {masked_sum:8.2f} | "
                f"Top Eig: {top_eigs[0]:.2f} | VRAM: {vram_mb:.1f} MB | Hash: {curr_hash[:8]}")

            M_t = M_next
            # Micro sleep to allow system monitoring and avoid 100% spin
            time.sleep(0.5)

        total_elapsed = time.time() - start_time
        final_status = {
            "status": "COMPLETED",
            "total_steps": step,
            "total_duration_seconds": round(total_elapsed, 2),
            "unique_isomorphic_hashes": len(self.seen_hashes),
            "device": self.device,
            "final_cost": self.cost_monitor.calculate_current_cost(),
            "storage_dir": str(self.storage_dir),
        }

        with open(self.storage_dir / "batch_final_summary.json", "w") as f:
            json.dump(final_status, f, indent=2)

        print("=================================================================")
        print(
            f"✅ Batch Manager Run Finished ({step} steps in {total_elapsed:.1f}s)")
        print(
            f"Summary Report: {self.storage_dir / 'batch_final_summary.json'}")
        print("=================================================================")

        return final_status


if __name__ == "__main__":
    # If run directly with argument, e.g. python3 batch_manager.py 3600
    # 60 sec test default, or 3600 for full hour
    dur = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    manager = BatchManager(duration_seconds=dur, snapshot_interval_steps=5)
    manager.run_batch()
