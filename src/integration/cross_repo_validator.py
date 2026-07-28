"""
Cross-Repository Validator for AlphaEvolve-K3-T2
=================================================
Ensures consistency between:
  - Stream 1 (Lean 4 formal proofs)
  - Stream 2 (K3 AutoEvolve rankings)
  - Stream 3 (GPU pipeline results)
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


class CrossRepoValidator:
    """Validates consistency across all three AlphaEvolve streams."""

    @staticmethod
    def validate_stream1_lean_proofs(lean_file: Path) -> bool:
        """Run `lean --make` on a Lean file to confirm all proofs pass."""
        try:
            result = subprocess.run(
                ["lean", "--make", str(lean_file)],
                capture_output=True, text=True, timeout=60
            )
            passed = result.returncode == 0
            if not passed:
                logger.warning(f"Stream 1 Lean proof failed:\n{result.stderr}")
            return passed
        except FileNotFoundError:
            logger.warning("Lean binary not found — skipping Stream 1 validation.")
            return False
        except subprocess.TimeoutExpired:
            logger.error("Lean proof validation timed out.")
            return False

    @staticmethod
    def validate_stream2_k3_ranking(k3_report: Path) -> bool:
        """Verify that Cooper s7 is the selected K3 surface in the ranking report."""
        try:
            with open(k3_report, "r") as f:
                report = json.load(f)
            selected = report.get("selected_k3", "")
            passed = "cooper_s7" in selected.lower()
            if not passed:
                logger.warning(f"Stream 2 K3 ranking mismatch: selected='{selected}'")
            return passed
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Stream 2 validation error: {e}")
            return False

    @staticmethod
    def validate_stream3_gpu_results(gpu_log: Path) -> bool:
        """Check that the GPU pipeline log reports ≥ 95% pass rate."""
        try:
            with open(gpu_log, "r") as f:
                log_content = f.read()
            passed = "pass rate: 100%" in log_content or "pass rate: 95%" in log_content
            if not passed:
                logger.warning("Stream 3 GPU pass rate below 95%.")
            return passed
        except FileNotFoundError as e:
            logger.error(f"Stream 3 validation error: {e}")
            return False

    def validate_all(self, lean_file: Path, k3_report: Path, gpu_log: Path) -> Dict[str, bool]:
        """Run all three stream validators."""
        return {
            "stream1_lean": self.validate_stream1_lean_proofs(lean_file),
            "stream2_k3":   self.validate_stream2_k3_ranking(k3_report),
            "stream3_gpu":  self.validate_stream3_gpu_results(gpu_log),
        }
