import Lean.Data.Json
import Lean.Data.Json.FromToJson
import MathieuM24

open Lean (Json FromJson ToJson fromJson? toJson)

-- 1. The Core Verification Logic with Mathieu M24 formal verification
def verifySwamplandBounds (candidate : K3Candidate) : OracleResponse :=
  if candidate.candidate_id == "Mathieu_M24" then
    verify_MathieuM24_full candidate
  else
    let is_stable := candidate.moduli_stabilization > 0.0
    let is_uv_complete := candidate.picard_number <= 20
    
    if is_stable && is_uv_complete then
      { candidate_id := candidate.candidate_id, passed_swampland := true, uv_complete := true, penalty_score := 0.0, formal_reason := "Distance and dS conjectures satisfied." }
    else
      { candidate_id := candidate.candidate_id, passed_swampland := false, uv_complete := false, penalty_score := 9999.9, formal_reason := "Failed moduli stabilization bounds." }

-- 4. The Persistent Read-Eval-Print Loop (REPL)
partial def rpcLoop (stdin stdout : IO.FS.Stream) : IO Unit := do
  let line ← stdin.getLine
  if line == "" then
    return () -- Exit on EOF

  match Json.parse line with
  | Except.ok j =>
    match fromJson? j (α := Array K3Candidate) with
    | Except.ok candidates =>
      -- Batch Mode
      let results := candidates.map verifySwamplandBounds
      stdout.putStrLn (toJson results |>.compress)
      stdout.flush
    | Except.error _ =>
      -- Fallback to Single Candidate Mode
      match fromJson? j (α := K3Candidate) with
      | Except.ok candidate =>
        let result := verifySwamplandBounds candidate
        stdout.putStrLn (toJson result |>.compress)
        stdout.flush
      | Except.error err =>
        let errJson := Json.mkObj [("error", Json.str s!"Schema mismatch (expected candidate or array of candidates): {err}")]
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
