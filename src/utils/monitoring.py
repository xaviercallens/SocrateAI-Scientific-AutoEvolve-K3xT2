"""
Centralized Monitoring & Logging for AlphaEvolve-K3-T2 (MON-01)
================================================================
"""

import json
import logging
import socket
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import psutil


class MonitoringLogger:
    """Provides centralized structured logging and metrics collection."""

    def __init__(
        self,
        name: str = "AlphaEvolve-K3-T2",
        log_file: Optional[Path] = None,
        metrics_file: Optional[Path] = None,
    ):
        self.name = name
        self.metrics_file = metrics_file
        self.metrics: Dict[str, Any] = {
            "start_time":     datetime.now().isoformat(),
            "host":           socket.gethostname(),
            "pid":            psutil.Process().pid,
            "cpu_count":      psutil.cpu_count(),
            "memory_total_mb": psutil.virtual_memory().total / (1024 ** 2),
        }

        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(fmt)
        self.logger.addHandler(ch)

        if log_file is not None:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(log_file)
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(fmt)
            self.logger.addHandler(fh)

    def log(self, message: str, level: str = "info", **kwargs) -> None:
        getattr(self.logger, level, self.logger.info)(message)
        if kwargs:
            self.metrics.update(kwargs)

    def log_metric(self, name: str, value: Any) -> None:
        self.metrics[name] = value
        self.logger.info(f"Metric: {name} = {value}")

    def log_timing(self, name: str, start_time: float) -> None:
        elapsed = time.time() - start_time
        self.log_metric(f"{name}_elapsed_s", round(elapsed, 4))

    def save_metrics(self) -> None:
        if self.metrics_file is not None:
            self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.metrics_file, "w") as f:
                json.dump(self.metrics, f, indent=2)
            self.logger.info(f"Metrics saved to {self.metrics_file}")

    def get_metrics(self) -> Dict[str, Any]:
        return dict(self.metrics)


# Singleton for convenience import
monitor = MonitoringLogger(
    log_file=Path("logs/alpha_evolve.log"),
    metrics_file=Path("logs/metrics.json"),
)
