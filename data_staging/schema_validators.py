"""
Pydantic Schema Validators for Data Lake Tensors and Catalogs
=============================================================
Enforces structural integrity and scientific validity of cosmological datasets
ingested into the SocrateAI data lake before AlphaEvolve MCMC processing.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator
import numpy as np

class BAODataPoint(BaseModel):
    z_eff: float = Field(..., ge=0.0, le=5.0, description="Effective redshift of the BAO measurement")
    D_v_over_r_d: float = Field(..., gt=0.0, description="Volume averaged distance D_V(z) / r_d")
    error: float = Field(..., gt=0.0, description="1-sigma uncertainty")
    survey: str = Field(..., description="Survey name (e.g., DESI, SDSS, BOSS)")

class DESILikelihoodSchema(BaseModel):
    dataset_version: str = Field(..., description="e.g., DR1, Y1")
    data_points: List[BAODataPoint]
    covariance_matrix: Optional[List[List[float]]] = None

    @field_validator('covariance_matrix')
    @classmethod
    def validate_cov_matrix(cls, v, info):
        if v is not None:
            n = len(info.data.get('data_points', []))
            if len(v) != n or any(len(row) != n for row in v):
                raise ValueError(f"Covariance matrix must be {n}x{n}")
        return v


class EuclidGalaxy(BaseModel):
    ra: float = Field(..., ge=0.0, le=360.0, description="Right ascension (degrees)")
    dec: float = Field(..., ge=-90.0, le=90.0, description="Declination (degrees)")
    z_phot: float = Field(..., ge=0.0, le=10.0, description="Photometric redshift")
    z_phot_err: float = Field(..., ge=0.0, description="Uncertainty in photometric redshift")
    mag_vis: float = Field(..., ge=10.0, le=30.0, description="Apparent magnitude in VIS band")
    shear_1: float = Field(..., ge=-1.0, le=1.0, description="Weak lensing shear component 1")
    shear_2: float = Field(..., ge=-1.0, le=1.0, description="Weak lensing shear component 2")
    weight: float = Field(1.0, ge=0.0, description="Statistical weight")


class EuclidCatalogSchema(BaseModel):
    catalog_id: str
    field_name: str = Field(..., description="e.g., EDFS, EDFN, EDF-F")
    total_objects: int = Field(..., gt=0)
    # Validating large lists of galaxies in pure python can be slow, 
    # but we can optionally sample or validate aggregated metadata.
    metadata: Dict[str, Any]


class TensorMetadataSchema(BaseModel):
    tensor_name: str
    shape: List[int]
    dtype: str
    is_sparse: bool = False
    description: str

    @field_validator('dtype')
    @classmethod
    def validate_dtype(cls, v):
        allowed = ["float32", "float64", "int32", "int64", "complex64", "complex128"]
        if v not in allowed:
            raise ValueError(f"Unsupported dtype: {v}")
        return v
