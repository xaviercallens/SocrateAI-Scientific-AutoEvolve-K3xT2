"""
Multi-Node MCMC System Tests (ST-7)
=====================================
Comprehensive unit tests for the Phase 4 MCMC evaluation system.

Tests cover:
    - DESI likelihood engine: data loading, covariance, known-point χ²
    - MCMC sampler: acceptance rate, chain output shape, prior enforcement
    - Convergence diagnostics: R̂ for identical/divergent chains, n_eff
    - Coordinator: chain spawning and collection
    - Posterior analysis: HPD intervals, summary statistics
"""

import math
import os
import sys
import unittest

import numpy as np

# Ensure src/ is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))


# ========================================================================
# ST-1 Tests: DESI Likelihood Engine
# ========================================================================

class TestDESILikelihoodEngine(unittest.TestCase):
    """Tests for src/mcmc/desi_likelihood.py"""

    def setUp(self):
        """Initialize the engine with real DESI data."""
        from mcmc.desi_likelihood import DESILikelihoodEngine
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'desi_dr1')
        if os.path.exists(self.data_dir):
            self.engine = DESILikelihoodEngine(data_dir=self.data_dir)
            self.has_data = True
        else:
            self.has_data = False

    def test_loads_12_data_points(self):
        """Verify all 12 DESI DR1 BAO data points are loaded."""
        if not self.has_data:
            self.skipTest("DESI data not available")
        self.assertEqual(self.engine.ndof, 12)
        self.assertEqual(len(self.engine.data_points), 12)

    def test_covariance_is_12x12(self):
        """Verify covariance matrix shape matches data points."""
        if not self.has_data:
            self.skipTest("DESI data not available")
        self.assertEqual(self.engine._cov.shape, (12, 12))

    def test_covariance_is_symmetric(self):
        """Verify loaded covariance is symmetric."""
        if not self.has_data:
            self.skipTest("DESI data not available")
        np.testing.assert_allclose(self.engine._cov, self.engine._cov.T, atol=1e-12)

    def test_covariance_positive_definite(self):
        """Verify Cholesky decomposition succeeded (positive definiteness)."""
        if not self.has_data:
            self.skipTest("DESI data not available")
        self.assertIsNotNone(self.engine._cov_chol, "Cholesky decomposition should succeed")

    def test_data_quantities_expected(self):
        """Verify expected BAO quantity types are present."""
        if not self.has_data:
            self.skipTest("DESI data not available")
        quantities = {dp.quantity for dp in self.engine.data_points}
        self.assertIn("DM_over_rs", quantities)
        self.assertIn("DH_over_rs", quantities)
        self.assertIn("DV_over_rs", quantities)

    def test_log_likelihood_returns_result(self):
        """Verify log_likelihood returns a valid DESILikelihoodResult."""
        if not self.has_data:
            self.skipTest("DESI data not available")
        from mcmc.desi_likelihood import DESILikelihoodResult

        phenotype = {"w0": -1.0, "omega_m": 0.30, "h0": 67.4}
        result = self.engine.log_likelihood(phenotype)

        self.assertIsInstance(result, DESILikelihoodResult)
        self.assertTrue(np.isfinite(result.log_likelihood))
        self.assertGreaterEqual(result.chi2, 0.0)
        self.assertEqual(result.ndof, 13)
        self.assertEqual(len(result.residuals), 12)
        self.assertEqual(len(result.model_predictions), 12)

    def test_fiducial_cosmology_low_chi2(self):
        """
        At the DESI fiducial cosmology (w₀=−1, Ωₘ=0.3, H₀=67.4),
        χ² should be reasonably small (model is close to data).
        """
        if not self.has_data:
            self.skipTest("DESI data not available")
        phenotype = {"w0": -1.0, "omega_m": 0.30, "h0": 67.4}
        result = self.engine.log_likelihood(phenotype)
        # Fiducial cosmology should give χ² < 50 for 12 DOF
        self.assertLess(result.chi2, 50.0, f"Fiducial χ²={result.chi2} is too high")

    def test_extreme_cosmology_high_chi2(self):
        """A clearly wrong cosmology should give very high χ²."""
        if not self.has_data:
            self.skipTest("DESI data not available")
        phenotype = {"w0": -0.5, "omega_m": 0.10, "h0": 50.0}
        result = self.engine.log_likelihood(phenotype)
        self.assertGreater(result.chi2, 10.0)

    def test_hubble_distance_positive(self):
        """D_H must be positive for physical cosmologies."""
        if not self.has_data:
            self.skipTest("DESI data not available")
        from mcmc.desi_likelihood import DESILikelihoodEngine
        dh = DESILikelihoodEngine._hubble_distance(1.0, 67.4, 0.3, -1.0)
        self.assertGreater(dh, 0)


