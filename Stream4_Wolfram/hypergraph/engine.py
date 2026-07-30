import torch
from typing import Dict, Any, Tuple, Optional


class HypergraphEngine:
    """Core PyTorch sparse tensor engine for hypergraph updates."""

    def __init__(self, device: Optional[str] = None):
        """Initializes the engine with the target compute device.

        Args:
            device (str, optional): Target device ('cuda' or 'cpu'). Defaults to auto-detect.
        """
        self.device = device or (
            "cuda" if torch.cuda.is_available() else "cpu")

    def create_k4_seed(self, vacuum_nodes: int = 11) -> torch.Tensor:
        """Constructs initial sparse COO adjacency matrix with K4 defect and vacuum ring.

        Args:
            vacuum_nodes (int): Number of nodes in the vacuum ring.

        Returns:
            torch.Tensor: The initialized sparse adjacency matrix.
        """
        # K4 seed (nodes 0..3) with weight 1.0, Vacuum ring (nodes 4..N) with
        # weight 0.5
        total_nodes = 4 + vacuum_nodes
        indices, values = [], []

        # K4 Complete Graph
        for i in range(4):
            for j in range(4):
                if i != j:
                    indices.append([i, j])
                    values.append(1.0)

        # Vacuum Lattice Ring
        for i in range(4, total_nodes):
            next_node = 4 + ((i - 4 + 1) % vacuum_nodes)
            indices.append([i, next_node])
            values.append(0.5)
            indices.append([next_node, i])
            values.append(0.5)

        idx_t = torch.tensor(indices, dtype=torch.long, device=self.device).t()
        val_t = torch.tensor(values, dtype=torch.float32, device=self.device)
        return torch.sparse_coo_tensor(
            idx_t, val_t, (total_nodes, total_nodes)).coalesce()

    def step(self, adj_matrix: torch.Tensor,
             mask_tensor: torch.Tensor) -> torch.Tensor:
        """Performs masked matrix multiplication update step.

        Args:
            adj_matrix (torch.Tensor): Current adjacency matrix.
            mask_tensor (torch.Tensor): Mask tensor to constrain the update.

        Returns:
            torch.Tensor: Updated sparse adjacency matrix.
        """
        adj_dense = adj_matrix.to_dense() if adj_matrix.is_sparse else adj_matrix
        m_squared = torch.matmul(adj_dense, adj_dense)
        unconstrained = m_squared + adj_dense
        masked_dense = unconstrained * \
            mask_tensor.to_dense() if mask_tensor.is_sparse else unconstrained * mask_tensor
        return masked_dense.to_sparse().coalesce()
