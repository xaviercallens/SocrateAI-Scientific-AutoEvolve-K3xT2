import math
import unittest

from src.evolution.population_diversity import population_diversity


class TestPopulationDiversity(unittest.TestCase):
    def test_diverse_population_is_not_collapsed(self):
        pop = [{"chi2_loss": v} for v in (0.5, 1.25, 2.0, 3.5)]
        d = population_diversity(pop)
        self.assertEqual(d["distinct"], 4)
        self.assertFalse(d["collapsed"])
        self.assertAlmostEqual(d["mean"], 1.8125)
        self.assertAlmostEqual(d["variance"], 1.23046875)  # deviations sum of squares 4.921875 / 4

    def test_two_values_count_as_collapsed(self):
        pop = [{"chi2_loss": v} for v in (1.0, 1.0, 1.0, 2.0, 2.0)]
        d = population_diversity(pop)
        self.assertEqual(d["distinct"], 2)
        self.assertTrue(d["collapsed"])

    def test_float_noise_below_resolution_is_not_diversity(self):
        pop = [{"chi2_loss": 1.0 + k * 1e-13} for k in range(10)]
        d = population_diversity(pop, decimals=9)
        self.assertEqual(d["distinct"], 1)
        self.assertTrue(d["collapsed"])

    def test_missing_and_non_finite_values_are_skipped_and_counted(self):
        pop = [{"chi2_loss": 1.0}, {"chi2_loss": math.nan}, {}, {"chi2_loss": 3.0}, {"chi2_loss": 5.0}]
        d = population_diversity(pop)
        self.assertEqual(d["n"], 3)
        self.assertEqual(d["skipped"], 2)
        self.assertFalse(d["collapsed"])

    def test_empty_population_is_collapsed(self):
        d = population_diversity([])
        self.assertEqual(d["n"], 0)
        self.assertTrue(d["collapsed"])


if __name__ == "__main__":
    unittest.main()
