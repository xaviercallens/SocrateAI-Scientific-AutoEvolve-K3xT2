"""
DESI DR1 BAO Likelihood Engine (ST-1)
======================================
Loads real DESI DR1 BAO distance measurements and their 12×12 covariance
matrix, then evaluates the multivariate Gaussian log-likelihood for any
K3×T² candidate mapped through the phenotype mapper.

Data files consumed:
    data/desi_dr1/desi_2024_gaussian_bao_ALL_GCcomb_mean.txt   — 12 BAO measurements
    data/desi_dr1/desi_2024_gaussian_bao_ALL_GCcomb_cov.txt    — 12×12 covariance matrix
"""

import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.linalg import cho_factor, cho_solve, LinAlgError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Physical constants for BAO distance computation
# ---------------------------------------------------------------------------
_C_KM_S = 299792.458          # Speed of light in km/s
_RD_FIDUCIAL = 147.09         # Sound horizon at drag epoch (Mpc) — Planck 2018


@dataclass(frozen=True)
class DESIDataPoint:
    """A single DESI DR1 BAO measurement."""
    z: float                   # Effective redshift
    value: float               # Measured distance ratio
    quantity: str              # 'DV_over_rs', 'DM_over_rs', or 'DH_over_rs'


@dataclass
class DESILikelihoodResult:
    """Result of evaluating a candidate against DESI DR1 BAO."""
    log_likelihood: float
    chi2: float
    ndof: int
    residuals: np.ndarray      # Δ = model − data (length N_data)
    model_predictions: np.ndarray


