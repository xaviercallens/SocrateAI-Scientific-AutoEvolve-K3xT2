"""
Vertex AI Campaign Budget Guardrail (Phase 4 Cost Control)
==========================================================
Hard-caps cloud compute spending at a configurable budget ceiling ($25 USD
default). Monitors wall-clock time and estimated cost in real-time, triggers
a graceful shutdown checkpoint when the ceiling is approached.

Integration Points:
    - MCMCCoordinator.run() → checks budget_guard.is_safe() before each iteration
    - deploy_vertex_job_optimized.sh → sets env vars for rate and ceiling
    - GCS checkpoint → saved on budget-triggered shutdown for resume

Architecture:
    ┌─────────────┐      ┌──────────────┐      ┌────────────────┐
    │ Orchestrator │─────▶│ BudgetGuard  │─────▶│ GCS Checkpoint │
    │  (run loop)  │      │ (wall-clock) │      │  (graceful)    │
    └─────────────┘      └──────────────┘      └────────────────┘
         │                     ▲
         │                     │ ENV VARS:
         │                CAMPAIGN_BUDGET_USD
         │                HOURLY_RATE_USD
         │                CAMPAIGN_DURATION_HOURS
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class BudgetConfig:
    """Budget guardrail configuration."""
    # Hard spending ceiling
    budget_ceiling_usd: float = 25.00

    # Estimated hourly rate for the provisioned VM+GPU combo
    # spot-l4: ~$0.24/hr | spot-t4: ~$0.36/hr | ondemand-t4: ~$0.73/hr
    hourly_rate_usd: float = 0.24

    # Maximum campaign duration in hours (secondary cap)
    max_duration_hours: float = 24.0

    # Reserve margin: stop this many $ before ceiling to allow checkpoint save
    reserve_margin_usd: float = 1.50

    # Alert thresholds (percentage of budget)
    warn_at_percent: float = 70.0
    critical_at_percent: float = 90.0

    # How often to check budget (seconds)
    check_interval_seconds: float = 60.0

    # GCS path for budget-triggered emergency checkpoints
    gcs_checkpoint_dir: str = "gs://socrateai-datalake-gen-lang-client-0625573011/checkpoints"

    @classmethod
    def from_environment(cls) -> "BudgetConfig":
        """Load config from environment variables (set by deploy script)."""
        return cls(
            budget_ceiling_usd=float(os.environ.get(
                "CAMPAIGN_BUDGET_USD", "25.00"
            )),
            hourly_rate_usd=float(os.environ.get(
                "HOURLY_RATE_USD", "0.24"
            )),
            max_duration_hours=float(os.environ.get(
                "CAMPAIGN_DURATION_HOURS", "24"
            )),
            gcs_checkpoint_dir=os.environ.get(
                "GCS_CHECKPOINT_DIR",
                "gs://socrateai-datalake-gen-lang-client-0625573011/checkpoints"
            ),
        )


class BudgetGuard:
    """
    Real-time wall-clock-based budget guardrail for Vertex AI campaigns.

    Monitors elapsed time × hourly rate and enforces a hard USD ceiling.
    Designed to be queried by the MCMC coordinator before each chain
    iteration to decide whether to continue or gracefully checkpoint+stop.

    Usage:
        guard = BudgetGuard(BudgetConfig.from_environment())
        guard.start()

        while not guard.is_budget_exhausted():
            # ... run next MCMC chain iteration ...
            status = guard.check()
            if status["action"] == "STOP":
                save_checkpoint()
                break
    """

    def __init__(self, config: BudgetConfig = None):
        self.config = config or BudgetConfig.from_environment()
        self.start_time: Optional[float] = None
        self._stopped = False

        # Derived: maximum runtime in seconds before budget is exhausted
        budget_limited_hours = (
            self.config.budget_ceiling_usd - self.config.reserve_margin_usd
        ) / max(self.config.hourly_rate_usd, 0.01)
        self.max_runtime_seconds = min(
            budget_limited_hours * 3600,
            self.config.max_duration_hours * 3600,
        )

        logger.info(
            f"BudgetGuard initialized: "
            f"ceiling=${self.config.budget_ceiling_usd:.2f}, "
            f"rate=${self.config.hourly_rate_usd:.2f}/hr, "
            f"max_runtime={self.max_runtime_seconds/3600:.1f}h"
        )

    def start(self) -> None:
        """Mark campaign start time."""
        self.start_time = time.monotonic()
        self._stopped = False
        logger.info("⏱️  BudgetGuard: Campaign timer started.")

    def elapsed_seconds(self) -> float:
        """Seconds since campaign start."""
        if self.start_time is None:
            return 0.0
        return time.monotonic() - self.start_time

    def elapsed_hours(self) -> float:
        """Hours since campaign start."""
        return self.elapsed_seconds() / 3600.0

    def estimated_spend_usd(self) -> float:
        """Current estimated spend based on wall clock."""
        return self.elapsed_hours() * self.config.hourly_rate_usd

    def remaining_budget_usd(self) -> float:
        """Budget remaining before ceiling."""
        return max(0.0, self.config.budget_ceiling_usd - self.estimated_spend_usd())

    def remaining_hours(self) -> float:
        """Hours remaining before budget or time cap."""
        remaining_secs = max(0.0, self.max_runtime_seconds - self.elapsed_seconds())
        return remaining_secs / 3600.0

    def percent_used(self) -> float:
        """Percentage of budget consumed."""
        ceiling = self.config.budget_ceiling_usd
        if ceiling <= 0:
            return 100.0
        return min(100.0, (self.estimated_spend_usd() / ceiling) * 100.0)

    def is_budget_exhausted(self) -> bool:
        """True if spending has reached the effective ceiling (ceiling - reserve)."""
        if self._stopped:
            return True
        effective_ceiling = (
            self.config.budget_ceiling_usd - self.config.reserve_margin_usd
        )
        return self.estimated_spend_usd() >= effective_ceiling

    def check(self) -> Dict[str, Any]:
        """
        Perform a budget check. Returns a status dict with recommended action.

        Returns:
            {
                "action": "CONTINUE" | "WARN" | "CRITICAL" | "STOP",
                "elapsed_hours": float,
                "estimated_spend_usd": float,
                "remaining_budget_usd": float,
                "remaining_hours": float,
                "percent_used": float,
                "reason": str,
            }
        """
        elapsed = self.elapsed_hours()
        spend = self.estimated_spend_usd()
        remaining = self.remaining_budget_usd()
        pct = self.percent_used()

        status = {
            "elapsed_hours": round(elapsed, 3),
            "estimated_spend_usd": round(spend, 4),
            "remaining_budget_usd": round(remaining, 4),
            "remaining_hours": round(self.remaining_hours(), 3),
            "percent_used": round(pct, 1),
        }

        if self.is_budget_exhausted():
            self._stopped = True
            status["action"] = "STOP"
            status["reason"] = (
                f"Budget ceiling reached: ${spend:.2f} / "
                f"${self.config.budget_ceiling_usd:.2f} "
                f"(reserve ${self.config.reserve_margin_usd:.2f} for checkpoint)"
            )
            logger.warning(f"🛑 BudgetGuard STOP: {status['reason']}")
        elif pct >= self.config.critical_at_percent:
            status["action"] = "CRITICAL"
            status["reason"] = f"Budget at {pct:.0f}% — approaching ceiling"
            logger.warning(f"🔴 BudgetGuard CRITICAL: {status['reason']}")
        elif pct >= self.config.warn_at_percent:
            status["action"] = "WARN"
            status["reason"] = f"Budget at {pct:.0f}%"
            logger.info(f"🟡 BudgetGuard WARN: {status['reason']}")
        else:
            status["action"] = "CONTINUE"
            status["reason"] = f"Budget healthy at {pct:.0f}%"

        return status

    def is_safe(self) -> bool:
        """Quick check: is it safe to start another iteration?"""
        return not self.is_budget_exhausted()

    def format_status_line(self) -> str:
        """One-line status for logging."""
        s = self.check()
        return (
            f"💰 [{s['action']}] "
            f"${s['estimated_spend_usd']:.2f}/${self.config.budget_ceiling_usd:.2f} "
            f"({s['percent_used']:.0f}%) | "
            f"{s['elapsed_hours']:.1f}h elapsed | "
            f"{s['remaining_hours']:.1f}h remaining"
        )

    def to_json(self) -> str:
        """Serialize current state for checkpoint metadata."""
        return json.dumps({
            "config": {
                "budget_ceiling_usd": self.config.budget_ceiling_usd,
                "hourly_rate_usd": self.config.hourly_rate_usd,
                "max_duration_hours": self.config.max_duration_hours,
            },
            "status": self.check(),
        }, indent=2)
