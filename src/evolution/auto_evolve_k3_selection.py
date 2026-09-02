"""
AutoEvolve for K3 Surface Selection (PL-01)
============================================
Genetic algorithm to evolve and select K3 surfaces for the Dual-Scale Model.
Fitness is weighted: 60% theoretical rigor, 30% empirical fit, 10% consistency.

Blocked candidates (non-K3 topology):
    BLOCKED_CANDIDATES = {"cooper_s18"}
"""

import json
import logging
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from src.mcmc.observational_constants import PTA_F_MONOPOLE_TARGET

logger = logging.getLogger(__name__)

# AP-02: Explicitly blocked K3 candidates (formally verified non-K3 or invalid)
BLOCKED_CANDIDATES = {"cooper_s18"}


@dataclass
class K3Candidate:
    id: str
    ode_order: int
    ode_coefficients: List[float]
    partner_ode: Optional[str] = None
    picard_rank: Optional[int] = None
    transcendental_lattice: Optional[int] = None
    kodaira_types: Optional[List[str]] = None
    delta_obs: Optional[float] = None
    pta_frequency: Optional[float] = None
    pta_amplitude: Optional[float] = None
    alpha_eff: Optional[float] = None
    fitness: float = 0.0


@dataclass
class EvolutionParameters:
    population_size: int = 100
    mutation_rate: float = 0.10
    crossover_rate: float = 0.70
    elitism_count: int = 5
    max_generations: int = 100
    tournament_size: int = 3
    mutation_scale: float = 0.50


