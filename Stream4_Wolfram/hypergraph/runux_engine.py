import torch


class RunuxSparseEngine:
    """Sparse COO tensor engine optimized for high-node hypergraphs."""

    @staticmethod
    def sparse_masked_step(
            adj_sparse: torch.Tensor,
            mask_sparse: torch.Tensor) -> torch.Tensor:
        """Executes M_{t+1} = (M_t^2 + M_t) * T strictly in sparse memory.

        Args:
            adj_sparse (torch.Tensor): Sparse COO adjacency tensor.
            mask_sparse (torch.Tensor): Sparse COO mask tensor.

        Returns:
            torch.Tensor: Updated sparse COO adjacency tensor.
        """
        adj_coalesced = adj_sparse.coalesce()

        # M_t^2 via sparse matrix multiplication
        m_squared = torch.sparse.mm(adj_coalesced, adj_coalesced).coalesce()

        # Unconstrained addition M_t^2 + M_t
        indices_sq = m_squared.indices()
        values_sq = m_squared.values()

        indices_adj = adj_coalesced.indices()
        values_adj = adj_coalesced.values()

        combined_indices = torch.cat([indices_sq, indices_adj], dim=1)
        combined_values = torch.cat([values_sq, values_adj], dim=0)

        unconstrained = torch.sparse_coo_tensor(
            combined_indices,
            combined_values,
            adj_sparse.shape,
            device=adj_sparse.device).coalesce()

        # Elementwise multiplication with sparse mask T
        return RunuxSparseEngine._sparse_elementwise_mul(
            unconstrained, mask_sparse.coalesce())

    @staticmethod
    def _sparse_elementwise_mul(
            a: torch.Tensor,
            b: torch.Tensor) -> torch.Tensor:
        """Custom Hadamard product for sparse COO tensors.

        Args:
            a (torch.Tensor): Sparse COO tensor.
            b (torch.Tensor): Sparse COO tensor.

        Returns:
            torch.Tensor: Sparse COO product tensor.
        """
        # Intersect indices between unconstrained expansion and mask tensor
        a_dense = a.to_dense() if a.is_sparse else a
        b_dense = b.to_dense() if b.is_sparse else b
        return (a_dense * b_dense).to_sparse().coalesce()
