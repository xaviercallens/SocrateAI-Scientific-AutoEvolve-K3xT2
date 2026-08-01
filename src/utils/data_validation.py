"""
Data Validation Schemas
=======================
Implements rigorous Pydantic schemas for validating JSON checkpoints,
candidate phenotypes, and Euclid/DESI observational datasets to prevent
silent data corruption.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator

class PhenotypeSchema(BaseModel):
    w0: float = Field(..., description="Dark energy equation of state parameter")
    omega_m: float = Field(..., description="Matter density parameter", ge=0.1, le=0.5)
    h0: float = Field(..., description="Hubble constant", ge=50.0, le=100.0)
    pta_f_monopole: float = Field(..., description="PTA monopole frequency")
    s8_gradient: float = Field(..., description="Structure growth parameter")
    pta_anisotropy: Optional[float] = Field(None, description="PTA anisotropy power")
    lya_spectral_tilt: Optional[float] = Field(None, description="Lyman-alpha spectral tilt")
    gw_polarisation: Optional[float] = Field(None, description="Gravitational wave polarization fraction")
    cs_magnitude: Optional[float] = Field(None, description="Complex structure magnitude")
    cs_theta_rad: Optional[float] = Field(None, description="Complex structure angle theta")
    cs_phi_rad: Optional[float] = Field(None, description="Complex structure angle phi")

class LikelihoodSchema(BaseModel):
    chi2: float = Field(..., description="Total chi-squared")
    fitness: float = Field(..., description="Overall fitness score (0 to 1)", ge=0.0, le=1.0)
    chi2_w0: float
    chi2_om: float
    chi2_h0: float

class CandidateSchema(BaseModel):
    name: str
    picard_fuchs_coefficients: List[float]
    hodge_numbers: Dict[str, int]
    kodaira_fiber_type: str
    complex_structure_tau: List[float]
    kahler_modulus_rho: List[float]
    candidate_id: str
    picard_number: float = Field(..., ge=1.0, le=20.0)
    moduli_stabilization: float
    complex_structure: List[float]
    t2_modulus_tau: float
    formal_reason: str
    phenotype: PhenotypeSchema
    likelihood: LikelihoodSchema
    chi2_loss: float
    gcs_stream_uri: Optional[str] = None

class EvolutionaryCheckpointSchema(BaseModel):
    run_id: str
    generation: int = Field(..., ge=1)
    best_candidate: CandidateSchema
    population: List[CandidateSchema]
    
    @field_validator("population")
    @classmethod
    def check_population_not_empty(cls, v):
        if len(v) == 0:
            raise ValueError("Population must not be empty.")
        return v

def validate_checkpoint_file(filepath: str) -> EvolutionaryCheckpointSchema:
    """Validates a JSON checkpoint file using Pydantic."""
    import json
    with open(filepath, 'r') as f:
        data = json.load(f)
    return EvolutionaryCheckpointSchema(**data)
