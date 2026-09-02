"""
Tier 2 Lean 4 Gatekeeper for AlphaEvolve K3xT2 Search.
Bridges Tier 1 survivors with Lean 4 RPC Oracle daemon to verify formal Swampland UV-completeness.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from src.integration.lean_client import LeanOracleClient

log = logging.getLogger(__name__)


def tier2_lean_gatekeeper(
    tier1_survivors: List[Any],
    oracle: Optional[LeanOracleClient] = None,
) -> Tuple[List[Any], Dict[str, Any]]:
    """
    Acts as the Tier 2 absolute filter.
    Only geometries mathematically proven by Lean 4 advance to Tier 3 TPU.
    Returns (proven_survivors, stats).
    """
    log.info(f"Dispatching {len(tier1_survivors)} K3xT2 candidates to Lean 4 Oracle...")

    should_close_oracle = False
    if oracle is None:
        oracle = LeanOracleClient()
        should_close_oracle = True

    try:
        formatted_payloads = []
        for idx, cand in enumerate(tier1_survivors):
            if isinstance(cand, dict):
                cand_id = str(cand.get("candidate_id", idx))
                picard = int(cand.get("picard_number", 20))
                stabilization = float(cand.get("moduli_stabilization", cand.get("r_moduli", 0.5)))
                c_struct = cand.get("complex_structure", cand.get("weights", [1, 1, 1, 1, 2, 2]))
            elif isinstance(cand, (list, tuple)):
                cand_id = str(idx)
                picard = 20
                stabilization = 0.5
                c_struct = list(cand)
            else:
                # Handle candidate object with attributes
                cand_id = getattr(cand, "candidate_id", str(idx))
                picard = getattr(cand, "picard_number", 20)
                stabilization = getattr(cand, "moduli_stabilization", 0.5)
                c_struct = getattr(cand, "weights", [])

            formatted_payloads.append({
                "candidate_id": cand_id,
                "picard_number": picard,
                "moduli_stabilization": stabilization,
                "complex_structure": [float(x) for x in c_struct],
            })

        verdicts = oracle.batch_evaluate(formatted_payloads)
        if not isinstance(verdicts, list):
            if isinstance(verdicts, dict) and "error" in verdicts:
                log.error(f"Lean 4 batch evaluate returned error: {verdicts['error']}")
            verdicts = [verdicts if isinstance(verdicts, dict) else {"passed_swampland": False, "formal_reason": str(verdicts)}] * len(tier1_survivors)

        proven_survivors = []
        failed_count = 0
        failure_reasons = {}

        for candidate, verdict in zip(tier1_survivors, verdicts):
            if isinstance(verdict, dict):
                passed = verdict.get("passed_swampland", False)
                reason = verdict.get("formal_reason", "Unknown")
            else:
                passed = False
                reason = str(verdict)

            if passed:
                if isinstance(candidate, dict):
                    candidate["formal_reason"] = reason
                    candidate["passed_swampland"] = True
                elif hasattr(candidate, "metadata") and isinstance(candidate.metadata, dict):
                    candidate.metadata["formal_reason"] = reason
                    candidate.metadata["passed_swampland"] = True
                proven_survivors.append(candidate)
            else:
                failed_count += 1
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
                if isinstance(candidate, dict):
                    candidate["passed_swampland"] = False
                    candidate["chi2"] = verdict.get("penalty_score", 9999.9)

        stats = {
            "input_count": len(tier1_survivors),
            "passed_count": len(proven_survivors),
            "failed_count": failed_count,
            "pass_rate_pct": (len(proven_survivors) / len(tier1_survivors) * 100.0) if tier1_survivors else 0.0,
            "failure_breakdown": failure_reasons,
        }

        log.info(f"Tier 2 Gatekeeper complete. {len(proven_survivors)}/{len(tier1_survivors)} passed Swampland bounds.")
        return proven_survivors, stats

    finally:
        if should_close_oracle and oracle:
            oracle.close()
