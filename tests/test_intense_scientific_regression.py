"""
Intense Scientific Unit & Regression Test Suite for K3×T² Cosmology Engine
==========================================================================
Enforces mathematical, theoretical, statistical, and code invariants to guarantee
zero regressions across all pipeline modules.

Modules Covered:
1. EFT Phenotype Mapping & Mathematical Provenance (phenotype_mapper.py)
2. Bayesian Likelihood Engine & Covariance Invariants (desi_likelihood.py)
3. Symbolic Swampland Gatekeeper & Lean 4 Interfaces (lean_client.py, lean_gatekeeper.py)
4. Physical Monopole Target & GA Resonance Penalties (auto_evolve_k3_selection.py)
5. Differentiable Picard-Fuchs Neural ODE Integrator (neural_ode_pf.py)
6. Multi-Schema Seed Serialization & Ingestion (autoevolve_ingest.py)
"""

import os
import sys
import unittest
import numpy as np
import torch
import pytest

# Ensure src/ is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from alpha_evolve.phenotype_mapper import map_k3_to_cosmology, map_k3_to_cosmology_eft
from mcmc.desi_likelihood import DESILikelihoodEngine
from mcmc.observational_constants import PTA_F_MONOPOLE_TARGET, H0_PLANCK, OMEGA_M_PLANCK
from integration.lean_client import _simulated_lean_verify
from alpha_evolve.lean_gatekeeper import tier2_lean_gatekeeper
from evolution.auto_evolve_k3_selection import AutoEvolveK3, K3Candidate, EvolutionParameters
from validation.astrophysics_validator import AstrophysicsValidator
from ml_modules.neural_ode_pf import PicardFuchsODEFunc, EulerNeuralODESolver
from integration.autoevolve_ingest import load_cooper_seeds, augment_seeds


class TestEFTPhenotypeInvariants(unittest.TestCase):
    """Regression tests for EFT phenotype mapping and mathematical provenance."""

    def test_eft_phenotype_mapping_domain_bounds(self):
        candidate = {
            "candidate_id": "cooper_s10_test",
            "picard_number": 19,
            "moduli_stabilization": 0.75,
            "complex_structure": [0.5, 0.5, 1.0],
            "t2_modulus_tau": 0.50,
        }
        pheno = map_k3_to_cosmology_eft(candidate)

        # Assert output keys exist
        self.assertIn("w0", pheno)
        self.assertIn("omega_m", pheno)
        self.assertIn("h0", pheno)
        self.assertIn("s8_gradient", pheno)
        self.assertIn("pta_f_monopole", pheno)

        # Physical domain bounds
        self.assertGreaterEqual(pheno["w0"], -2.0)
        self.assertLessEqual(pheno["w0"], 0.0)
        self.assertGreater(pheno["omega_m"], 0.0)
        self.assertLess(pheno["omega_m"], 1.0)
        self.assertGreaterEqual(pheno["h0"], 50.0)
        self.assertLessEqual(pheno["h0"], 90.0)
        self.assertGreater(pheno["pta_f_monopole"], 0.0)

    def test_discrete_picard_number_handling(self):
        """Ensure Picard numbers are handled consistently whether passed as int or float."""
        cand_int = {"picard_number": 19, "moduli_stabilization": 0.5, "complex_structure": [1.0, 1.0, 1.0]}
        cand_float = {"picard_number": 19.0, "moduli_stabilization": 0.5, "complex_structure": [1.0, 1.0, 1.0]}

        p_int = map_k3_to_cosmology_eft(cand_int)
        p_float = map_k3_to_cosmology_eft(cand_float)

        self.assertAlmostEqual(p_int["w0"], p_float["w0"], places=6)
        self.assertAlmostEqual(p_int["omega_m"], p_float["omega_m"], places=6)

    def test_strict_eft_provenance_error_on_missing_module(self):
        """Ensure silent fallback is disabled and error is raised when invalid potential input is supplied."""
        invalid_candidate = {"picard_number": "INVALID_PICARD"}
        with self.assertRaises((RuntimeError, TypeError, ValueError)):
            map_k3_to_cosmology_eft(invalid_candidate)


class TestDESILikelihoodInvariants(unittest.TestCase):
    """Regression tests for DESI BAO MCMC likelihood engine and covariance properties."""

    def setUp(self):
        self.engine = DESILikelihoodEngine()

    def test_desi_likelihood_ndof_is_twelve(self):
        """DESI BAO likelihood MUST strictly return ndof = 12 (no double-counted anisotropic probes)."""
        self.assertEqual(self.engine._ndof, 12)

    def test_desi_covariance_matrix_properties(self):
        """Covariance matrix must be 12x12, symmetric, and positive definite."""
        cov = self.engine._cov
        self.assertEqual(cov.shape, (12, 12))

        # Check symmetry
        np.testing.assert_allclose(cov, cov.T, rtol=1e-5, atol=1e-8)

        # Check positive definiteness (all eigenvalues > 0)
        eigvals = np.linalg.eigvalsh(cov)
        self.assertTrue(np.all(eigvals > 0), f"Non-positive eigenvalues found: {eigvals}")

    def test_desi_log_likelihood_eval_result(self):
        phenotype = {
            "w0": -1.0,
            "omega_m": OMEGA_M_PLANCK,
            "h0": H0_PLANCK,
        }
        res = self.engine.log_likelihood(phenotype)

        self.assertEqual(res.ndof, 12)
        self.assertGreaterEqual(res.chi2, 0.0)
        self.assertEqual(len(res.residuals), 12)
        self.assertEqual(len(res.model_predictions), 12)
        self.assertIsInstance(res.log_likelihood, float)