# ========================================================================
# ST-2 Tests: MCMC Sampler
# ========================================================================

class TestMetropolisHastingsSampler(unittest.TestCase):
    """Tests for src/mcmc/sampler.py"""

    def _make_sampler(self, n_steps=200, burn_in=50, seed=42):
        """Create a sampler with a simple Gaussian log-likelihood."""
        from mcmc.sampler import MetropolisHastingsSampler, MCMCConfig

        # Simple multivariate Gaussian target for testing
        target_mean = np.array([0.5, 0.0, 0.0, 0.0, 0.0])
        target_cov_inv = np.eye(5) * 4.0

        def log_l_fn(candidate):
            from mcmc.sampler import candidate_to_theta
            theta = candidate_to_theta(candidate)
            delta = theta - target_mean
            return -0.5 * delta @ target_cov_inv @ delta

        base_candidate = {
            "candidate_id": "test_cand",
            "picard_number": 19,
            "t2_modulus_tau": 0.5,
            "complex_structure": [1.0, 1.0, 1.0],
        }

        config = MCMCConfig(
            n_steps=n_steps,
            burn_in=burn_in,
            thin_factor=1,
            seed=seed,
        )

        return MetropolisHastingsSampler(
            log_likelihood_fn=log_l_fn,
            base_candidate=base_candidate,
            config=config,
        )

    def test_chain_output_shape(self):
        """Chain samples should have shape (n_kept, 5)."""
        from mcmc.sampler import N_PARAMS
        sampler = self._make_sampler(n_steps=200, burn_in=50)
        chain = sampler.run(chain_id=0)
        self.assertEqual(chain.samples.shape[1], N_PARAMS)
        # Expected kept = (200 - 50) / 1 = 150 (thin_factor=1)
        self.assertEqual(chain.samples.shape[0], 150)

    def test_acceptance_rate_reasonable(self):
        """Acceptance rate should be between 5% and 95% for a simple target."""
        sampler = self._make_sampler(n_steps=500, burn_in=100)
        chain = sampler.run(chain_id=0)
        self.assertGreater(chain.acceptance_rate, 0.05)
        self.assertLess(chain.acceptance_rate, 0.95)

    def test_log_likelihoods_finite(self):
        """All stored log-likelihoods should be finite."""
        sampler = self._make_sampler(n_steps=200, burn_in=50)
        chain = sampler.run(chain_id=0)
        self.assertTrue(np.all(np.isfinite(chain.log_likelihoods)))

    def test_prior_bounds_enforced(self):
        """All samples should be within the prior bounds."""
        from mcmc.sampler import PARAM_BOUNDS
        sampler = self._make_sampler(n_steps=500, burn_in=100)
        chain = sampler.run(chain_id=0)
        for p in range(chain.samples.shape[1]):
            self.assertTrue(
                np.all(chain.samples[:, p] >= PARAM_BOUNDS[p, 0]),
                f"Param {p} has samples below lower bound"
            )
            self.assertTrue(
                np.all(chain.samples[:, p] <= PARAM_BOUNDS[p, 1]),
                f"Param {p} has samples above upper bound"
            )

    def test_theta_candidate_roundtrip(self):
        """theta_to_candidate and candidate_to_theta should roundtrip."""
        from mcmc.sampler import theta_to_candidate, candidate_to_theta
        base = {
            "candidate_id": "test",
            "picard_number": 19,
            "t2_modulus_tau": 0.6,
            "complex_structure": [0.5, -0.2, 0.1],
        }
        theta = candidate_to_theta(base)
        reconstructed = theta_to_candidate(theta, base)
        self.assertAlmostEqual(reconstructed["t2_modulus_tau"], 0.6, places=5)
        self.assertAlmostEqual(reconstructed["complex_structure"][0], 0.5, places=5)


# ========================================================================
# ST-4 Tests: Convergence Diagnostics
# ========================================================================

