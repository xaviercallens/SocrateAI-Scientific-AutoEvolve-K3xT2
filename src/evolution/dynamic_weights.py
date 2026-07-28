"""
Dynamic Fitness Weight Adapter for AlphaEvolve-K3-T2
=====================================================
Adapts the 60/30/10 theoretical/empirical/consistency fitness weights
based on per-criterion pass rates observed during evolution.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DynamicWeights:
    """Adapts fitness weights based on observed validation pass rates."""

    DEFAULT_WEIGHTS = {
        "theoretical":   0.60,
        "empirical":     0.30,
        "consistency":   0.10,
    }

    def __init__(self, initial_weights: Optional[Dict[str, float]] = None):
        self.weights: Dict[str, float] = dict(initial_weights or self.DEFAULT_WEIGHTS)
        self.history: List[Dict[str, float]] = [dict(self.weights)]
        self._normalize()

    def _normalize(self) -> None:
        total = sum(self.weights.values())
        if total == 0:
            raise ValueError("Weights sum to zero — cannot normalize.")
        self.weights = {k: v / total for k, v in self.weights.items()}

    def update_weights(self, pass_rates: Dict[str, float]) -> None:
        """
        Update weights based on per-criterion pass rates.
        Criteria that fail frequently get higher weight (more selective pressure).

        Args:
            pass_rates: Dict mapping criterion name to float in [0, 1].
        """
        for criterion, rate in pass_rates.items():
            if criterion in self.weights:
                if rate < 0.5:       # Frequently failing → increase weight
                    self.weights[criterion] = min(self.weights[criterion] + 0.05, 0.90)
                elif rate > 0.9:     # Easily passing → gently reduce weight
                    self.weights[criterion] = max(self.weights[criterion] - 0.02, 0.01)
        self._normalize()
        self.history.append(dict(self.weights))
        logger.info(f"Dynamic weights updated: {self.weights}")

    def get_weights(self) -> Dict[str, float]:
        return dict(self.weights)

    def save_history(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.history, f, indent=2)
        logger.info(f"Weight history saved to {path}")