class TestSwamplandGatekeeperInvariants(unittest.TestCase):
    """Regression tests for Swampland Lean 4 gatekeeper boundary conditions."""

    def test_simulated_lean_verify_valid_regime(self):
        cand = {"picard_number": 19, "moduli_stabilization": 0.50}
        res = _simulated_lean_verify(cand)

        self.assertTrue(res["passed_swampland"])
        self.assertTrue(res["uv_complete"])
        self.assertEqual(res["penalty_score"], 0.0)
        self.assertIn("Distance and dS conjectures satisfied", res["formal_reason"])

    def test_simulated_lean_verify_picard_exceeded(self):
        cand = {"picard_number": 25, "moduli_stabilization": 0.50}
        res = _simulated_lean_verify(cand)

        self.assertFalse(res["passed_swampland"])
        self.assertFalse(res["uv_complete"])
        self.assertEqual(res["penalty_score"], 9999.9)

    def test_simulated_lean_verify_unstable_moduli(self):
        cand = {"picard_number": 15, "moduli_stabilization": -0.05}
        res = _simulated_lean_verify(cand)

        self.assertFalse(res["passed_swampland"])
        self.assertFalse(res["uv_complete"])
        self.assertEqual(res["penalty_score"], 9999.9)

    def test_tier2_gatekeeper_filtering_stats(self):
        pop = [
            {"candidate_id": "valid_1", "picard_number": 19, "moduli_stabilization": 0.5},
            {"candidate_id": "invalid_picard", "picard_number": 25, "moduli_stabilization": 0.5},
            {"candidate_id": "invalid_moduli", "picard_number": 15, "moduli_stabilization": -0.2},
        ]
        survivors, stats = tier2_lean_gatekeeper(pop)

        self.assertEqual(len(survivors), 1)
        self.assertEqual(survivors[0]["candidate_id"], "valid_1")
        self.assertEqual(stats["input_count"], 3)
        self.assertEqual(stats["passed_count"], 1)
        self.assertEqual(stats["failed_count"], 2)


class TestPhysicalResonanceInvariants(unittest.TestCase):
    """Regression tests for PTA Compton monopole target frequency alignment."""

    def test_pta_monopole_target_value(self):
        """PTA_F_MONOPOLE_TARGET must match 24.18 nHz (2.418e-8 Hz)."""
        self.assertAlmostEqual(PTA_F_MONOPOLE_TARGET, 2.418e-8, delta=1e-11)

    def test_astrophysics_validator_pta(self):
        # Exact target passes
        self.assertTrue(AstrophysicsValidator.validate_pta(PTA_F_MONOPOLE_TARGET, 1e-15))
        # Off target fails
        self.assertFalse(AstrophysicsValidator.validate_pta(PTA_F_MONOPOLE_TARGET * 2.0, 1e-15))

    def test_auto_evolve_selection_fitness(self):
        cand_perfect = K3Candidate(
            id="cand_perf",
            ode_order=3,
            ode_coefficients=[1.0, 0.0, 0.0, 0.0],
            delta_obs=47.0,
            pta_frequency=PTA_F_MONOPOLE_TARGET,
            pta_amplitude=1e-15,
            alpha_eff=0.50
        )
        ev = AutoEvolveK3()
        fitness = ev._calculate_fitness(cand_perfect)
        self.assertGreaterEqual(fitness, 0.70)


class TestNeuralODEPicardFuchsInvariants(unittest.TestCase):
    """Regression tests for Picard-Fuchs 3rd-order Neural ODE integration."""

    def test_neural_ode_3d_state_vector_shape(self):
        ode_func = PicardFuchsODEFunc(hidden_dim=16)
        solver = EulerNeuralODESolver(ode_func)

        z_span = torch.linspace(0.001, 0.02, steps=10)
        # 3D state vector [y, dy/dz, d2y/dz2]
        y0 = torch.tensor([[1.0, 0.0, 0.0]], dtype=torch.float32)

        traj = solver.integrate(y0, z_span)

        # Expected output shape: (batch_size=1, num_steps=10, state_dim=3)
        self.assertEqual(traj.shape, (1, 10, 3))

    def test_neural_ode_gradient_backprop(self):
        ode_func = PicardFuchsODEFunc(hidden_dim=16)
        solver = EulerNeuralODESolver(ode_func)

        z_span = torch.linspace(0.001, 0.02, steps=10)
        y0 = torch.tensor([[1.0, 0.0, 0.0]], dtype=torch.float32)

        traj = solver.integrate(y0, z_span)
        loss = traj.sum()
        loss.backward()

        for name, param in ode_func.named_parameters():
            if param.requires_grad:
                self.assertIsNotNone(param.grad, f"Gradient missing for parameter {name}")


class TestSeedSchemaInvariants(unittest.TestCase):
    """Regression tests for cooper_seeds.json multi-schema loading and augmentation."""

    def test_load_cooper_seeds_multi_schema(self):
        seeds_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "configs", "cooper_seeds.json")
        )
        seeds = load_cooper_seeds(seeds_path)

        self.assertGreaterEqual(len(seeds), 3)
        for s in seeds:
            self.assertEqual(s.generation, 0)
            self.assertGreater(s.complex_structure_tau.imag, 0.0)

    def test_augment_seeds_output_size_and_tau_bounds(self):
        seeds_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "configs", "cooper_seeds.json")
        )
        seeds = load_cooper_seeds(seeds_path)
        n_pert = 4
        augmented = augment_seeds(seeds, n_perturbations=n_pert)

        expected_count = len(seeds) + (len(seeds) * n_pert)
        self.assertEqual(len(augmented), expected_count)

        for c in augmented:
            self.assertGreater(c.complex_structure_tau.imag, 0.0)


if __name__ == "__main__":
    unittest.main()
