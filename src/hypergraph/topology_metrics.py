import torch
from typing import Dict, Any


def extract_spectral_gap(adj_matrix: torch.Tensor,
                         k: int = 8) -> Dict[str, Any]:
    """Extracts top-k eigenvalues and computes the spectral gap delta_lambda.

    Args:
        adj_matrix (torch.Tensor): Sparse or dense adjacency matrix tensor.
        k (int, optional): Number of top eigenvalues to extract. Defaults to 8.

    Returns:
        Dict[str, Any]: Dictionary containing top eigenvalues and spectral gap metrics.
    """
    dense = adj_matrix.to_dense() if adj_matrix.is_sparse else adj_matrix

    # Compute real symmetric eigenvalues
    eigenvalues = torch.linalg.eigvalsh(dense)
    sorted_evals, _ = torch.sort(eigenvalues, descending=True)

    top_k = sorted_evals[:k].tolist()
    lambda_1 = top_k[0] if len(top_k) > 0 else 0.0
    lambda_2 = top_k[1] if len(top_k) > 1 else 0.0

    return {
        "top_eigenvalues": top_k,
        "lambda_1": lambda_1,
        "lambda_2": lambda_2,
        "spectral_gap": lambda_1 - lambda_2,
    }
