"""
Astrophysics Validator for AlphaEvolve-K3-T2
=============================================
Validates evolved K3×T² geometries against empirical astrophysics thresholds:
  - Weak Lensing discriminant Δ_obs
  - PTA scalar monopole frequency & amplitude
  - Chameleon mechanism α_eff (M87* superradiance evasion)
  - GD-1 stream heating bounds
  - Core-Cusp tension resolution
  - Euclid S_8 gradient
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List


@dataclass
class AstrophysicsCriteria:
    # Weak Lensing (required)
    delta_obs: float

    # PTA scalar monopole
    pta_frequency: Optional[float] = None   # Hz (target ~1e-8)
    pta_amplitude: Optional[float] = None   # dimensionless (target ~1e-15)

    # Chameleon mechanism
    alpha_eff: Optional[float] = None       # must be > 0.45

    # GD-1 stream
    gd1_heating_bounds: Optional[Dict[str, float]] = None

    # Core-Cusp
    core_cusp_tension: Optional[float] = None

    # Euclid S_8 gradient
    s8_gradient: Optional[float] = None     # target 0.83


class AstrophysicsValidator:
    """Validates K3×T² phenotype against astrophysics empirical thresholds."""

    @staticmethod
    def validate_weak_lensing(delta_obs: float) -> bool:
        """Δ < 1.0 (smooth), 1–10 (moderate), ≥ 10 (extreme / 7-brane intersection)."""
        return delta_obs >= 0.0

    @staticmethod
    def validate_pta(frequency: float, amplitude: float) -> bool:
        """PTA scalar monopole must be within 10% of NANOGrav nanohertz target."""
        target_freq = 1e-8
        target_amp  = 1e-15
        freq_ok = abs(frequency - target_freq) / target_freq < 0.10
        amp_ok  = abs(amplitude  - target_amp)  / target_amp  < 0.10
        return freq_ok and amp_ok

    @staticmethod
    def validate_chameleon(alpha_eff: float) -> bool:
        """α_eff > 0.45 required for M87* superradiance evasion."""
        return alpha_eff > 0.45

    @staticmethod
    def validate_gd1(heating_bounds: Dict[str, float]) -> bool:
        """All GD-1 heating rates must be ≤ 0.1 (km/s)²/Myr."""
        return all(v <= 0.1 for v in heating_bounds.values())

    @staticmethod
    def validate_core_cusp(tension: float) -> bool:
        """Core-Cusp density slope tension must be < 0.05."""
        return tension < 0.05

    @staticmethod
    def validate_s8(s8_gradient: float) -> bool:
        """Euclid S_8 gradient must be within 2% of 0.83."""
        return abs(s8_gradient - 0.83) / 0.83 < 0.02

    def validate_all(self, criteria: AstrophysicsCriteria) -> Dict[str, bool]:
        """Run all applicable validators and return a result dict."""
        results: Dict[str, bool] = {}
        results["weak_lensing"] = self.validate_weak_lensing(criteria.delta_obs)

        if criteria.pta_frequency is not None and criteria.pta_amplitude is not None:
            results["pta"] = self.validate_pta(criteria.pta_frequency, criteria.pta_amplitude)

        if criteria.alpha_eff is not None:
            results["chameleon"] = self.validate_chameleon(criteria.alpha_eff)

        if criteria.gd1_heating_bounds is not None:
            results["gd1"] = self.validate_gd1(criteria.gd1_heating_bounds)

        if criteria.core_cusp_tension is not None:
            results["core_cusp"] = self.validate_core_cusp(criteria.core_cusp_tension)

        if criteria.s8_gradient is not None:
            results["s8_gradient"] = self.validate_s8(criteria.s8_gradient)

        return results
