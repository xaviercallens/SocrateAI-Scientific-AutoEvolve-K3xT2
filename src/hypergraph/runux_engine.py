import torch


class RunuxSparseEngine:
    """Sparse COO tensor engine optimized for high-node hypergraphs."""

    @staticmethod
    def sparse_masked_step(
            adj_sparse: torch.Tensor,
            mask_sparse: torch.Tensor) -> torch.Tensor:
        """Executes M_{t+1} = (M_t^2 + M_t) * T strictly in sparse memory."""
        from hypergraph.masking import hypergraph_step
        return hypergraph_step(adj_sparse, mask_sparse)

    @staticmethod
    def _sparse_elementwise_mul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
        """Hadamard (element-wise) multiplication via sparse COO index intersection."""
        from hypergraph.masking import sparse_elementwise_mul
        return sparse_elementwise_mul(a, b)
