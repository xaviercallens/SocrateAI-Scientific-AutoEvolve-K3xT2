"""
GD-1 Stream & Core-Cusp Tension Validators
==========================================
Provides empirical validation for:
  - GD-1 stellar stream heating bounds
  - Core-Cusp density slope tension resolution
"""


class GD1Validator:
    """Validates K3×T² predictions against GD-1 stream heating constraints."""

    TARGET_HEATING_RATE = 0.05   # (km/s)²/Myr (literature estimate)
    MAX_HEATING_RATE    = 0.10   # upper bound
    MAX_STREAM_LENGTH   = 10.0   # kpc

    @staticmethod
    def validate_gd1_stream(heating_rate: float, expected_length: float) -> bool:
        """
        Validate GD-1 stream against heating bounds.

        Args:
            heating_rate: Heating rate in (km/s)²/Myr.
            expected_length: Expected stream length in kpc.

        Returns:
            bool: True if within observational bounds.
        """
        if heating_rate > GD1Validator.MAX_HEATING_RATE:
            return False
        if expected_length > GD1Validator.MAX_STREAM_LENGTH:
            return False
        return True


class CoreCuspValidator:
    """Validates K3×T² predictions against Core-Cusp density slope observations."""

    TENSION_THRESHOLD = 0.05  # Maximum allowed slope discrepancy

    @staticmethod
    def validate_core_cusp(density_slope: float, expected_slope: float) -> bool:
        """
        Validate Core-Cusp tension resolution.

        Args:
            density_slope: Measured d log ρ / d log r.
            expected_slope: Predicted slope from N-body simulations.

        Returns:
            bool: True if tension is resolved (|Δslope| < threshold).
        """
        tension = abs(density_slope - expected_slope)
        return tension < CoreCuspValidator.TENSION_THRESHOLD


if __name__ == "__main__":
    gd1_valid = GD1Validator.validate_gd1_stream(heating_rate=0.05, expected_length=8.0)
    cc_valid  = CoreCuspValidator.validate_core_cusp(density_slope=-1.0, expected_slope=-1.2)
    print(f"GD-1 Validation:        {'PASS' if gd1_valid else 'FAIL'}")
    print(f"Core-Cusp Validation:   {'PASS' if cc_valid  else 'FAIL'}")
