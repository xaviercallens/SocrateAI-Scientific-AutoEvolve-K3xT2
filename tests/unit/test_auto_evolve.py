"""
Unit tests for AutoEvolveK3 and AstrophysicsValidator (TEST-02)
"""

import json
import sys
import os
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from evolution.auto_evolve_k3_selection import (
    AutoEvolveK3, K3Candidate, EvolutionParameters, BLOCKED_CANDIDATES
)
from validation.astrophysics_validator import AstrophysicsValidator, AstrophysicsCriteria
from mcmc.observational_constants import PTA_F_MONOPOLE_TARGET


# ------------------------------------------------------------------ #
# Fixtures                                                             #
# ------------------------------------------------------------------ #

@pytest.fixture
def seeds():
    return [
        K3Candidate("cooper_s7",  3, [13.0, 4.0, -27.0, 3.0], "A279619", 4, 18, ["II","II"], 47.0, PTA_F_MONOPOLE_TARGET, 1e-15, 0.50),
        K3Candidate("cooper_s10", 3, [6.0, 2.0, -64.0, 4.0],  None,      4, 18, ["II","II"], 33.0, PTA_F_MONOPOLE_TARGET, 1e-15, 0.46),
        K3Candidate("cooper_s22", 3, [1.0, 1.0,  1.0,  1.0],  None,      None,None,None,     None,None, None, None),
    ]


@pytest.fixture
def evolve(seeds):
    ev = AutoEvolveK3(EvolutionParameters(population_size=3, max_generations=5, elitism_count=1))
    ev.initialize_population(seeds)
    return ev


# ------------------------------------------------------------------ #
# AutoEvolveK3                                                         #
# ------------------------------------------------------------------ #

class TestAutoEvolveK3:

    def test_initialization_population_size(self, seeds):
        ev = AutoEvolveK3(EvolutionParameters(population_size=3, elitism_count=1))
        ev.initialize_population(seeds)
        assert len(ev.population) == 3

    def test_best_candidate_set_after_init(self, evolve):
        assert evolve.best_candidate is not None

    def test_blocked_candidate_filtered(self, seeds):
        """cooper_s18 must never appear in population."""
        blocked = K3Candidate("cooper_s18", 3, [2.0, 3.0, -5.0, 1.0])
        ev = AutoEvolveK3(EvolutionParameters(population_size=3, elitism_count=1))
        ev.initialize_population(seeds + [blocked])
        ids = {c.id for c in ev.population}
        assert "cooper_s18" not in ids
        assert "cooper_s18" in BLOCKED_CANDIDATES

    def test_evolve_increments_generation(self, evolve):
        assert evolve.generation == 0
        evolve.evolve()
        assert evolve.generation == 1

    def test_fitness_in_bounds(self, evolve):
        for c in evolve.population:
            assert 0.0 <= c.fitness <= 1.0

    def test_crossover_preserves_ode_length(self, evolve):
        p1, p2 = evolve.population[0], evolve.population[1]
        c1, c2 = evolve._crossover(p1, p2)
        assert len(c1.ode_coefficients) == len(p1.ode_coefficients)
        assert len(c2.ode_coefficients) == len(p2.ode_coefficients)

    def test_mutation_preserves_ode_order(self, evolve):
        original = evolve.population[0]
        mutated = evolve._mutate(original)
        assert mutated.ode_order == original.ode_order
        assert len(mutated.ode_coefficients) == len(original.ode_coefficients)

    def test_run_returns_k3_candidate(self, evolve):
        best = evolve.run(num_generations=2)
        assert isinstance(best, K3Candidate)

    def test_save_results(self, evolve, tmp_path):
        evolve.run(num_generations=1)
        evolve.save_results(tmp_path)
        assert (tmp_path / "best_candidate.json").exists()
        assert (tmp_path / "evolution_history.json").exists()
        with open(tmp_path / "best_candidate.json") as f:
            data = json.load(f)
        assert "fitness" in data
        assert "ode_order" in data

    def test_convergence_check_too_early(self, evolve):
        """Should not converge with < 10 generations of history."""
        assert evolve._check_convergence() is False


# ------------------------------------------------------------------ #
# AstrophysicsValidator                                                #
# ------------------------------------------------------------------ #

class TestAstrophysicsValidator:

    def test_weak_lensing_smooth(self):
        assert AstrophysicsValidator.validate_weak_lensing(0.5) is True

    def test_weak_lensing_moderate(self):
        assert AstrophysicsValidator.validate_weak_lensing(5.0) is True

    def test_weak_lensing_extreme(self):
        assert AstrophysicsValidator.validate_weak_lensing(47.0) is True

    def test_pta_exact_target(self):
        assert AstrophysicsValidator.validate_pta(PTA_F_MONOPOLE_TARGET, 1e-15) is True

    def test_pta_fail_frequency(self):
        assert AstrophysicsValidator.validate_pta(PTA_F_MONOPOLE_TARGET * 2, 1e-15) is False

    def test_chameleon_pass(self):
        assert AstrophysicsValidator.validate_chameleon(0.46) is True

    def test_chameleon_fail_boundary(self):
        assert AstrophysicsValidator.validate_chameleon(0.40) is False

    def test_chameleon_exact_boundary(self):
        # α_eff > 0.45 strictly, 0.45 is a fail
        assert AstrophysicsValidator.validate_chameleon(0.45) is False

    def test_gd1_pass(self):
        assert AstrophysicsValidator.validate_gd1({"rate": 0.05}) is True

    def test_gd1_fail(self):
        assert AstrophysicsValidator.validate_gd1({"rate": 0.15}) is False

    def test_core_cusp_pass(self):
        assert AstrophysicsValidator.validate_core_cusp(0.01) is True

    def test_core_cusp_fail(self):
        assert AstrophysicsValidator.validate_core_cusp(0.10) is False

    def test_s8_gradient_exact(self):
        assert AstrophysicsValidator.validate_s8(0.83) is True

    def test_s8_gradient_fail(self):
        assert AstrophysicsValidator.validate_s8(0.70) is False

    def test_validate_all_full_pass(self):
        validator = AstrophysicsValidator()
        criteria = AstrophysicsCriteria(
            delta_obs=47.0,
            pta_frequency=PTA_F_MONOPOLE_TARGET,
            pta_amplitude=1e-15,
            alpha_eff=0.50,
            gd1_heating_bounds={"rate": 0.05},
            core_cusp_tension=0.01,
            s8_gradient=0.83,
        )
        results = validator.validate_all(criteria)
        assert all(results.values()), f"Failing criteria: {[k for k,v in results.items() if not v]}"

    def test_validate_all_partial(self):
        """Only weak_lensing required; others skipped when None."""
        validator = AstrophysicsValidator()
        criteria = AstrophysicsCriteria(delta_obs=5.0)
        results = validator.validate_all(criteria)
        assert "weak_lensing" in results
        assert "pta" not in results
