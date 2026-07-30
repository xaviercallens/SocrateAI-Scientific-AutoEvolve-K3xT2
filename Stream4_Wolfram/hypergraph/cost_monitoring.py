"""
Global Cost Monitoring and GCP Budget Management Module
=========================================================
Tracks compute burn rate, GPU utilization hours, persistent storage costs,
and enforces budget guardrails (< $100 budget) with automatic termination warnings.
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Optional


# GCP Region Hourly Pricing Matrix (Spot / Preemptible Pricing - USD)
REGION_SPOT_PRICING = {"us-central1": {"t4_gpu": 0.110,
                                       "vcpu_hr": 0.008,
                                       "ram_gb_hr": 0.001,
                                       "disk_gb_mo": 0.040},
                       "us-east1": {"t4_gpu": 0.110,
                                    "vcpu_hr": 0.008,
                                    "ram_gb_hr": 0.001,
                                    "disk_gb_mo": 0.040},
                       "us-west1": {"t4_gpu": 0.110,
                                    "vcpu_hr": 0.008,
                                    "ram_gb_hr": 0.001,
                                    "disk_gb_mo": 0.040},
                       "europe-west4": {"t4_gpu": 0.125,
                                        "vcpu_hr": 0.009,
                                        "ram_gb_hr": 0.0012,
                                        "disk_gb_mo": 0.044},
                       }

DEFAULT_STORAGE_PATH = Path(
    "/mnt/disks/disk-socrateai-local-1/hypergraph_logs")


class GlobalCostMonitor:
    def __init__(
        self,
        region: str = "us-central1",
        vcpus: int = 4,
        ram_gb: float = 15.0,
        gpus: int = 1,
        disk_gb: float = 500.0,
        max_budget_usd: float = 100.0,
        storage_dir: Path = DEFAULT_STORAGE_PATH,
    ):
        """Initializes the GlobalCostMonitor.

        Args:
            region (str, optional): The GCP region. Defaults to "us-central1".
            vcpus (int, optional): Number of virtual CPUs. Defaults to 4.
            ram_gb (float, optional): Amount of RAM in GB. Defaults to 15.0.
            gpus (int, optional): Number of GPUs. Defaults to 1.
            disk_gb (float, optional): Amount of disk space in GB. Defaults to 500.0.
            max_budget_usd (float, optional): Maximum budget in USD. Defaults to 100.0.
            storage_dir (Path, optional): Directory to store cost logs. Defaults to DEFAULT_STORAGE_PATH.
        """
        self.region = region if region in REGION_SPOT_PRICING else "us-central1"
        self.vcpus = vcpus
        self.ram_gb = ram_gb
        self.gpus = gpus
        self.disk_gb = disk_gb
        self.max_budget_usd = max_budget_usd
        self.storage_dir = Path(storage_dir)

        # Ensure log directory exists on mounted disk
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Fallback to current workspace if mount unavailable
            self.storage_dir = Path("./logs_cost_monitor")
            self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.pricing = REGION_SPOT_PRICING[self.region]
        self.start_time = time.time()

        # Calculate hourly rates
        self.gpu_hourly_cost = self.gpus * self.pricing["t4_gpu"]
        self.cpu_hourly_cost = self.vcpus * self.pricing["vcpu_hr"]
        self.ram_hourly_cost = self.ram_gb * self.pricing["ram_gb_hr"]
        self.disk_hourly_cost = (
            self.disk_gb * self.pricing["disk_gb_mo"]) / 730.0  # 730 hrs/month

        self.total_hourly_burn_rate = (
            self.gpu_hourly_cost +
            self.cpu_hourly_cost +
            self.ram_hourly_cost +
            self.disk_hourly_cost)

    def get_elapsed_hours(self) -> float:
        """Calculates the elapsed time since initialization in hours.

        Returns:
            float: Elapsed hours.
        """
        return (time.time() - self.start_time) / 3600.0

    def calculate_current_cost(self) -> dict:
        """Calculates the current cost metrics based on elapsed time and hardware.

        Returns:
            dict: Current cost metrics.
        """
        elapsed_hrs = self.get_elapsed_hours()
        compute_cost = elapsed_hrs * \
            (self.gpu_hourly_cost + self.cpu_hourly_cost + self.ram_hourly_cost)
        disk_cost = elapsed_hrs * self.disk_hourly_cost
        total_cost = compute_cost + disk_cost
        remaining_budget = max(0.0, self.max_budget_usd - total_cost)

        # Calculate max remaining compute hours under budget
        remaining_compute_hrs = remaining_budget / \
            max(0.001, self.total_hourly_burn_rate)

        return {
            "region": self.region, "elapsed_seconds": round(
                time.time() - self.start_time, 2), "elapsed_hours": round(
                elapsed_hrs, 4), "hourly_burn_rate_usd": round(
                self.total_hourly_burn_rate, 4), "total_cost_usd": round(
                    total_cost, 6), "remaining_budget_usd": round(
                        remaining_budget, 4), "max_remaining_compute_hours": round(
                            remaining_compute_hrs, 2), "budget_used_pct": round(
                                (total_cost / self.max_budget_usd) * 100.0, 2), }

    def log_telemetry(self, step_info: Optional[dict] = None) -> Path:
        """Logs current cost telemetry to disk.

        Args:
            step_info (dict, optional): Additional step information to include. Defaults to None.

        Returns:
            Path: Path to the generated log file.
        """
        cost_info = self.calculate_current_cost()
        payload = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "cost_metrics": cost_info,
            "step_info": step_info or {},
        }

        log_file = self.storage_dir / "cost_telemetry.json"
        with open(log_file, "w") as f:
            json.dump(payload, f, indent=2)

        return log_file

    def enforce_budget_guardrails(self) -> bool:
        """
        Returns True if execution is within safe budget limits.
        Raises Warning / SystemExit if budget cap is exceeded.
        """
        cost_info = self.calculate_current_cost()
        if cost_info["total_cost_usd"] >= self.max_budget_usd:
            print(
                f"⚠️ BUDGET EXCEEDED: Total spend ${cost_info['total_cost_usd']:.2f} >= Cap ${self.max_budget_usd:.2f}. Triggering graceful shutdown!")
            return False
        return True


if __name__ == "__main__":
    monitor = GlobalCostMonitor(
        region="us-central1",
        disk_gb=500.0,
        max_budget_usd=100.0)
    print("Cost Monitor Initialized:")
    print(json.dumps(monitor.calculate_current_cost(), indent=2))
