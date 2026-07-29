"""
MLOps Persistent Checkpointing — GCS-Backed for Vertex AI (Stream 5)
======================================================================
Saves evolutionary population state directly to GCS so Vertex AI ephemeral
TPU VMs can resume from any generation after node preemption or restart.

Falls back to local disk automatically when gcsfs is not installed
(e.g. local Hermes node development runs).
"""

import json
import logging
import os
from datetime import datetime

try:
    import gcsfs
except ImportError:
    gcsfs = None

logger = logging.getLogger(__name__)

GCS_BUCKET_DEFAULT = "socrateai-datalake-gen-lang-client-0625573011/checkpoints"


class EvolutionCheckpoint:
    def __init__(
        self,
        gcs_bucket: str = GCS_BUCKET_DEFAULT,
        local_fallback_dir: str = "./outputs/checkpoints",
    ):
        self.use_gcs = gcsfs is not None
        if self.use_gcs:
            self.gcs_dir = f"gs://{gcs_bucket}"
            try:
                self.fs = gcsfs.GCSFileSystem()
                logger.info(f"☁️  GCS checkpointing enabled → {self.gcs_dir}")
            except Exception as e:
                logger.warning(f"GCS auth failed ({e}), falling back to local disk.")
                self.use_gcs = False

        if not self.use_gcs:
            self.local_dir = local_fallback_dir
            os.makedirs(self.local_dir, exist_ok=True)
            logger.info(f"💾 Local checkpointing enabled → {self.local_dir}")

        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ------------------------------------------------------------------ #
    # Save                                                                  #
    # ------------------------------------------------------------------ #

    def save_generation(self, generation: int, population: list, best_candidate: dict):
        """Persist current generation state to GCS or local disk."""
        state = {
            "run_id":         self.run_id,
            "generation":     generation,
            "best_candidate": best_candidate,
            "population":     population,
        }
        filename = f"run_{self.run_id}_gen_{generation:04d}.json"

        if self.use_gcs:
            path = f"{self.gcs_dir}/{filename}"
            try:
                with self.fs.open(path, "w") as f:
                    json.dump(state, f, indent=2)
                logger.info(f"☁️  Cloud Checkpoint saved: {path}")
                return
            except Exception as e:
                logger.error(f"GCS write failed ({e}), attempting local fallback.")

        # Local fallback
        local_path = os.path.join(self.local_dir, filename)
        with open(local_path, "w") as f:
            json.dump(state, f, indent=2)
        logger.info(f"Checkpoint saved: {local_path}")

    # ------------------------------------------------------------------ #
    # Load                                                                  #
    # ------------------------------------------------------------------ #

    def load_latest_checkpoint(self) -> dict | None:
        """Find and load the most recent checkpoint to resume evolution."""
        try:
            if self.use_gcs:
                files = self.fs.ls(self.gcs_dir)
                checkpoints = sorted(f for f in files if f.endswith(".json"))
                if not checkpoints:
                    return None
                latest = checkpoints[-1]
                gcs_path = f"gs://{latest}"
                with self.fs.open(gcs_path, "r") as f:
                    logger.info(f"☁️  Resuming from Cloud Checkpoint: {gcs_path}")
                    data = json.load(f)
            else:
                if not os.path.exists(self.local_dir):
                    return None
                checkpoints = [
                    fn for fn in os.listdir(self.local_dir) if fn.endswith(".json")
                ]
                if not checkpoints:
                    return None
                latest = max(
                    checkpoints,
                    key=lambda fn: os.path.getmtime(os.path.join(self.local_dir, fn)),
                )
                with open(os.path.join(self.local_dir, latest), "r") as f:
                    logger.info(f"Resuming from local Checkpoint: {latest}")
                    data = json.load(f)

            # Restore run_id so new checkpoints continue the same run series
            self.run_id = data.get("run_id", self.run_id)
            return data

        except Exception as e:
            logger.warning(f"No checkpoint found (first run?): {e}")
            return None