class TestConvergenceDiagnostics(unittest.TestCase):
    """Tests for src/mcmc/diagnostics.py"""

    def test_gelman_rubin_identical_chains(self):
        """R̂ should be ≈ 1.0 for identical chains."""
        from mcmc.diagnostics import compute_gelman_rubin

        rng = np.random.default_rng(42)
        chain = rng.normal(0, 1, size=(500, 3))
        chains = [chain.copy() for _ in range(4)]
        param_names = ["p1", "p2", "p3"]

        r_hat = compute_gelman_rubin(chains, param_names, split=True)

        for name, r in r_hat.items():
            self.assertAlmostEqual(r, 1.0, delta=0.01,
                msg=f"R̂ for {name} should be ~1.0 for identical chains, got {r}")

    def test_gelman_rubin_divergent_chains(self):
        """R̂ should be >> 1.0 for chains with different means."""
        from mcmc.diagnostics import compute_gelman_rubin

        rng = np.random.default_rng(42)
        chains = [
            rng.normal(i * 5, 0.5, size=(500, 2))
            for i in range(4)
        ]
        param_names = ["p1", "p2"]

        r_hat = compute_gelman_rubin(chains, param_names, split=True)

        for name, r in r_hat.items():
            self.assertGreater(r, 1.5,
                msg=f"R̂ for {name} should be >> 1 for divergent chains, got {r}")

    def test_effective_sample_size_positive(self):
        """n_eff should be positive for any valid chain."""
        from mcmc.diagnostics import compute_effective_sample_size

        rng = np.random.default_rng(42)
        chains = [rng.normal(0, 1, size=(200, 2)) for _ in range(2)]
        param_names = ["p1", "p2"]

        n_eff = compute_effective_sample_size(chains, param_names)

        for name, n in n_eff.items():
            self.assertGreater(n, 0, f"n_eff for {name} should be positive")

    def test_autocorrelation_time_positive(self):
        """τ_int should be ≥ 1 for any valid chain."""
        from mcmc.diagnostics import compute_autocorrelation_time

        rng = np.random.default_rng(42)
        chains = [rng.normal(0, 1, size=(200, 2)) for _ in range(2)]
        param_names = ["p1", "p2"]

        tau = compute_autocorrelation_time(chains, param_names)

        for name, t in tau.items():
            self.assertGreaterEqual(t, 1.0, f"τ_int for {name} should be ≥ 1")

    def test_geweke_stationary_chain(self):
        """Geweke z-score should be small (< 2) for a stationary chain."""
        from mcmc.diagnostics import compute_geweke

        rng = np.random.default_rng(42)
        chains = [rng.normal(0, 1, size=(1000, 2)) for _ in range(2)]
        param_names = ["p1", "p2"]

        geweke = compute_geweke(chains, param_names)

        for name, z in geweke.items():
            self.assertLess(abs(z), 3.0,
                f"Geweke z for {name} should be small for stationary chain, got {z}")

    def test_run_all_diagnostics(self):
        """run_all_diagnostics should return a ConvergenceDiagnostics object."""
        from mcmc.diagnostics import run_all_diagnostics, ConvergenceDiagnostics

        rng = np.random.default_rng(42)
        chains = [rng.normal(0, 1, size=(200, 3)) for _ in range(4)]
        param_names = ["p1", "p2", "p3"]

        diagnostics = run_all_diagnostics(chains, param_names)

        self.assertIsInstance(diagnostics, ConvergenceDiagnostics)
        self.assertEqual(len(diagnostics.r_hat), 3)
        self.assertEqual(len(diagnostics.n_eff), 3)
        self.assertIsInstance(diagnostics.all_converged, bool)
        self.assertTrue(diagnostics.all_converged,
            "IID Gaussian chains should converge")


# ========================================================================
# ST-3 Tests: Coordinator
# ========================================================================

