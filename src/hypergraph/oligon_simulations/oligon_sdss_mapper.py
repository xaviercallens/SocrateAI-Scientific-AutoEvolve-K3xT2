import torch
import numpy as np
from typing import Dict, Any, Optional
from data_benchmarks.sdss_loader import SDSSDataLoader
from hypergraph.continuum_limits.power_spectrum import compute_hypergraph_power_spectrum


class OligonSDSSMapper:
    """Maps Oligon hypergraph tangle structures to SDSS galaxy cluster halo catalogs."""

    def __init__(self, data_loader: Optional[SDSSDataLoader] = None):
        """Initializes the Oligon SDSS Mapper.

        Args:
            data_loader (SDSSDataLoader, optional): SDSS data loader instance. Defaults to None.
        """
        self.loader = data_loader or SDSSDataLoader()

    def map_tangle_to_halos(self, adj_matrix: torch.Tensor) -> Dict[str, Any]:
        """Maps adjacency matrix node densities to SDSS galaxy halo mass spectrum.

        Args:
            adj_matrix (torch.Tensor): Adjacency matrix tensor.

        Returns:
            Dict[str, Any]: Dictionary containing power spectrum and halo mass statistics.
        """
        k_vals, P_k = compute_hypergraph_power_spectrum(adj_matrix)
        halo_masses = self.loader.load_sdss_halo_masses("sample.fits")

        return {
            "power_spectrum_k": k_vals,
            "power_spectrum_Pk": P_k,
            "mean_halo_mass": float(np.mean(halo_masses)),
            "status": "MAPPED",
        }