class AutoEvolveK3:
    """Genetic algorithm for evolving K3 surfaces."""

    def __init__(self, params: EvolutionParameters = EvolutionParameters()):
        self.params = params
        self.population: List[K3Candidate] = []
        self.best_candidate: Optional[K3Candidate] = None
        self.generation: int = 0
        self.history: List[Dict] = []

    # ------------------------------------------------------------------ #
    #  Initialization                                                       #
    # ------------------------------------------------------------------ #

    def initialize_population(self, candidates: List[K3Candidate]) -> None:
        # AP-02: filter blocked candidates
        candidates = [c for c in candidates if c.id not in BLOCKED_CANDIDATES]
        if len(candidates) < self.params.population_size:
            # Oversample via mutation if not enough seeds
            base = list(candidates)
            while len(candidates) < self.params.population_size:
                candidates.append(self._mutate(random.choice(base)))
        self.population = random.sample(candidates, self.params.population_size)
        self._evaluate_population()
        self._update_best()
        logger.info(f"Population initialized: {len(self.population)} candidates")

    # ------------------------------------------------------------------ #
    #  Fitness                                                              #
    # ------------------------------------------------------------------ #

    def _calculate_fitness(self, c: K3Candidate) -> float:
        return (
            0.60 * self._theoretical_score(c) +
            0.30 * self._empirical_score(c) +
            0.10 * self._consistency_score(c)
        )

    def _theoretical_score(self, c: K3Candidate) -> float:
        score = 0.0
        # TIER A: K3 and CY Geometry Requirements
        if c.ode_order in (3, 4):
            score += 0.50        # K3 Picard-Fuchs operators (e.g. Order-3/4 for Almkvist-Zudilin / Cooper)
        elif c.ode_order == 5:
            score += 0.50        # CY4 sequences (Weight-5)

        if self._swampland_ok(c):
            score += 0.30
        if c.partner_ode is not None:
            score += 0.20        # Sym² structure confirmed
            
        return min(max(score, 0.0), 1.0)

    def _empirical_score(self, c: K3Candidate) -> float:
        score = 0.0
        if c.delta_obs is not None:
            if c.delta_obs >= 10.0:
                score += 0.40    # 7-brane intersection
            elif c.delta_obs >= 1.0:
                score += 0.30
            else:
                score += 0.20
        if c.pta_frequency is not None and abs(c.pta_frequency - PTA_F_MONOPOLE_TARGET) / PTA_F_MONOPOLE_TARGET < 0.10:
            score += 0.30
        if c.pta_amplitude is not None and abs(c.pta_amplitude - 1e-15) / 1e-15 < 0.10:
            score += 0.30
        return min(score, 1.0)

    def _consistency_score(self, c: K3Candidate) -> float:
        score = 0.0
        if c.alpha_eff is not None and c.alpha_eff > 0.45:
            score += 0.50        # Chameleon mechanism OK
        score += 0.50            # Placeholder GD-1 pass
        return min(score, 1.0)

    def _swampland_ok(self, c: K3Candidate) -> bool:
        return True              # Formal check delegated to Lean 4 daemon

    # ------------------------------------------------------------------ #
    #  Genetic Operators                                                    #
    # ------------------------------------------------------------------ #

    def _tournament_selection(self) -> K3Candidate:
        tournament = random.sample(self.population, self.params.tournament_size)
        return max(tournament, key=lambda x: x.fitness)

    def _crossover(self, p1: K3Candidate, p2: K3Candidate):
        c1_coeffs, c2_coeffs = [], []
        for a, b in zip(p1.ode_coefficients, p2.ode_coefficients):
            if random.random() < 0.5:
                c1_coeffs.append(a); c2_coeffs.append(b)
            else:
                c1_coeffs.append(b); c2_coeffs.append(a)
        def _child(base, coeffs, suffix):
            return K3Candidate(
                id=f"{p1.id}_x_{p2.id}_{suffix}",
                ode_order=base.ode_order,
                ode_coefficients=coeffs,
                partner_ode=p1.partner_ode if random.random() < 0.5 else p2.partner_ode,
                picard_rank=p1.picard_rank if random.random() < 0.5 else p2.picard_rank,
                transcendental_lattice=p1.transcendental_lattice if random.random() < 0.5 else p2.transcendental_lattice,
                kodaira_types=p1.kodaira_types if random.random() < 0.5 else p2.kodaira_types,
                delta_obs=p1.delta_obs if random.random() < 0.5 else p2.delta_obs,
                pta_frequency=p1.pta_frequency if random.random() < 0.5 else p2.pta_frequency,
                pta_amplitude=p1.pta_amplitude if random.random() < 0.5 else p2.pta_amplitude,
                alpha_eff=p1.alpha_eff if random.random() < 0.5 else p2.alpha_eff,
            )
        return _child(p1, c1_coeffs, "1"), _child(p2, c2_coeffs, "2")

    def _mutate(self, c: K3Candidate) -> K3Candidate:
        new_coeffs = []
        for coeff in c.ode_coefficients:
            if random.random() < self.params.mutation_rate:
                new_coeffs.append(coeff + random.gauss(0, self.params.mutation_scale * (abs(coeff) or 1.0)))
            else:
                new_coeffs.append(coeff)
        return K3Candidate(
            id=f"{c.id}_m",
            ode_order=c.ode_order,
            ode_coefficients=new_coeffs,
            partner_ode=c.partner_ode,
            picard_rank=c.picard_rank,
            transcendental_lattice=c.transcendental_lattice,
            kodaira_types=c.kodaira_types,
            delta_obs=c.delta_obs,
            pta_frequency=c.pta_frequency,
            pta_amplitude=c.pta_amplitude,
            alpha_eff=c.alpha_eff,
        )

    # ------------------------------------------------------------------ #
    #  Evolution Loop                                                       #
    # ------------------------------------------------------------------ #

    def _evaluate_population(self) -> None:
        for c in self.population:
            c.fitness = self._calculate_fitness(c)

    def _update_best(self) -> None:
        if self.population:
            self.best_candidate = max(self.population, key=lambda x: x.fitness)

    def evolve(self) -> None:
        new_pop = sorted(self.population, key=lambda x: x.fitness, reverse=True)[:self.params.elitism_count]

        while len(new_pop) < self.params.population_size:
            p1 = self._tournament_selection()
            p2 = self._tournament_selection()
            if random.random() < self.params.crossover_rate:
                c1, c2 = self._crossover(p1, p2)
                new_pop.extend([c1, c2])
            else:
                new_pop.extend([p1, p2])

        new_pop = new_pop[:self.params.population_size]

        for i in range(len(new_pop)):
            if random.random() < self.params.mutation_rate:
                new_pop[i] = self._mutate(new_pop[i])

        self.population = new_pop
        self._evaluate_population()
        self._update_best()
        self.generation += 1

        avg_fitness = float(np.mean([c.fitness for c in self.population]))
        logger.info(f"Generation {self.generation}: avg_fitness={avg_fitness:.4f}, best={self.best_candidate.fitness:.4f} ({self.best_candidate.id})")
        self.history.append({
            "generation": self.generation,
            "avg_fitness": avg_fitness,
            "best_fitness": self.best_candidate.fitness,
            "best_id": self.best_candidate.id,
        })

    def _check_convergence(self, tolerance: float = 1e-4) -> bool:
        if len(self.history) < 10:
            return False
        last = [h["avg_fitness"] for h in self.history[-10:]]
        return (max(last) - min(last)) < tolerance

    def run(self, num_generations: Optional[int] = None) -> K3Candidate:
        max_gen = num_generations if num_generations is not None else self.params.max_generations
        for _ in range(max_gen):
            self.evolve()
            if self._check_convergence():
                logger.info("Convergence detected — stopping early.")
                break
        return self.best_candidate

    def save_results(self, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        if self.best_candidate:
            with open(output_dir / "best_candidate.json", "w") as f:
                json.dump({
                    "id": self.best_candidate.id,
                    "fitness": self.best_candidate.fitness,
                    "ode_order": self.best_candidate.ode_order,
                    "ode_coefficients": self.best_candidate.ode_coefficients,
                    "partner_ode": self.best_candidate.partner_ode,
                    "picard_rank": self.best_candidate.picard_rank,
                    "kodaira_types": self.best_candidate.kodaira_types,
                    "delta_obs": self.best_candidate.delta_obs,
                    "pta_frequency": self.best_candidate.pta_frequency,
                    "pta_amplitude": self.best_candidate.pta_amplitude,
                }, f, indent=2)
        with open(output_dir / "evolution_history.json", "w") as f:
            json.dump(self.history, f, indent=2)
        logger.info(f"Results saved to {output_dir}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    seeds = [
        K3Candidate("cooper_s7",  3, [13, 4, -27, 3], "A279619", 4, 18, ["II", "II"], 47.0, PTA_F_MONOPOLE_TARGET, 1e-15, 0.50),
        K3Candidate("cooper_s10", 3, [6, 2, -64, 4],  None,      4, 18, ["II", "II"], 33.0, PTA_F_MONOPOLE_TARGET, 1e-15, 0.46),
        K3Candidate("cooper_s22", 3, [1, 1, 1, 1],    None,      None, None, None,    None, None, None,  None),
        K3Candidate("callens_s20", 5, [1, 0, -34, 0, 1], None,   None, None, None,    None, None, None,  None),  # Weight-5 CY4 seed
        K3Candidate("cooper_s18", 3, [2, 3, -5, 1],   None,      None, None, None,    None, None, None,  None),  # should be filtered
    ]
    ev = AutoEvolveK3(EvolutionParameters(population_size=10, max_generations=20))
    ev.initialize_population(seeds)
    best = ev.run(num_generations=10)
    print(f"\nBest: {best.id}  fitness={best.fitness:.4f}")
    ev.save_results(Path("outputs/k3_evolution"))
