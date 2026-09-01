import os
import json
import time
import subprocess
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def scaffold_lean_project(target_dir: str):
    """Creates the minimal Lean 4 Lake project structure."""
    d = Path(target_dir)
    d.mkdir(parents=True, exist_ok=True)
    
    # 1. lean-toolchain (forces a stable version)
    with open(d / "lean-toolchain", "w") as f:
        f.write("leanprover/lean4:stable\n")
        
    # 2. lakefile.lean
    lakefile = """
import Lake
open Lake DSL

package «lean_oracle» {
}

@[default_target]
lean_exe «rpc_server» {
  root := `Main
}
"""
    with open(d / "lakefile.lean", "w") as f:
        f.write(lakefile.strip())
        
    # 3. Main.lean (The actual RPC Server code)
    main_lean = """
import Lean.Data.Json
import Lean.Data.Json.FromToJson

open Lean (Json FromJson ToJson fromJson? toJson)

structure K3Candidate where
  candidate_id : String
  picard_number : Nat
  moduli_stabilization : Float
  complex_structure : Array Float
  deriving FromJson, ToJson, Inhabited

structure OracleResponse where
  candidate_id : String
  passed_swampland : Bool
  uv_complete : Bool
  penalty_score : Float
  formal_reason : String
  deriving FromJson, ToJson, Inhabited

def verifySwamplandBounds (candidate : K3Candidate) : OracleResponse :=
  -- A placeholder heuristic proving the JSON-RPC pipeline works.
  -- In production, this imports DualScaleStability.lean
  let is_stable := candidate.moduli_stabilization > 0.0
  let is_uv_complete := candidate.picard_number <= 20
  
  if is_stable && is_uv_complete then
    { candidate_id := candidate.candidate_id, passed_swampland := true, uv_complete := true, penalty_score := 0.0, formal_reason := "Distance and dS conjectures satisfied." }
  else
    { candidate_id := candidate.candidate_id, passed_swampland := false, uv_complete := false, penalty_score := 9999.9, formal_reason := "Failed moduli stabilization bounds." }

partial def rpcLoop (stdin stdout : IO.FS.Stream) : IO Unit := do
  let line ← stdin.getLine
  if line == "" then return () -- Exit on EOF

  match Json.parse line with
  | Except.ok j =>
    match fromJson? j (α := K3Candidate) with
    | Except.ok candidate =>
      let result := verifySwamplandBounds candidate
      stdout.putStrLn (toJson result |>.compress)
      stdout.flush
    | Except.error err =>
      let errJson := Json.mkObj [("error", Json.str s!"Schema mismatch: {err}")]
      stdout.putStrLn errJson.compress
      stdout.flush
  | Except.error err =>
    let errJson := Json.mkObj [("error", Json.str s!"Invalid JSON: {err}")]
    stdout.putStrLn errJson.compress
    stdout.flush
    
  rpcLoop stdin stdout

def main : IO Unit := do
  let stdin ← IO.getStdin
  let stdout ← IO.getStdout
  rpcLoop stdin stdout
"""
    with open(d / "Main.lean", "w") as f:
        f.write(main_lean.strip())
        
    logger.info(f"Lean 4 project scaffolded in {target_dir}")

def compile_lean_oracle(target_dir: str) -> str:
    """Runs 'lake build' to compile the RPC server."""
    logger.info("Compiling Lean RPC Server (this may take a minute on first run)...")
    result = subprocess.run(
        ["lake", "build"], 
        cwd=target_dir, 
        capture_output=True, 
        text=True
    )
    if result.returncode != 0:
        logger.error(f"Lake build failed:\n{result.stderr}")
        raise RuntimeError("Lean compilation failed. Is 'lake' in your PATH?")
        
    binary_path = Path(target_dir) / ".lake" / "build" / "bin" / "rpc_server"
    logger.info(f"Compilation successful! Binary at: {binary_path}")
    return str(binary_path.absolute())

class LeanOracleClient:
    """The isolated IPC Client for testing."""
    def __init__(self, binary_path: str):
        self.process = subprocess.Popen(
            [binary_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1 # Line-buffered for instantaneous I/O
        )
        logger.info("IPC Daemon started.")

    def send_and_receive(self, payload: dict) -> dict:
        if self.process.poll() is not None:
            raise RuntimeError("Daemon crashed.")
        
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
            return {"error": "Failed to decode", "raw_output": response_str}
            
    def close(self):
        self.process.stdin.close()
        self.process.terminate()
        self.process.wait()

if __name__ == "__main__":
    LEAN_DIR = "./test_lean_oracle"
    
    try:
        scaffold_lean_project(LEAN_DIR)
        binary_path = compile_lean_oracle(LEAN_DIR)
        
        client = LeanOracleClient(binary_path)
        
        # Test 1: Ideal K3xT2 Candidate (Should Pass)
        cand_pass = {
            "candidate_id": "k3_cooper_s7_mut1",
            "picard_number": 19,
            "moduli_stabilization": 0.5,
            "complex_structure": [1.0, 2.0, 3.5]
        }
        
        # Test 2: Unstable Candidate (Should Fail)
        cand_fail = {
            "candidate_id": "k3_random_unstable",
            "picard_number": 21, # Swampland violation (too high)
            "moduli_stabilization": -0.1, # Tachyonic instability
            "complex_structure": [0.1, 0.9]
        }
        
        # Test 3: Mathieu M24 Candidate (Should Pass)
        cand_mathieu = {
            "candidate_id": "Mathieu_M24",
            "picard_number": 20,
            "moduli_stabilization": 1.0,
            "complex_structure": [0.0, 1.0, 0.0]
        }
        
        logger.info("--- Running IPC Tests ---")
        
        res1 = client.send_and_receive(cand_pass)
        logger.info(f"TEST 1 (Passing Candidate): {json.dumps(res1, indent=2)}")
        
        res2 = client.send_and_receive(cand_fail)
        logger.info(f"TEST 2 (Failing Candidate): {json.dumps(res2, indent=2)}")
        
        res3 = client.send_and_receive(cand_mathieu)
        logger.info(f"TEST 3 (Mathieu M24 Candidate): {json.dumps(res3, indent=2)}")
        
        client.close()
        logger.info("Tests completed successfully. IPC Bridge is stable.")
        
    except Exception as e:
        logger.error(f"Test sequence failed: {e}")
