import numpy as np
import dynesty
import copy
from typing import Dict, Any, Callable
from src.alpha_evolve.phenotype_mapper import map_k3_to_cosmology
from src.mcmc.desi_likelihood import DESILikelihoodEngine

class NestedSamplingEngine:
    def __init__(self, base_candidate: dict):
        self.base_candidate = base_candidate
        self.engine = DESILikelihoodEngine()
        # Parameters: t2_modulus_tau, cs_1, cs_2, cs_3, picard_offset
        self.bounds = [
            (0.01, 1.50),  # tau
            (-3.0, 3.0),   # cs_1
            (-3.0, 3.0),   # cs_2
            (-3.0, 3.0),   # cs_3
            (-3.0, 3.0)    # picard_offset
        ]

    def prior_transform(self, u):
        x = np.empty_like(u)
        for i, (lo, hi) in enumerate(self.bounds):
            x[i] = lo + u[i] * (hi - lo)
        return x

    def _theta_to_candidate(self, theta):
        candidate = copy.deepcopy(self.base_candidate)
        candidate["t2_modulus_tau"] = float(theta[0])
        candidate["complex_structure"] = [float(theta[1]), float(theta[2]), float(theta[3])]
        base_picard = self.base_candidate.get("picard_number", 19)
        candidate["picard_number"] = int(np.clip(base_picard + round(theta[4]), 1, 20))
        return candidate

    def log_likelihood(self, theta):
        candidate = self._theta_to_candidate(theta)
        phenotype = map_k3_to_cosmology(candidate)
        
        result = self.engine.log_likelihood(phenotype)
        return result.log_likelihood

    def run(self, nlive=200, dlogz=0.01):
        sampler = dynesty.NestedSampler(
            self.log_likelihood, self.prior_transform,
            ndim=5, nlive=nlive, bound='multi', sample='rwalk'
        )
        sampler.run_nested(dlogz=dlogz, print_progress=True)
        return sampler.results

    def extract_evidence(self, results):
        return {
            'logZ': float(results.logz[-1]),
            'logZ_err': float(results.logzerr[-1]),
            'H': float(results.information[-1]),
            'n_samples': len(results.samples),
        }
