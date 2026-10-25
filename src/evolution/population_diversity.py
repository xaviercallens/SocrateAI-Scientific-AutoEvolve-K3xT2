"""Population fitness-diversity monitor for selection loops.

Why this exists. For one locus, two alleles and haploid selection, one round of
selection raises mean fitness by exactly Var(w) / mean(w) -- proved in Lean 4
(theorem ``kal_increment_is_variance`` and ``aurelia_mean_fitness_nondecreasing``,
formal/ANSE/AlixPopulationGenetics.lean in xaviercallens/AutoevolveAI). Progress
under selection is proportional to the fitness variance present, and stops when
it is gone.

That prediction was tested on Kernel-Gated Evolution (Paper J edition 5,
DOI 10.5281/zenodo.23640856): once a population's fitness variance collapsed, the
per-generation chance of solving fell at both rungs with enough data
(L3 p = 0.015, L5 p = 0.0019). Injecting random immigrants did NOT help, because
random individuals are culled before they add variance among the survivors.

This module only MEASURES. It changes nothing about selection, so adding it to a
loop cannot alter that loop's results. ``collapsed`` uses the same pre-registered
criterion as the KGE study: at most two distinct fitness values among the
individuals kept for the next generation.
"""

from __future__ import annotations

import math
from typing import Any, Iterable


def population_diversity(
    population: Iterable[dict[str, Any]],
    key: str = "chi2_loss",
    decimals: int = 9,
) -> dict[str, Any]:
    """Diversity of ``key`` across ``population``.

    Values are rounded to ``decimals`` before counting distinct ones, so float
    noise below that resolution does not masquerade as diversity. Individuals
    without ``key`` or with a non-finite value are skipped and counted.
    """
    values: list[float] = []
    skipped = 0
    for ind in population:
        v = ind.get(key)
        if isinstance(v, (int, float)) and math.isfinite(v):
            values.append(float(v))
        else:
            skipped += 1
    n = len(values)
    if n == 0:
        return {"n": 0, "skipped": skipped, "distinct": 0, "mean": None,
                "variance": None, "collapsed": True}
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    distinct = len({round(v, decimals) for v in values})
    return {
        "n": n,
        "skipped": skipped,
        "distinct": distinct,
        "mean": mean,
        "variance": variance,
        "collapsed": distinct <= 2,
    }
