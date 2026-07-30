import hashlib
import torch
from typing import Optional, Set


class CanonicalLedger:
    """Manages isomorphic state pruning using canonical degree-sequence hashing."""

    def __init__(
            self,
            redis_host: Optional[str] = None,
            redis_port: int = 6379):
        """Initializes the CanonicalLedger with optional Redis backing.

        Args:
            redis_host (str, optional): Redis server hostname. Defaults to None.
            redis_port (int, optional): Redis server port. Defaults to 6379.
        """
        self.local_cache: Set[str] = set()
        self.redis = None
        if redis_host:
            import redis
            self.redis = redis.Redis(host=redis_host, port=redis_port, db=0)

    def compute_canonical_hash(self, adj_matrix: torch.Tensor) -> str:
        """Computes a node-permutation invariant hash of the adjacency matrix.

        Args:
            adj_matrix (torch.Tensor): Sparse or dense adjacency matrix tensor.

        Returns:
            str: SHA-256 canonical hash string.
        """
        dense = adj_matrix.to_dense() if adj_matrix.is_sparse else adj_matrix
        # Sort rows and columns by node degree to generate canonical order
        degrees = torch.sum(dense > 0, dim=1)
        sorted_indices = torch.argsort(degrees, descending=True)
        canonical_matrix = dense[sorted_indices][:, sorted_indices]

        matrix_bytes = canonical_matrix.cpu().numpy().tobytes()
        return hashlib.sha256(matrix_bytes).hexdigest()

    def register_and_check_prune(self, state_hash: str) -> bool:
        """Checks if a state has been seen and registers it.

        Args:
            state_hash (str): The state hash string.

        Returns:
            bool: True if state was already registered (should be pruned), else False.
        """
        if self.redis:
            is_new = self.redis.sadd("hypergraph:canonical_hashes", state_hash)
            return is_new == 0
        else:
            if state_hash in self.local_cache:
                return True
            self.local_cache.add(state_hash)
            return False
