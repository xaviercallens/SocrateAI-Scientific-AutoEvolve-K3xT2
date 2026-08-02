import torch
import numpy as np
from typing import Tuple


def compute_hypergraph_power_spectrum(
        adj_matrix: torch.Tensor, num_bins: int = 50) -> Tuple[np.ndarray, np.ndarray]:
    """Computes emergent matter power spectrum P(k) from hypergraph node density.

    Args:
        adj_matrix (torch.Tensor): Sparse or dense adjacency matrix tensor.
        num_bins (int, optional): Number of wavenumber bins to return. Defaults to 50.

    Returns:
        Tuple[np.ndarray, np.ndarray]: Tuple of (k_vals, P_vals) numpy arrays.
    """
    dense = adj_matrix.to_dense() if adj_matrix.is_sparse else adj_matrix
    node_density = torch.sum(dense, dim=1).cpu().numpy()

    # Compute 1D FFT as simplified 1D power spectrum representation
    fft_vals = np.abs(np.fft.rfft(node_density)) ** 2
    k_vals = np.fft.rfftfreq(len(node_density))

    return k_vals[:num_bins], fft_vals[:num_bins]