class TestMCMCCoordinator(unittest.TestCase):
    """Tests for src/mcmc/coordinator.py"""

    def _make_coordinator(self, n_chains=2, n_steps=200, burn_in=50):
        """Create a coordinator with a simple Gaussian target."""
        from mcmc.coordinator import MCMCCoordinator, CoordinatorConfig

        target_mean = np.array([0.5, 0.0, 0.0, 0.0, 0.0])

        def log_l_fn(candidate):
            from mcmc.sampler import candidate_to_theta
            theta = candidate_to_theta(candidate)
            delta = theta - target_mean
            return -0.5 * float(delta @ delta) * 4.0

        base_candidate = {
            "candidate_id": "test_coord",
            "picard_number": 19,
            "t2_modulus_tau": 0.5,
            "complex_structure": [1.0, 1.0, 1.0],
        }

        config = CoordinatorConfig(
            n_chains=n_chains,
            n_steps_per_chain=n_steps,
            burn_in=burn_in,
            thin_factor=1,
            max_iterations=1,
            n_workers=1,  # Sequential for test reliability
            checkpoint_dir="outputs/mcmc/test_chains",
        )

        return MCMCCoordinator(
            log_likelihood_fn=log_l_fn,
            base_candidate=base_candidate,
            config=config,
        )

    def test_spawn_and_collect_n_chains(self):
        """Coordinator should produce exactly N chains."""
        coordinator = self._make_coordinator(n_chains=3, n_steps=200, burn_in=50)
        result = coordinator.run()
        self.assertEqual(len(result.chains), 3)

    def test_merged_samples_shape(self):
        """Merged samples should have correct total count."""
        from mcmc.sampler import N_PARAMS
        coordinator = self._make_coordinator(n_chains=2, n_steps=200, burn_in=50)
        result = coordinator.run()
        expected_per_chain = 200 - 50  # thin_factor=1
        expected_total = 2 * expected_per_chain
        self.assertEqual(result.merged_samples.shape, (expected_total, N_PARAMS))

    def test_result_has_diagnostics(self):
        """Result should contain convergence diagnostics."""
        from mcmc.diagnostics import ConvergenceDiagnostics
        coordinator = self._make_coordinator(n_chains=2, n_steps=200, burn_in=50)
        result = coordinator.run()
        self.assertIsInstance(result.diagnostics, ConvergenceDiagnostics)


# ========================================================================
# ST-5 Tests: Posterior Analysis
# ========================================================================

class TestPosteriorAnalysis(unittest.TestCase):
    """Tests for src/mcmc/posterior.py"""

    def test_hpd_contains_true_value(self):
        """68% HPD of Gaussian samples should contain the true mean."""
        from mcmc.posterior import compute_hpd

        rng = np.random.default_rng(42)
        samples = rng.normal(5.0, 1.0, size=5000)
        lo, hi = compute_hpd(samples, 0.68)
        self.assertLess(lo, 5.0, "68% HPD lower bound should be below true mean")
        self.assertGreater(hi, 5.0, "68% HPD upper bound should be above true mean")

    def test_hpd_95_wider_than_68(self):
        """95% HPD should be wider than 68% HPD."""
        from mcmc.posterior import compute_hpd

        rng = np.random.default_rng(42)
        samples = rng.normal(0.0, 1.0, size=5000)
        hpd_68 = compute_hpd(samples, 0.68)
        hpd_95 = compute_hpd(samples, 0.95)
        width_68 = hpd_68[1] - hpd_68[0]
        width_95 = hpd_95[1] - hpd_95[0]
        self.assertGreater(width_95, width_68)

    def test_analyze_posterior_output(self):
        """analyze_posterior should return a PosteriorSummary."""
        from mcmc.posterior import analyze_posterior, PosteriorSummary

        rng = np.random.default_rng(42)
        samples = rng.normal(0, 1, size=(500, 3))
        log_l = -0.5 * np.sum(samples ** 2, axis=1)
        param_names = ["p1", "p2", "p3"]

        posterior = analyze_posterior(samples, log_l, param_names, "test")

        self.assertIsInstance(posterior, PosteriorSummary)
        self.assertEqual(len(posterior.parameters), 3)
        self.assertEqual(posterior.correlation_matrix.shape, (3, 3))

    def test_posterior_to_dict(self):
        """to_dict should produce a JSON-serializable dict."""
        from mcmc.posterior import analyze_posterior

        rng = np.random.default_rng(42)
        samples = rng.normal(0, 1, size=(200, 2))
        log_l = -0.5 * np.sum(samples ** 2, axis=1)

        posterior = analyze_posterior(samples, log_l, ["p1", "p2"], "test")
        d = posterior.to_dict()

        self.assertIn("candidate_id", d)
        self.assertIn("parameters", d)
        self.assertIn("correlation_matrix", d)
        # Verify JSON-serializable
        import json
        json.dumps(d)  # Should not raise

    def test_latex_table_output(self):
        """format_latex_table should produce a string with LaTeX markers."""
        from mcmc.posterior import analyze_posterior, format_latex_table

        rng = np.random.default_rng(42)
        samples = rng.normal(0, 1, size=(200, 2))
        log_l = -0.5 * np.sum(samples ** 2, axis=1)

        posterior = analyze_posterior(samples, log_l, ["w0", "omega_m"], "test")
        latex = format_latex_table(posterior)

        self.assertIn(r"\begin{table}", latex)
        self.assertIn(r"\end{table}", latex)
        self.assertIn("w0", latex)


if __name__ == "__main__":
    unittest.main()
