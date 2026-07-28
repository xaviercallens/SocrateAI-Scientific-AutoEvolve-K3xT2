"""
Unified Data Preprocessor for AlphaEvolve-K3-T2 (PL-02)
=========================================================
Standardized preprocessing for SDSS DR17, Euclid DR1, PTA (NANOGrav),
and JWST UNCOVER datasets. Outputs Parquet files with consistent schemas.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DataPreprocessor:
    """Preprocess all AlphaEvolve-K3-T2 observational datasets."""

    def __init__(self, data_dir: Union[str, Path] = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # SDSS DR17                                                            #
    # ------------------------------------------------------------------ #
    def preprocess_sdss(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
    ) -> pd.DataFrame:
        input_path = Path(input_path)
        try:
            from astropy.io import fits
            from astropy.table import Table
            with fits.open(input_path) as hdul:
                data = Table(hdul[1].data).to_pandas()
        except Exception:
            data = pd.read_csv(input_path)

        rename = {"RA": "ra", "DEC": "dec", "Z": "redshift", "MAG": "magnitude", "MAG_ERR": "magnitude_error"}
        data = data.rename(columns={k: v for k, v in rename.items() if k in data.columns})
        if "magnitude" in data.columns:
            data["luminosity"] = 10 ** (-0.4 * data["magnitude"])
        data = data.dropna(subset=["ra", "dec", "redshift"] if "redshift" in data.columns else ["ra", "dec"])
        if "redshift" in data.columns:
            data = data[(data["redshift"] > 0) & (data["redshift"] < 10)]
        return self._save(data, output_path, "SDSS")

    # ------------------------------------------------------------------ #
    # Euclid DR1                                                           #
    # ------------------------------------------------------------------ #
    def preprocess_euclid(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
    ) -> pd.DataFrame:
        input_path = Path(input_path)
        try:
            from astropy.io import fits
            from astropy.table import Table
            with fits.open(input_path) as hdul:
                data = Table(hdul[1].data).to_pandas()
        except Exception:
            data = pd.read_csv(input_path)

        rename = {"ALPHA": "ra", "DELTA": "dec", "Z": "redshift", "G_MAG": "magnitude", "G_MAG_ERR": "magnitude_error"}
        data = data.rename(columns={k: v for k, v in rename.items() if k in data.columns})
        if "magnitude" in data.columns:
            data["luminosity"] = 10 ** (-0.4 * data["magnitude"])
        data = data.dropna(subset=["ra", "dec"] if "ra" in data.columns else [])
        if "redshift" in data.columns:
            data = data[(data["redshift"] > 0) & (data["redshift"] < 10)]
        return self._save(data, output_path, "Euclid")

    # ------------------------------------------------------------------ #
    # PTA (NANOGrav / PPTA / EPTA)                                         #
    # ------------------------------------------------------------------ #
    def preprocess_pta(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
    ) -> pd.DataFrame:
        data = pd.read_csv(input_path)
        rename = {"MJD": "mjd", "TOA": "toa", "TOA_ERR": "toa_error", "FREQ": "frequency", "AMP": "amplitude"}
        data = data.rename(columns={k: v for k, v in rename.items() if k in data.columns})
        if "mjd" in data.columns:
            data["time"] = pd.to_datetime(data["mjd"], origin="1858-11-17", unit="D", errors="coerce")
        data = data.dropna(subset=["mjd"] if "mjd" in data.columns else [])
        if "frequency" in data.columns:
            data = data[(data["frequency"] > 0) & (data["frequency"] < 1e-6)]
        return self._save(data, output_path, "PTA")

    # ------------------------------------------------------------------ #
    # JWST UNCOVER                                                          #
    # ------------------------------------------------------------------ #
    def preprocess_jwst(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
    ) -> pd.DataFrame:
        data = pd.read_csv(input_path)
        rename = {"ID": "id", "RA": "ra", "DEC": "dec", "Z": "redshift", "MASS": "mass", "MASS_ERR": "mass_error"}
        data = data.rename(columns={k: v for k, v in rename.items() if k in data.columns})
        if "mass" in data.columns:
            data["luminosity"] = data["mass"] * 1e6
        data = data.dropna(subset=["ra", "dec"] if "ra" in data.columns else [])
        if "redshift" in data.columns:
            data = data[(data["redshift"] > 8) & (data["redshift"] < 10)]
        return self._save(data, output_path, "JWST")

    # ------------------------------------------------------------------ #
    # Batch                                                                 #
    # ------------------------------------------------------------------ #
    def preprocess_all(self) -> Dict[str, pd.DataFrame]:
        results: Dict[str, pd.DataFrame] = {}
        mapping = {
            "sdss":   (self.data_dir / "sdss"  / "galaxy_dr17.fits",   self.data_dir / "sdss"  / "galaxy_dr17_preprocessed.parquet",  self.preprocess_sdss),
            "euclid": (self.data_dir / "euclid" / "euclid_dr1.fits",    self.data_dir / "euclid" / "euclid_dr1_preprocessed.parquet",   self.preprocess_euclid),
            "pta":    (self.data_dir / "pta"    / "nanograv_data.csv",  self.data_dir / "pta"    / "nanograv_data_preprocessed.parquet", self.preprocess_pta),
            "jwst":   (self.data_dir / "jwst"   / "uncover_catalog.csv",self.data_dir / "jwst"   / "uncover_catalog_preprocessed.parquet",self.preprocess_jwst),
        }
        for name, (inp, out, fn) in mapping.items():
            if inp.exists():
                results[name] = fn(inp, out)
            else:
                logger.warning(f"{name.upper()} input not found, skipping: {inp}")
        return results

    # ------------------------------------------------------------------ #
    # Internal                                                              #
    # ------------------------------------------------------------------ #
    def _save(self, df: pd.DataFrame, output_path, label: str) -> pd.DataFrame:
        if output_path is not None:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(out, index=False)
            logger.info(f"Preprocessed {label} data saved to {out} ({len(df)} rows)")
        return df
