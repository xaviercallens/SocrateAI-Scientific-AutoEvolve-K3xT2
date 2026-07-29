"""
K3×T² Candidate Preselection for MCMC Evaluation
==================================================
Ranks evolutionary Pareto candidates by posterior probability and
physics plausibility, selecting only the highest-value candidates
for expensive MCMC inference. This avoids burning GPU-hours on
candidates unlikely to produce publication-quality posteriors.

Scoring Criteria (Bayesian Information Content):
    1. χ² fitness to DESI DR1 BAO                       (weight: 0.40)
    2. Physics consistency (w₀ ≈ -1, Ωₘ ≈ 0.30, H₀ ≈ 67.4)  (weight: 0.30)
    3. Novel signature strength (PTA, S₈)               (weight: 0.20)
    4. Picard number stability (P=19 preferred)          (weight: 0.10)

Input:
    GCS checkpoint JSON files from the evolutionary Deep Burn campaign
    (gs://socrateai-datalake-gen-lang-client-0625573011/checkpoints/)

Output:
    Ranked list of candidates with probability scores and MCMC cost estimates
"""

import json
import logging
import math
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ─── Target Physical Values ─────────────────────────────────────────────────
TARGETS = {
    "w0":       {"value": -1.000, "sigma": 0.020},   # ΛCDM dark energy EoS
    "omega_m":  {"value":  0.300, "sigma": 0.006},   # Planck 2018
    "h0":       {"value": 67.400, "sigma": 0.500},   # Planck 2018
    "pta_freq": {"value": 1.0e-9, "sigma": 1.0e-10}, # NanoGrav 15yr band
    "s8":       {"value":  0.830, "sigma": 0.013},   # KiDS-1000/DES-Y3 tension mid
}


@dataclass
class ScoredCandidate:
    """A K3×T² candidate scored for MCMC evaluation priority."""
    candidate_id: str
    generation: int
    raw_candidate: Dict[str, Any]

    # Sub-scores (0..1, higher = better)
    chi2_score: float = 0.0
    physics_score: float = 0.0
    signature_score: float = 0.0
    picard_score: float = 0.0

    # Composite
    composite_score: float = 0.0

    # MCMC cost estimate
    estimated_mcmc_hours: float = 0.0
    estimated_mcmc_cost_usd: float = 0.0

    @property
    def phenotype(self) -> Dict[str, Any]:
        return self.raw_candidate.get("phenotype", {})

    @property
    def likelihood(self) -> Dict[str, Any]:
        return self.raw_candidate.get("likelihood", {})


def _gaussian_score(observed: float, target: float, sigma: float) -> float:
    """Score how close an observed value is to a target (Gaussian kernel, 0..1)."""
    z = (observed - target) / sigma
    return math.exp(-0.5 * z * z)


def score_candidate(
    candidate: Dict[str, Any],
    generation: int,
    weights: Dict[str, float] = None,
) -> ScoredCandidate:
    """
    Score a single K3×T² candidate for MCMC evaluation priority.

    Args:
        candidate: Raw candidate dict from evolutionary checkpoint
        generation: Generation number this candidate came from
        weights: Optional custom scoring weights

    Returns:
        ScoredCandidate with computed scores
    """
    if weights is None:
        weights = {"chi2": 0.40, "physics": 0.30, "signatures": 0.20, "picard": 0.10}

    pheno = candidate.get("phenotype", {})
    lk = candidate.get("likelihood", {})
    cid = candidate.get("candidate_id", f"gen{generation}_unknown")

    sc = ScoredCandidate(
        candidate_id=cid,
        generation=generation,
        raw_candidate=candidate,
    )

    # 1. Chi² Fitness Score (lower χ² = better → sigmoid transform)
    chi2 = lk.get("chi2", candidate.get("chi2_loss", 1e6))
    # Map chi2 to [0,1]: score = 1/(1 + chi2/scale)
    sc.chi2_score = 1.0 / (1.0 + chi2 / 1e-4)

    # 2. Physics Consistency Score (proximity to ΛCDM targets)
    w0 = pheno.get("w0", 0.0)
    om = pheno.get("omega_m", 0.0)
    h0 = pheno.get("h0", 0.0)
    sc.physics_score = (
        _gaussian_score(w0, TARGETS["w0"]["value"], TARGETS["w0"]["sigma"]) *
        _gaussian_score(om, TARGETS["omega_m"]["value"], TARGETS["omega_m"]["sigma"]) *
        _gaussian_score(h0, TARGETS["h0"]["value"], TARGETS["h0"]["sigma"])
    ) ** (1.0 / 3.0)  # Geometric mean of the three

    # 3. Novel Signature Strength (PTA + S₈)
    pta = pheno.get("pta_f_monopole", 0.0)
    s8 = pheno.get("s8_gradient", 0.0)
    pta_score = _gaussian_score(pta, TARGETS["pta_freq"]["value"], TARGETS["pta_freq"]["sigma"])
    s8_score = _gaussian_score(s8, TARGETS["s8"]["value"], TARGETS["s8"]["sigma"])
    sc.signature_score = (pta_score * s8_score) ** 0.5  # Geometric mean

    # 4. Picard Number Stability (P=19 is the preferred topological invariant)
    picard = candidate.get("picard_number", 0)
    sc.picard_score = 1.0 if picard == 19 else max(0.0, 1.0 - abs(picard - 19) * 0.15)

    # Composite weighted score
    sc.composite_score = (
        weights["chi2"]       * sc.chi2_score +
        weights["physics"]    * sc.physics_score +
        weights["signatures"] * sc.signature_score +
        weights["picard"]     * sc.picard_score
    )

    # MCMC cost estimate based on expected difficulty
    # Lower composite → harder convergence → more steps needed
    base_hours = 2.0  # Base MCMC time for a well-behaved candidate
    difficulty_factor = 1.0 / max(sc.composite_score, 0.1)
    sc.estimated_mcmc_hours = min(base_hours * difficulty_factor, 12.0)
    sc.estimated_mcmc_cost_usd = sc.estimated_mcmc_hours * 0.24  # Spot L4 rate

    return sc


