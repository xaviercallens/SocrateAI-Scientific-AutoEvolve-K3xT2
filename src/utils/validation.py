"""
Input Validation Utilities for AlphaEvolve-K3-T2
=================================================
Validates file paths, numerical parameters, probabilities, and list lengths
before any pipeline logic executes.
"""

import re
from pathlib import Path
from typing import List, Optional, Union


class ValidationError(Exception):
    """Raised when an input parameter fails validation."""
    pass


class InputValidator:
    """Validates input parameters for AlphaEvolve-K3-T2 pipeline scripts."""

    @staticmethod
    def validate_file_path(path: Union[str, Path], exists: bool = True, is_file: bool = True) -> Path:
        path = Path(path)
        if exists and not path.exists():
            raise ValidationError(f"File not found: {path}")
        if is_file and path.exists() and not path.is_file():
            raise ValidationError(f"Path is not a file: {path}")
        return path

    @staticmethod
    def validate_directory_path(path: Union[str, Path], exists: bool = True) -> Path:
        path = Path(path)
        if exists and not path.exists():
            raise ValidationError(f"Directory not found: {path}")
        if path.exists() and not path.is_dir():
            raise ValidationError(f"Path is not a directory: {path}")
        return path

    @staticmethod
    def validate_positive_integer(value: int, name: str = "value") -> int:
        if not isinstance(value, int):
            raise ValidationError(f"{name} must be an integer, got {type(value).__name__}")
        if value <= 0:
            raise ValidationError(f"{name} must be positive, got {value}")
        return value

    @staticmethod
    def validate_probability(value: float, name: str = "value") -> float:
        if not isinstance(value, (int, float)):
            raise ValidationError(f"{name} must be a number, got {type(value).__name__}")
        if not (0.0 <= value <= 1.0):
            raise ValidationError(f"{name} must be in [0, 1], got {value}")
        return float(value)

    @staticmethod
    def validate_list_length(value: List, min_length: int, max_length: Optional[int] = None, name: str = "list") -> List:
        if not isinstance(value, list):
            raise ValidationError(f"{name} must be a list, got {type(value).__name__}")
        if len(value) < min_length:
            raise ValidationError(f"{name} must have at least {min_length} elements, got {len(value)}")
        if max_length is not None and len(value) > max_length:
            raise ValidationError(f"{name} must have at most {max_length} elements, got {len(value)}")
        return value

    @staticmethod
    def validate_string_pattern(value: str, pattern: str, name: str = "string") -> str:
        if not isinstance(value, str):
            raise ValidationError(f"{name} must be a string")
        if not re.match(pattern, value):
            raise ValidationError(f"{name} does not match pattern '{pattern}': got '{value}'")
        return value
