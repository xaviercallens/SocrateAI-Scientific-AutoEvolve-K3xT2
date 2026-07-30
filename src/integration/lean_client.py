import subprocess
import json
import logging
from typing import Dict, Any, List
import time
import os

logger = logging.getLogger(__name__)

class LeanOracleClient:
    def __init__(self, binary_path: str = "./test_lean_oracle/.lake/build/bin/rpc_server"):
        """Initializes the persistent Lean 4 subprocess."""
        if not os.path.exists(binary_path):
            alt_path = "./lean_oracle/.lake/build/bin/rpc_server"
            if os.path.exists(alt_path):
                binary_path = alt_path

        self.binary_path = binary_path
        self.process = subprocess.Popen(
            [binary_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1 
        )
        logger.info(f"Lean 4 Symbolic Oracle daemon initialized from {binary_path}.")

    def send_and_receive(self, payload: dict) -> dict:
        """Sends a K3xT2 geometry to Lean and awaits the proof state."""
        if self.process.poll() is not None:
            raise RuntimeError("Lean 4 subprocess crashed.")

        t0 = time.perf_counter()
        # Serialize and send
        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()

        # Await the formal verdict
        response_str = self.process.stdout.readline().strip()
        t1 = time.perf_counter()
        
        try:
            resp = json.loads(response_str)
            resp["_ipc_latency_ms"] = round((t1 - t0) * 1000, 3)
            return resp
        except json.JSONDecodeError:
            logger.error(f"Failed to decode Lean output: {response_str}")
            return {"passed_swampland": False, "formal_reason": "RPC Decode Error", "penalty_score": 9999.9}

    def evaluate_candidate(self, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """Alias for send_and_receive for backwards compatibility."""
        return self.send_and_receive(candidate_data)

    def batch_evaluate(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluates all Tier 1 survivors in a high-speed batch."""
        return [self.send_and_receive(cand) for cand in candidates]

    def close(self):
        """Safely terminates the Oracle daemon."""
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.close()
                self.process.terminate()
                self.process.wait()
            except Exception as e:
                logger.warning(f"Error closing Lean process: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

def _simulated_lean_verify(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback simulation of Lean 4 swampland verification."""
    picard = candidate.get("picard_number", 19)
    stabilization = candidate.get("moduli_stabilization", 0.5)
    if picard <= 20 and stabilization > 0:
        return {
            "passed_swampland": True,
            "uv_complete": True,
            "penalty_score": 0.0,
            "formal_reason": "Distance and dS conjectures satisfied",
        }
    else:
        return {
            "passed_swampland": False,
            "uv_complete": False,
            "penalty_score": 9999.9,
            "formal_reason": "Swampland constraint violated",
        }

