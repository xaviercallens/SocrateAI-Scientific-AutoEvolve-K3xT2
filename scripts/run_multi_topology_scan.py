#!/usr/bin/env python3
"""
Multi-Topology Scan (Phase 5C-1)
================================
Explores alternative hypergraph seeds (K3, K5, K33, Petersen) to see
if they yield competitive K3 surfaces via the spectral bridge.
"""

import numpy as np
from scipy import linalg
import networkx as nx
import sys
import json
from pathlib import Path

# Ensure we can import from src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from stream4_bridge.deterministic_k3_generator import DeterministicK3Generator

def build_graph_with_vacuum(G: nx.Graph, vacuum_nodes: int = 11) -> np.ndarray:
    """Builds the adjacency matrix with a vacuum ring attached, same logic as K4."""
    core_nodes = len(G.nodes)
    total = core_nodes + vacuum_nodes
    M = np.zeros((total, total))
    
    # Core adjacency
    for u, v in G.edges:
        M[u, v] = 1.0
        M[v, u] = 1.0
        
    # Vacuum ring (nodes core_nodes to total-1)
    if vacuum_nodes > 0:
        for i in range(core_nodes, total):
            nxt = core_nodes + ((i - core_nodes + 1) % vacuum_nodes)
            M[i, nxt] = 0.5
            M[nxt, i] = 0.5
            
    return M

def main():
    print("===========================================================")
    print("  Phase 5C-1: Multi-Topology Hypergraph Scan")
    print("===========================================================")
    
    gen = DeterministicK3Generator()
    
    topologies = {
        "K3 (Triangle)": nx.complete_graph(3),
        "K4 (Tetrahedron)": nx.complete_graph(4),
        "K5 (Pentachoron)": nx.complete_graph(5),
        "K3,3 (Utility Graph)": nx.complete_bipartite_graph(3, 3),
        "Petersen Graph": nx.petersen_graph(),
        "Cayley (Cube)": nx.cubical_graph(),
    }
    
    results = []
    
    print(f"{'Topology':<22} | {'λ1 (Spectral Radius)':<20} | {'Matched K3 Surface':<20}")
    print("-" * 68)
    
    for name, G in topologies.items():
        M = build_graph_with_vacuum(G, vacuum_nodes=11)
        eigenvalues = np.abs(linalg.eigvals(M))
        lambda_1 = float(np.max(eigenvalues))
        
        # We manually call match or just try/except if it falls back to a default.
        # The generator maps to nearest spectral radius.
        k3 = gen.from_adjacency_matrix(M)
        
        print(f"{name:<22} | {lambda_1:<20.4f} | {k3.name:<20} (P={k3.picard_number})")
        
        results.append({
            "topology": name,
            "lambda_1": lambda_1,
            "matched_k3": k3.name,
            "picard_number": k3.picard_number
        })
        
    out_dir = Path("outputs/stream4_bridge")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "multi_topology_scan.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print("\n✅ Multi-topology scan complete. Results saved to outputs/stream4_bridge/multi_topology_scan.json")

if __name__ == "__main__":
    main()