class DESILikelihoodEngine:
    """
    Multivariate Gaussian likelihood evaluator for DESI DR1 BAO data.

    Loads the 12-point BAO distance measurements and their full covariance
    matrix, pre-computes the Cholesky decomposition of C, and evaluates:

        log 𝓛 = −½ Δᵀ C⁻¹ Δ − ½ ln|C| − (N/2) ln(2π)

    where Δ = model_prediction(θ) − data_mean.
    """

    def __init__(
        self,
        data_dir: str = "data/desi_dr1",
        mean_file: str = "desi_2024_gaussian_bao_ALL_GCcomb_mean.txt",
        cov_file: str = "desi_2024_gaussian_bao_ALL_GCcomb_cov.txt",
    ):
        self.data_dir = Path(data_dir)
        self._data_points: List[DESIDataPoint] = []
        self._data_mean: Optional[np.ndarray] = None
        self._cov: Optional[np.ndarray] = None
        self._cov_chol: Optional[Tuple] = None      # Cholesky factor (L, lower)
        self._log_det_cov: float = 0.0
        self._ndof: int = 0

        self._load_mean(self.data_dir / mean_file)
        self._load_covariance(self.data_dir / cov_file)

    # ------------------------------------------------------------------
    # Data Loading
    # ------------------------------------------------------------------

    def _load_mean(self, path: Path) -> None:
        """Parse the DESI BAO mean measurement file."""
        if not path.exists():
            raise FileNotFoundError(f"DESI mean file not found: {path}")

        data_points = []
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 3:
                    data_points.append(DESIDataPoint(
                        z=float(parts[0]),
                        value=float(parts[1]),
                        quantity=parts[2],
                    ))

        self._data_points = data_points
        self._data_mean = np.array([dp.value for dp in data_points])
        self._ndof = len(data_points)
        logger.info(f"Loaded {self._ndof} DESI DR1 BAO data points from {path}")

    def _load_covariance(self, path: Path) -> None:
        """Parse the DESI BAO covariance matrix and pre-compute Cholesky."""
        if not path.exists():
            raise FileNotFoundError(f"DESI covariance file not found: {path}")

        self._cov = np.loadtxt(str(path))

        if self._cov.shape != (self._ndof, self._ndof):
            raise ValueError(
                f"Covariance shape {self._cov.shape} does not match "
                f"number of data points ({self._ndof})"
            )

        # Check symmetry
        if not np.allclose(self._cov, self._cov.T, atol=1e-12):
            logger.warning("Covariance matrix not symmetric — symmetrizing.")
            self._cov = 0.5 * (self._cov + self._cov.T)

        # Cholesky decomposition for stable inversion
        try:
            self._cov_chol = cho_factor(self._cov)
            sign, log_det = np.linalg.slogdet(self._cov)
            if sign <= 0:
                raise LinAlgError("Covariance matrix is not positive definite.")
            self._log_det_cov = log_det
        except LinAlgError as e:
            logger.error(f"Cholesky decomposition failed: {e}")
            logger.warning("Falling back to pseudo-inverse (results may be unreliable).")
            self._cov_chol = None
            eigenvals = np.linalg.eigvalsh(self._cov)
            self._log_det_cov = np.sum(np.log(np.maximum(eigenvals, 1e-30)))

        logger.info(
            f"Loaded {self._ndof}×{self._ndof} DESI covariance matrix from {path} "
            f"(log|C| = {self._log_det_cov:.4f})"
        )

    # ------------------------------------------------------------------
    # Model Predictions from K3×T² Phenotype
    # ------------------------------------------------------------------

    def predict_bao_distances(self, phenotype: Dict[str, float]) -> np.ndarray:
        """
        Predict BAO distance ratios from a K3×T² cosmological phenotype.

        Uses the Friedmann equations in a flat w₀CDM cosmology:
            H(z) = H₀ √[ Ωₘ(1+z)³ + (1−Ωₘ)(1+z)^{3(1+w₀)} ]

        Maps to:
            D_M(z) / r_d   — comoving angular diameter distance / sound horizon
            D_H(z) / r_d   — Hubble distance / sound horizon
            D_V(z) / r_d   — volume-averaged distance / sound horizon
        """
        w0 = phenotype.get("w0", -1.0)
        omega_m = phenotype.get("omega_m", 0.30)
        h0 = phenotype.get("h0", 67.4)

        predictions = np.zeros(self._ndof)

        for i, dp in enumerate(self._data_points):
            z = dp.z
            d_h = self._hubble_distance(z, h0, omega_m, w0)
            d_m = self._comoving_distance(z, h0, omega_m, w0)

            if dp.quantity == "DH_over_rs":
                predictions[i] = d_h / _RD_FIDUCIAL
            elif dp.quantity == "DM_over_rs":
                predictions[i] = d_m / _RD_FIDUCIAL
            elif dp.quantity == "DV_over_rs":
                d_v = (z * d_m**2 * d_h) ** (1.0 / 3.0)
                predictions[i] = d_v / _RD_FIDUCIAL
            else:
                logger.warning(f"Unknown quantity '{dp.quantity}' at z={z}")
                predictions[i] = dp.value  # Fallback: no contribution to χ²

        return predictions

    @staticmethod
    def _hubble_distance(z: float, h0: float, omega_m: float, w0: float) -> float:
        """D_H(z) = c / H(z) in Mpc."""
        omega_de = 1.0 - omega_m
        ez_sq = omega_m * (1 + z) ** 3 + omega_de * (1 + z) ** (3 * (1 + w0))
        if ez_sq <= 0:
            return 1e10  # Penalize unphysical cosmologies
        hz = h0 * math.sqrt(ez_sq)
        return _C_KM_S / hz

    @staticmethod
    def _comoving_distance(
        z: float, h0: float, omega_m: float, w0: float, n_steps: int = 200
    ) -> float:
        """
        D_M(z) = ∫₀ᶻ c/H(z') dz' via trapezoidal integration (flat universe).
        """
        omega_de = 1.0 - omega_m
        zz = np.linspace(0, z, n_steps + 1)
        dz = z / n_steps

        integrand = np.zeros(n_steps + 1)
        for j, zi in enumerate(zz):
            ez_sq = omega_m * (1 + zi) ** 3 + omega_de * (1 + zi) ** (3 * (1 + w0))
            if ez_sq > 0:
                integrand[j] = 1.0 / math.sqrt(ez_sq)
            else:
                integrand[j] = 0.0

        # Trapezoidal rule
        integral = np.trapezoid(integrand, dx=dz)
        return (_C_KM_S / h0) * integral

    # ------------------------------------------------------------------
    # Likelihood Evaluation
    # ------------------------------------------------------------------

    def nanograv_log_likelihood(self, phenotype: Dict[str, float]) -> Tuple[float, float]:
        """
        Evaluate the NanoGrav 15yr free spectrum likelihood.
        Simulates the cross-correlation constraint for the PTA frequency spectrum.
        """
        # A simple mock of the NanoGrav 15yr spectral shape likelihood
        # Actual constraint fits f_monopole ~ 1e-9 Hz with spectral index gamma ~ 13/3
        f_mono = phenotype.get("pta_f_monopole", 1e-9)
        
        # Penalize deviation from 1.0e-9 Hz and require spectral shape consistency
        target_f = 1.0e-9
        sigma_f = 1.0e-10
        
        chi2_pta = ((f_mono - target_f) / sigma_f) ** 2
        log_l_pta = -0.5 * chi2_pta - 0.5 * math.log(2 * math.pi * sigma_f**2)
        
        return log_l_pta, chi2_pta

    def euclid_log_likelihood(self, phenotype: Dict[str, float]) -> Tuple[float, float]:
        """
        Evaluate the Euclid / KiDS Weak Lensing likelihood.
        Constrains the S_8 parameter (structure growth).
        """
        s8_model = phenotype.get("s8_gradient", 0.8)
        
        # Target S8 (e.g. Euclid DR1 / KiDS-1000 consensus)
        target_s8 = 0.766
        sigma_s8 = 0.014
        
        chi2_euclid = ((s8_model - target_s8) / sigma_s8) ** 2
        log_l_euclid = -0.5 * chi2_euclid - 0.5 * math.log(2 * math.pi * sigma_s8**2)
        
        return log_l_euclid, chi2_euclid

    def log_likelihood(self, phenotype: Dict[str, float]) -> DESILikelihoodResult:
        """
        Evaluate the combined multivariate Gaussian log-likelihood:
            log 𝓛 = log 𝓛_DESI + log 𝓛_NanoGrav + log 𝓛_Euclid
        """
        # DESI BAO log-likelihood
        model = self.predict_bao_distances(phenotype)
        delta = model - self._data_mean

        if self._cov_chol is not None:
            cinv_delta = cho_solve(self._cov_chol, delta)
        else:
            cinv = np.linalg.pinv(self._cov)
            cinv_delta = cinv @ delta

        chi2_desi = float(delta @ cinv_delta)
        log_norm = -0.5 * self._ndof * math.log(2 * math.pi) - 0.5 * self._log_det_cov
        log_l_desi = -0.5 * chi2_desi + log_norm
        
        # NanoGrav 15yr log-likelihood
        log_l_pta, chi2_pta = self.nanograv_log_likelihood(phenotype)
        
        # Euclid Weak Lensing log-likelihood
        log_l_euclid, chi2_euclid = self.euclid_log_likelihood(phenotype)
        
        total_log_l = log_l_desi + log_l_pta + log_l_euclid
        total_chi2 = chi2_desi + chi2_pta + chi2_euclid

        return DESILikelihoodResult(
            log_likelihood=total_log_l,
            chi2=total_chi2,
            ndof=self._ndof + 2,  # Added PTA and Euclid constraint DOFs
            residuals=delta,
            model_predictions=model,
        )

    @property
    def data_points(self) -> List[DESIDataPoint]:
        return list(self._data_points)

    @property
    def ndof(self) -> int:
        return self._ndof
