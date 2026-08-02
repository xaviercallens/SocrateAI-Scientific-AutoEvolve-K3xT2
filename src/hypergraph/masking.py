import torch

def sparse_elementwise_mul(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """Hadamard (element-wise) multiplication via sparse COO index intersection.

    Computes C = A ⊙ B where both A and B are sparse COO tensors.
    Only indices present in BOTH tensors survive in the output, with
    values multiplied element-wise.

    For large N where dense fallback would OOM, this performs an
    efficient hash-join on the (row, col) index pairs.
    """
    if not a.is_sparse or not b.is_sparse:
        raise ValueError("Both a and b must be sparse tensors")

    a = a.coalesce()
    b = b.coalesce()

    N = a.shape[0]
    DENSE_THRESHOLD = 20_000  # Safe for 16 GB T4 VRAM (20k² × 4B ≈ 1.5 GB)

    if N <= DENSE_THRESHOLD:
        # Dense path: fast and numerically exact for moderate N
        return (a.to_dense() * b.to_dense()).to_sparse_coo().coalesce()

    # Sparse index intersection path for large N
    a_indices = a.indices()  # shape (2, nnz_a)
    a_values = a.values()
    b_indices = b.indices()  # shape (2, nnz_b)
    b_values = b.values()

    # Encode (row, col) pairs as single int64 keys for hash-based intersection
    a_keys = a_indices[0] * N + a_indices[1]
    b_keys = b_indices[0] * N + b_indices[1]

    # Build lookup from B keys to B values
    b_key_set, b_inverse = torch.unique(b_keys, return_inverse=True)

    # For each A key, check membership in B keys via searchsorted
    sorted_b_keys, sort_order = torch.sort(b_keys)
    sorted_b_values = b_values[sort_order]

    insert_positions = torch.searchsorted(sorted_b_keys, a_keys)
    # Clamp to valid range
    insert_positions = torch.clamp(insert_positions, 0, len(sorted_b_keys) - 1)
    # Check for exact match
    match_mask = sorted_b_keys[insert_positions] == a_keys

    if not match_mask.any():
        # No overlapping indices — return empty sparse tensor
        empty_idx = torch.zeros((2, 0), dtype=torch.long, device=a.device)
        empty_val = torch.zeros(0, dtype=a.dtype, device=a.device)
        return torch.sparse_coo_tensor(empty_idx, empty_val, a.shape, device=a.device).coalesce()

    # Extract matched entries and multiply values
    matched_a_indices = a_indices[:, match_mask]
    matched_a_values = a_values[match_mask]
    matched_b_values = sorted_b_values[insert_positions[match_mask]]

    result_values = matched_a_values * matched_b_values

    return torch.sparse_coo_tensor(
        matched_a_indices, result_values, a.shape, device=a.device
    ).coalesce()


def hypergraph_step(adj_matrix: torch.Tensor, mask_tensor: torch.Tensor) -> torch.Tensor:
    """Performs masked matrix multiplication update step.
    
    Computes M_{t+1} = (M_t^2 + M_t) ⊙ T
    
    Args:
        adj_matrix (torch.Tensor): Current adjacency matrix (sparse or dense).
        mask_tensor (torch.Tensor): Mask tensor T to constrain the update (sparse or dense).
        
    Returns:
        torch.Tensor: Updated sparse adjacency matrix.
    """
    if adj_matrix.is_sparse and mask_tensor.is_sparse:
        # Fully sparse path
        adj_coalesced = adj_matrix.coalesce()
        # Sparse matrix multiplication for M^2
        m_squared = torch.sparse.mm(adj_coalesced, adj_coalesced)
        # unconstrained = M^2 + M
        unconstrained = m_squared + adj_coalesced
        
        # Apply mask
        return sparse_elementwise_mul(unconstrained, mask_tensor)
    else:
        # Mixed or dense path
        adj_dense = adj_matrix.to_dense() if adj_matrix.is_sparse else adj_matrix
        m_squared = torch.matmul(adj_dense, adj_dense)
        unconstrained = m_squared + adj_dense
        mask_dense = mask_tensor.to_dense() if mask_tensor.is_sparse else mask_tensor
        masked_dense = unconstrained * mask_dense
        return masked_dense.to_sparse().coalesce()
