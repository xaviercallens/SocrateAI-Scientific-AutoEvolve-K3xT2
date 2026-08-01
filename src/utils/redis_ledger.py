"""
Redis Ledger for Distributed State Sharing
==========================================
Enables cross-pod (GKE/Kubernetes) distributed state coordination for the
AlphaEvolve MCMC evolutionary pipeline. Provides robust fault tolerance,
checkpoint locking, and global discovery broadcasts.
"""

import os
import json
import logging
from typing import Any, Dict, Optional
import redis

logger = logging.getLogger(__name__)

class DistributedRedisLedger:
    def __init__(self, host: str = None, port: int = None, db: int = 0):
        self.host = host or os.environ.get("REDIS_HOST", "localhost")
        self.port = port or int(os.environ.get("REDIS_PORT", "6379"))
        self.db = db
        self.prefix = "autoevolve_k3xt2:"
        
        try:
            self.client = redis.Redis(host=self.host, port=self.port, db=self.db, decode_responses=True)
            self.client.ping()
            self._connected = True
            logger.info(f"Connected to Redis ledger at {self.host}:{self.port}")
        except redis.ConnectionError as e:
            self._connected = False
            logger.warning(f"Could not connect to Redis ledger: {e}. Falling back to single-node (in-memory mock).")
            self._mock_store = {}

    def is_connected(self) -> bool:
        return self._connected

    def _get_key(self, key: str) -> str:
        return f"{self.prefix}{key}"

    def set_best_candidate(self, generation: int, candidate_data: Dict[str, Any]):
        """Broadcasts the best candidate discovered across all GPU pods."""
        key = self._get_key("global_best")
        payload = {
            "generation": generation,
            "data": candidate_data
        }
        if self._connected:
            self.client.set(key, json.dumps(payload))
        else:
            self._mock_store[key] = json.dumps(payload)

    def get_best_candidate(self) -> Optional[Dict[str, Any]]:
        """Retrieves the globally best candidate discovered by the cluster."""
        key = self._get_key("global_best")
        if self._connected:
            val = self.client.get(key)
        else:
            val = self._mock_store.get(key)
            
        if val:
            return json.loads(val)
        return None

    def acquire_checkpoint_lock(self, generation: int, timeout_secs: int = 60) -> bool:
        """
        Attempts to acquire a distributed lock to write the JSON checkpoint for a generation.
        Prevents race conditions where multiple pods try to upload gen_0150.json to GCS.
        """
        lock_key = self._get_key(f"lock:checkpoint_gen_{generation}")
        if self._connected:
            # Set NX (Not Exists) flag so only the first pod gets the lock
            acquired = self.client.set(lock_key, "locked", nx=True, ex=timeout_secs)
            return bool(acquired)
        else:
            if lock_key not in self._mock_store:
                self._mock_store[lock_key] = "locked"
                return True
            return False

    def release_checkpoint_lock(self, generation: int):
        """Releases the checkpoint lock."""
        lock_key = self._get_key(f"lock:checkpoint_gen_{generation}")
        if self._connected:
            self.client.delete(lock_key)
        else:
            self._mock_store.pop(lock_key, None)

    def increment_global_generation(self) -> int:
        """Atomically increments the global evolutionary generation counter."""
        key = self._get_key("global_generation")
        if self._connected:
            return self.client.incr(key)
        else:
            current = int(self._mock_store.get(key, 0)) + 1
            self._mock_store[key] = str(current)
            return current

    def set_task_state(self, task_id: str, state_json: str, expire_secs: int = 86400):
        """Saves the state of an orchestration task, useful for idempotency and fault tolerance."""
        key = self._get_key(f"task_state:{task_id}")
        if self._connected:
            self.client.setex(key, expire_secs, state_json)
        else:
            self._mock_store[key] = state_json

    def get_task_state(self, task_id: str) -> Optional[str]:
        """Retrieves the cached state of an orchestration task."""
        key = self._get_key(f"task_state:{task_id}")
        if self._connected:
            return self.client.get(key)
        else:
            return self._mock_store.get(key)