def load_candidates_from_gcs(
    bucket: str = "socrateai-datalake-gen-lang-client-0625573011",
    prefix: str = "checkpoints",
    last_n_generations: int = 10,
) -> List[Dict[str, Any]]:
    """
    Load the best candidates from the most recent GCS checkpoints.

    Returns list of (generation, candidate_dict) tuples.
    """
    candidates = []

    try:
        # List checkpoint files
        result = subprocess.run(
            ["gcloud", "storage", "ls", f"gs://{bucket}/{prefix}/"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            logger.error(f"GCS listing failed: {result.stderr}")
            return candidates

        files = [line.strip() for line in result.stdout.splitlines() if line.strip().endswith(".json")]
        files.sort()

        # Take last N generations
        target_files = files[-last_n_generations:] if len(files) > last_n_generations else files

        for gcs_path in target_files:
            try:
                cat_result = subprocess.run(
                    ["gcloud", "storage", "cat", gcs_path],
                    capture_output=True, text=True, timeout=15,
                )
                if cat_result.returncode == 0:
                    data = json.loads(cat_result.stdout)
                    # Extract generation number from filename
                    fname = gcs_path.split("/")[-1]
                    gen_num = int("".join(filter(str.isdigit, fname.split("gen_")[-1].split(".")[0]))) if "gen_" in fname else 0
                    candidates.append({"generation": gen_num, "data": data})
            except Exception as e:
                logger.warning(f"Failed to load {gcs_path}: {e}")

    except Exception as e:
        logger.error(f"GCS candidate loading failed: {e}")

    return candidates


def preselect_candidates(
    candidates: List[Dict[str, Any]],
    budget_usd: float = 25.00,
    hourly_rate_usd: float = 0.24,
    max_candidates: int = 3,
    overhead_hours: float = 1.0,
) -> List[ScoredCandidate]:
    """
    Preselect K3×T² candidates for MCMC evaluation within a budget ceiling.

    Strategy:
        1. Score all candidates
        2. Sort by composite_score descending
        3. Greedily select candidates whose cumulative MCMC cost fits budget
        4. Return selected candidates in priority order

    Args:
        candidates: Raw candidate dicts
        budget_usd: Hard budget ceiling for the entire campaign
        hourly_rate_usd: Spot VM hourly rate
        max_candidates: Maximum number of candidates to evaluate
        overhead_hours: Time reserved for container startup, checkpointing, etc.

    Returns:
        List of ScoredCandidate in evaluation priority order
    """
    # Score all candidates
    scored = []
    for entry in candidates:
        gen = entry.get("generation", 0)
        data = entry.get("data", entry)

        # Handle both single-candidate and population checkpoint formats
        if isinstance(data, dict) and "candidate_id" in data:
            scored.append(score_candidate(data, gen))
        elif isinstance(data, dict):
            # Try to find the best candidate in a population checkpoint
            for key in ["best_candidate", "global_best", "pareto_front"]:
                if key in data:
                    val = data[key]
                    if isinstance(val, list):
                        for c in val:
                            scored.append(score_candidate(c, gen))
                    elif isinstance(val, dict):
                        scored.append(score_candidate(val, gen))
                    break

    if not scored:
        logger.warning("No candidates found to score.")
        return []

    # Deduplicate by candidate_id (keep highest-scoring version)
    seen = {}
    for sc in scored:
        if sc.candidate_id not in seen or sc.composite_score > seen[sc.candidate_id].composite_score:
            seen[sc.candidate_id] = sc
    scored = list(seen.values())

    # Sort by composite score (best first)
    scored.sort(key=lambda s: s.composite_score, reverse=True)

    # Greedy knapsack: select candidates within budget
    available_budget = budget_usd - (overhead_hours * hourly_rate_usd)
    selected = []
    cumulative_cost = 0.0

    for sc in scored:
        if len(selected) >= max_candidates:
            break
        if cumulative_cost + sc.estimated_mcmc_cost_usd <= available_budget:
            cumulative_cost += sc.estimated_mcmc_cost_usd
            selected.append(sc)
        else:
            logger.info(
                f"Skipping {sc.candidate_id} (est. ${sc.estimated_mcmc_cost_usd:.2f}) — "
                f"would exceed budget (${cumulative_cost:.2f} + ${sc.estimated_mcmc_cost_usd:.2f} > ${available_budget:.2f})"
            )

    logger.info(
        f"Preselected {len(selected)}/{len(scored)} candidates | "
        f"Est. MCMC cost: ${cumulative_cost:.2f} / ${available_budget:.2f} budget"
    )

    return selected


def format_preselection_report(selected: List[ScoredCandidate], budget_usd: float = 25.00) -> str:
    """Format a human-readable preselection report."""
    lines = [
        "=" * 70,
        "  K3×T² Candidate Preselection Report",
        f"  Budget Ceiling: ${budget_usd:.2f}",
        "=" * 70,
    ]

    total_cost = 0.0
    for i, sc in enumerate(selected, 1):
        total_cost += sc.estimated_mcmc_cost_usd
        lines.extend([
            f"",
            f"  #{i}  {sc.candidate_id}  (Gen {sc.generation})",
            f"      Composite Score:  {sc.composite_score:.4f}",
            f"      ├── χ² fitness:   {sc.chi2_score:.4f} (40%)",
            f"      ├── Physics:      {sc.physics_score:.4f} (30%)",
            f"      ├── Signatures:   {sc.signature_score:.4f} (20%)",
            f"      └── Picard P={str(sc.raw_candidate.get('picard_number','?')):>2s}:  {sc.picard_score:.4f} (10%)",
            f"      Phenotype: w₀={sc.phenotype.get('w0',0):.4f}, Ωₘ={sc.phenotype.get('omega_m',0):.3f}, H₀={sc.phenotype.get('h0',0):.1f}",
            f"      Est. MCMC: {sc.estimated_mcmc_hours:.1f}h → ${sc.estimated_mcmc_cost_usd:.2f}",
        ])

    lines.extend([
        "",
        "─" * 70,
        f"  Total Estimated MCMC Cost:  ${total_cost:.2f} / ${budget_usd:.2f} ceiling",
        f"  Budget Margin:              ${budget_usd - total_cost:.2f} reserved",
        "=" * 70,
    ])

    return "\n".join(lines)


# ─── CLI Entry Point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    # Use the known best candidate from Deep Burn gen 75 as the primary
    best_candidate = {
        "candidate_id": "cooper_s10_g63_32",
        "picard_number": 19,
        "complex_structure": [0.22742914757560284, -1.435738265137309, 0.9453496565018775],
        "t2_modulus_tau": 0.4998315525628445,
        "phenotype": {
            "w0": -0.9999157762814223,
            "omega_m": 0.300,
            "h0": 67.4038974368775,
            "pta_f_monopole": 9.999831552562845e-10,
            "s8_gradient": 0.83,
        },
        "likelihood": {
            "chi2": 4.905883986492089e-06,
            "fitness": 0.9999950941400811,
        },
    }

    candidates = [{"generation": 75, "data": best_candidate}]

    # Try loading from GCS
    gcs_candidates = load_candidates_from_gcs(last_n_generations=5)
    if gcs_candidates:
        candidates.extend(gcs_candidates)

    selected = preselect_candidates(candidates, budget_usd=25.00)
    report = format_preselection_report(selected)
    print(report)
