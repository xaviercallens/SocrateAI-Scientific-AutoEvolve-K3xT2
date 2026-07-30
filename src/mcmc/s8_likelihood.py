"""
KiDS-1000 S₈ Likelihood for AlphaEvolve K3×T² (IMP-04)
========================================================
Implements the S₈ tension likelihood from the KiDS-1000 weak lensing
survey as a Gaussian constraint:

    S₈ = σ₈ √(Ωₘ/0.3)  = 0.759 ± 0.024  (KiDS-1000, Asgari et al. 2021)

The K3×T² model predicts:
    S₈_model = s8_gradient(P) = 0.83 - 0.015 × (19 - P)

at P=19 → S₈_model = 0.830, which is in ~3σ tension with KiDS-1000
and ~1σ consistent with DES-Y3 (0.776 ± 0.017).

This module adds the S₈ likelihood term to the full joint MCMC, which:
1. Formally quantifies the tension as a Bayesian evidence ratio
2. Constrains the Picard offset independently from BAO data
3. Tests whether K3×T² at P=19 genuinely resolves or amplifies the S₈ tension

References:
    Asgari et al. 2021 (KiDS-1000): S₈ = 0.759 ± 0.024
    Amon et al. 2022 (DES-Y3):      S₈ = 0.776 ± 0.017
    Planck 2018:                    S₈ = 0.832 ± 0.013
"""

import math
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class S8LikelihoodConfig:
    """Configuration for the S₈ likelihood term."""
    # KiDS-1000 constraint (Asgari et al. 2021) — tightest WL measurement
    kids_s8_mean:  float = 0.759
    kids_s8_sigma: float = 0.024

    # DES-Y3 constraint (Amon et al. 2022)
    des_s8_mean:   float = 0.776
    des_s8_sigma:  float = 0.017

    # Planck 2018 CMB (baseline)
    planck_s8_mean:  float = 0.832
    planck_s8_sigma: float = 0.013

    # Which dataset(s) to include
    use_kids:   bool = True
    use_des:    bool = True
    use_planck: bool = False    # Planck S₈ is derived — can cause double-counting


@dataclass
class S8LikelihoodResult:
    """Result of evaluating the S₈ likelihood."""
    log_likelihood: float
    s8_model: float
    chi2_kids: Optional[float]
    chi2_des: Optional[float]
    chi2_planck: Optional[float]
    tension_kids_sigma: float      # How many σ away from KiDS-1000


class S8Likelihood:
    """
    S₈ weak lensing likelihood for the K3×T² posterior.

    Combines KiDS-1000 and/or DES-Y3 measurements as independent
    Gaussian constraints on the predicted S₈ value.

    The model prediction is extracted from the phenotype mapper output:
        S₈_model = 0.83 - 0.015 × (19 - P)

    Usage:
        engine = S8Likelihood(S8LikelihoodConfig())
        result = engine.log_likelihood(phenotype)
    """

    def __init__(self, config: S8LikelihoodConfig = S8LikelihoodConfig()):
        self.config = config
        logger.info(
            f"S₈ Likelihood: KiDS={config.use_kids} "
            f"(S₈={config.kids_s8_mean}±{config.kids_s8_sigma}), "
            f"DES={config.use_des} "
            f"(S₈={config.des_s8_mean}±{config.des_s8_sigma})"
        )

    def log_likelihood(self, phenotype: dict) -> S8LikelihoodResult:
        """
        Evaluate log-likelihood from model S₈ against observational priors.

        Args:
            phenotype: Output from map_k3_to_cosmology(), must contain 's8_gradient'.

        Returns:
            S8LikelihoodResult with total log-likelihood and tension diagnostics.
        """
        s8_model = phenotype.get("s8_gradient", 0.83)
        log_l = 0.0
        chi2_kids = None
        chi2_des = None
        chi2_planck = None

        if self.config.use_kids:
            chi2_kids = ((s8_model - self.config.kids_s8_mean)
                         / self.config.kids_s8_sigma) ** 2
            log_l -= 0.5 * chi2_kids
            log_l -= 0.5 * math.log(2 * math.pi * self.config.kids_s8_sigma ** 2)

        if self.config.use_des:
            chi2_des = ((s8_model - self.config.des_s8_mean)
                        / self.config.des_s8_sigma) ** 2
            log_l -= 0.5 * chi2_des
            log_l -= 0.5 * math.log(2 * math.pi * self.config.des_s8_sigma ** 2)

        if self.config.use_planck:
            chi2_planck = ((s8_model - self.config.planck_s8_mean)
                           / self.config.planck_s8_sigma) ** 2
            log_l -= 0.5 * chi2_planck
            log_l -= 0.5 * math.log(2 * math.pi * self.config.planck_s8_sigma ** 2)

        # Compute tension in σ units relative to KiDS-1000
        tension_sigma = abs(s8_model - self.config.kids_s8_mean) / self.config.kids_s8_sigma

        return S8LikelihoodResult(
            log_likelihood=log_l,
            s8_model=s8_model,
            chi2_kids=chi2_kids,
            chi2_des=chi2_des,
            chi2_planck=chi2_planck,
            tension_kids_sigma=tension_sigma,
        )
