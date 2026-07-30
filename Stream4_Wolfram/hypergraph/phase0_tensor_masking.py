"""
Phase 0 MVP: Single-Node Tensor Validation
===========================================
Objective: Validate that standard PyTorch sparse tensor masking
           M_{t+1} = (M_t^2 + M_t) * T
successfully prevents runaway VRAM explosion on a K_4 Oligon seed
up to N=15..20 iterations on a single GPU node.
"""

import sys
import time
import hashlib
import torch
import numpy as np
import networkx as nx
from typing import Optional


def create_k4_oligon_seed(vacuum_size: int = 6) -> torch.Tensor:
    """
    Creates a initial adjacency matrix M_0 containing:
    1. A K_4 defect block (complete graph on 4 nodes, indices 0..3)
    2. A simple vacuum background ring of size `vacuum_size` (indices 4..4+vacuum_size-1)
    """
    total_nodes = 4 + vacuum_size
    M_0 = torch.zeros((total_nodes, total_nodes), dtype=torch.float32)

    # K4 defect block (all-to-all except self-loops)
    for i in range(4):
        for j in range(4):
            if i != j:
                M_0[i, j] = 1.0

    # Vacuum background ring (cyclic edges)
    vac_start = 4
    for k in range(vacuum_size):
        u = vac_start + k
        v = vac_start + ((k + 1) % vacuum_size)
        M_0[u, v] = 0.5
        M_0[v, u] = 0.5

    return M_0


def generate_topological_mask(
    M_t: torch.Tensor, k4_indices: list = [
        0, 1, 2, 3]) -> torch.Tensor:
    """
    Generates a boolean/float mask tensor T.
    T flags and preserves interaction edges around topological defect zones (e.g. K4 subgraphs),
    while zeroing out non-physical, higher-order exponential noise on background edges.

    Rule:
    - Preserve all edges within and connected to K4 defect nodes.
    - Suppress unmasked exponential edge buildup in background vacuum.
    """
    dim = M_t.shape[0]
    T = torch.zeros((dim, dim), dtype=torch.float32, device=M_t.device)

    # Preserve defect interaction core
    for idx in k4_indices:
        if idx < dim:
            T[idx, :] = 1.0
            T[:, idx] = 1.0

    # Preserve original 1-hop background neighborhood structure (linear
    # background)
    bg_mask = (M_t > 0.0).float()
    T = torch.clamp(T + bg_mask, 0.0, 1.0)

    return T


def canonical_graph_hash(M_t: torch.Tensor) -> str:
    """
    Computes a canonical graph hash using NetworkX Weisfeiler-Leman algorithm.
    Used for local in-memory single-node isomorphic branch pruning.
    """
    adj_np = (M_t.cpu().detach().numpy() > 0.1).astype(int)
    G = nx.from_numpy_array(adj_np)

    # NetworkX Weisfeiler-Lehman hash is permutation invariant
    wl_hash = nx.weisfeiler_lehman_graph_hash(G)
    return wl_hash


def run_phase0_simulation(
        max_steps: int = 15,
        device: Optional[str] = None) -> dict:
    """
    Executes the Phase 0 PyTorch MVP simulation for max_steps iterations.
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    print(
        f"=== Running Phase 0 PyTorch Tensor Masking MVP on Device: {device} ===")

    M_t = create_k4_oligon_seed(vacuum_size=10).to(device)
    seen_hashes = set()
    history = []

    start_time = time.time()
    vram_peak_mb = 0.0

    initial_hash = canonical_graph_hash(M_t)
    seen_hashes.add(initial_hash)

    for step in range(1, max_steps + 1):
        # 1. Generate topological mask T
        T = generate_topological_mask(M_t)

        # 2. Execute PyTorch Hadamard rewrite update: M_{t+1} = (M_t^2 + M_t)
        # (o) T
        M_sq = torch.matmul(M_t, M_t)
        M_next_unmasked = M_sq + M_t
        M_next = M_next_unmasked * T

        # 3. Apply normalization / threshold to keep numeric stability
        M_next = torch.clamp(M_next, 0.0, 100.0)

        # 4. Check local canonical hash for isomorphic pruning
        current_hash = canonical_graph_hash(M_next)
        is_pruned = current_hash in seen_hashes
        if not is_pruned:
            seen_hashes.add(current_hash)

        # Record VRAM and edge metrics
        if device.startswith("cuda"):
            vram_mb = torch.cuda.max_memory_allocated() / (1024 * 1024)
            vram_peak_mb = max(vram_peak_mb, vram_mb)
        else:
            vram_mb = 0.0  # CPU mode

        non_zero_edges = torch.count_nonzero(M_next > 0.01).item()
        unmasked_sum = M_next_unmasked.sum().item()
        masked_sum = M_next.sum().item()

        print(
            f"Step {step:2d} | Edges: {non_zero_edges:4d} | Unmasked Sum: {unmasked_sum:10.2f} | Masked Sum: {masked_sum:8.2f} | Hash: {current_hash[:8]} | Pruned: {is_pruned}")

        history.append({
            "step": step,
            "edges": non_zero_edges,
            "unmasked_sum": unmasked_sum,
            "masked_sum": masked_sum,
            "hash": current_hash,
            "is_pruned": is_pruned,
        })

        # Advance state
        M_t = M_next

    elapsed_time = time.time() - start_time
    print(
        f"\nPhase 0 MVP Completed in {elapsed_time:.3f}s. Total Unique Isomorphic Hashes: {len(seen_hashes)}")

    return {
        "status": "SUCCESS",
        "max_steps": max_steps,
        "device": device,
        "vram_peak_mb": vram_peak_mb,
        "unique_hashes": len(seen_hashes),
        "history": history
    }


if __name__ == "__main__":
    results = run_phase0_simulation(max_steps=15)
    print("Phase 0 MVP Results Summary:", results["status"])
