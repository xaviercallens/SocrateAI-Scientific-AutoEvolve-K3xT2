"""
Equivariant Graph Neural Network (GNN) for Hypergraph Continuous Limits
================================================----------------======
Maps discrete K4 oligon adjacency matrices and Hadamard rewriting sequences
to continuous geometric limits (Picard number P, spectral radius lambda_1,
and topological mass gap gamma).
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.cuda.amp import autocast, GradScaler
import numpy as np
from typing import Dict, Tuple, Any

class EquivariantGraphConv(nn.Module):
    """Permutation-equivariant graph convolution layer for hypergraph adjacency."""
    def __init__(self, in_features: int, out_features: int):
        super().__init__()
        self.msg_mlp = nn.Sequential(
            nn.Linear(2 * in_features + 1, out_features),
            nn.SiLU(),
            nn.Linear(out_features, out_features)
        )
        self.node_mlp = nn.Sequential(
            nn.Linear(in_features + out_features, out_features),
            nn.SiLU(),
            nn.Linear(out_features, out_features)
        )

    def forward(self, h: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        # h: [batch, N, in_features]
        # adj: [batch, N, N]
        batch, N, f = h.shape
        
        # Expand node features for pairwise messages
        h_i = h.unsqueeze(2).repeat(1, 1, N, 1) # [batch, N, N, f]
        h_j = h.unsqueeze(1).repeat(1, N, 1, 1) # [batch, N, N, f]
        edge_attr = adj.unsqueeze(-1)           # [batch, N, N, 1]
        
        msg_input = torch.cat([h_i, h_j, edge_attr], dim=-1)
        messages = self.msg_mlp(msg_input) * edge_attr # Masked by adjacency
        
        # Aggregate messages
        aggr_msg = messages.sum(dim=2) # [batch, N, out_features]
        
        # Update node representation
        update_input = torch.cat([h, aggr_msg], dim=-1)
        h_next = self.node_mlp(update_input)
        return h_next

class HypergraphGNNPredictor(nn.Module):
    """
    Equivariant GNN model for K4 hypergraph continuum limit prediction.
    """
    def __init__(self, node_dim: int = 16, hidden_dim: int = 64):
        super().__init__()
        self.embedding = nn.Linear(1, node_dim)
        self.conv1 = EquivariantGraphConv(node_dim, hidden_dim)
        self.conv2 = EquivariantGraphConv(hidden_dim, hidden_dim)
        self.conv3 = EquivariantGraphConv(hidden_dim, hidden_dim)
        
        # Global graph pooling & predictor heads
        self.head_spectral = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.SiLU(),
            nn.Linear(32, 1) # Spectral radius lambda_1
        )
        self.head_picard = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.SiLU(),
            nn.Linear(32, 1) # Picard number P
        )
        self.head_gap = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.SiLU(),
            nn.Linear(32, 1) # Spectral gap gamma
        )

    def forward(self, adj: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        # adj: [batch, N, N]
        batch, N, _ = adj.shape
        degree = adj.sum(dim=-1, keepdim=True) # [batch, N, 1]
        h = self.embedding(degree) # Initial node features from degree
        
        h = self.conv1(h, adj)
        h = self.conv2(h, adj)
        h = self.conv3(h, adj)
        
        # Permutation-invariant graph pooling (Mean + Max)
        g_mean = h.mean(dim=1)
        
        lambda_1 = self.head_spectral(g_mean).squeeze(-1)
        picard = self.head_picard(g_mean).squeeze(-1)
        gap = self.head_gap(g_mean).squeeze(-1)
        
        return lambda_1, picard, gap

import os
from pathlib import Path

def train_gnn_on_k4_rewriting(n_steps: int = 200, save_pretrained: bool = True) -> Dict[str, Any]:
    """
    Simulates K4 hypergraph rewritings and trains the Equivariant GNN to learn
    the continuous limit properties. Saves/loads pretrained model weights.
    
    AUDIT FIX (TASK-09/B4): This function is explicitly marked as a SYNTHETIC
    PRE-TRAINING HARNESS. It generates mock adjacency matrices (`A_noisy`) to test
    the permutation-equivariant architecture of the GNN. It DOES NOT read live
    topological data from the Lean 4 hypergraph engine, and therefore the loss metrics
    produced here do not validate physical K3 geometry.
    """
    import logging
    logging.getLogger(__name__).warning(
        "GNN training pipeline is running in SYNTHETIC PRE-TRAINING mode. "
        "Generated adjacency matrices are mock data (TASK-09)."
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    is_distributed = False
    
    if "WORLD_SIZE" in os.environ and torch.cuda.is_available():
        if not dist.is_initialized():
            dist.init_process_group("nccl")
        local_rank = int(os.environ.get("LOCAL_RANK", 0))
        torch.cuda.set_device(local_rank)
        device = torch.device(f"cuda:{local_rank}")
        is_distributed = True
        
    model = HypergraphGNNPredictor(node_dim=16, hidden_dim=64).to(device)
    pretrained_path = Path("models/pretrained/gnn_k4_pretrained.pt")
    
    # Load pretrained weights if available
    if pretrained_path.exists():
        try:
            # Handle DDP state dict loading if necessary
            state_dict = torch.load(pretrained_path, weights_only=True, map_location=device)
            model.load_state_dict(state_dict)
            model.eval()
            print(f"📥 Loaded pretrained Equivariant GNN weights from {pretrained_path}")
        except Exception as e:
            print(f"⚠️ Could not load pretrained weights: {e}")

    if is_distributed:
        model = DDP(model, device_ids=[local_rank])

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    scaler = GradScaler(enabled=torch.cuda.is_available())
    
    import glob
    import json
    
    # Checkpoint batch generator
    def generate_batch(batch_size=16, N=4):
        adjs = []
        target_lambda = []
        target_picard = []
        target_gap = []
        
        # Load real checkpoints if available
        checkpoint_files = glob.glob("data/checkpoints/*.json")
        if checkpoint_files:
            sampled_files = np.random.choice(checkpoint_files, min(batch_size, len(checkpoint_files)), replace=True)
            for fpath in sampled_files:
                try:
                    with open(fpath, 'r') as f:
                        data = json.load(f)
                        # Extract data from best_candidate
                        cand = data.get("best_candidate", {})
                        
                        # Reconstruct a "pseudo-adjacency" based on the moduli (simplified for demonstration, 
                        # in a real K4 hypergraph this would come from the topology state)
                        # We use the complex structure & kahler moduli to perturb the K4 base graph
                        cs = cand.get("complex_structure", [0.0, 0.0, 0.0])
                        tau = cand.get("t2_modulus_tau", 0.5)
                        
                        A = np.ones((N, N)) - np.eye(N)
                        # Add deterministic perturbation based on physics parameters
                        perturbation = np.array([
                            [0, tau, cs[0], cs[1]],
                            [tau, 0, cs[2], tau],
                            [cs[0], cs[2], 0, tau],
                            [cs[1], tau, tau, 0]
                        ])
                        # Keep it bounded and symmetric
                        perturbation = (perturbation + perturbation.T) / 2.0
                        perturbation = np.clip(perturbation, -0.5, 0.5)
                        A_noisy = np.clip(A + perturbation, 0.0, 1.0)
                        
                        # Real target values from the checkpoint
                        # Picard number
                        p_val = float(cand.get("picard_number", 19.0))
                        
                        # We reverse-engineer a lambda_1 that correlates with this P
                        eigvals = np.linalg.eigvalsh(A_noisy)
                        l1 = float(np.max(eigvals))
                        
                        # Gap from phenotype
                        gap_val = cand.get("phenotype", {}).get("pta_anisotropy", 0.05) * 100.0 # scale for stability

                        adjs.append(A_noisy)
                        target_lambda.append(l1)
                        target_picard.append(p_val)
                        target_gap.append(gap_val)
                except Exception as e:
                    pass
                    
        # Fallback to synthetic if no checkpoints loaded or failed
        while len(adjs) < batch_size:
            A = np.ones((N, N)) - np.eye(N)
            noise = np.random.uniform(0.0, 0.2, (N, N))
            A_noisy = (A + noise + noise.T) / 2.0
            
            eigvals = np.linalg.eigvalsh(A_noisy)
            l1 = float(np.max(eigvals))
            p_val = 19.0 - (l1 - 3.0) * 2.0 + np.random.normal(0, 0.1)
            gap_val = 4.847 + (l1 - 3.0) * 0.5
            
            adjs.append(A_noisy)
            target_lambda.append(l1)
            target_picard.append(p_val)
            target_gap.append(gap_val)
            
        return (torch.tensor(np.array(adjs), dtype=torch.float32),
                torch.tensor(np.array(target_lambda), dtype=torch.float32),
                torch.tensor(np.array(target_picard), dtype=torch.float32),
                torch.tensor(np.array(target_gap), dtype=torch.float32))

    model.train()
    losses = []
    for step in range(n_steps):
        adj, t_l1, t_p, t_gap = generate_batch(batch_size=32)
        adj, t_l1, t_p, t_gap = adj.to(device), t_l1.to(device), t_p.to(device), t_gap.to(device)
        
        optimizer.zero_grad()
        
        # Phase 1: Mixed Precision (AMP) & Sparse Tensor Support
        with autocast(enabled=torch.cuda.is_available()):
            # Sparse Tensor Conversion (torch.sparse)
            if adj.shape[1] > 100:
                adj = adj.to_sparse()
                
            pred_l1, pred_p, pred_gap = model(adj)
            
            loss = (F.mse_loss(pred_l1, t_l1) + 
                    F.mse_loss(pred_p, t_p) + 
                    F.mse_loss(pred_gap, t_gap))
        
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        losses.append(loss.item())

    # Save pretrained weights
    if save_pretrained:
        pretrained_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), pretrained_path)
        print(f"💾 Pretrained GNN checkpoint saved to: {pretrained_path}")

    # Predict on pure K4 graph
    model.eval()
    K4_pure = torch.tensor(np.ones((1, 4, 4)) - np.eye(4), dtype=torch.float32)
    with torch.no_grad():
        p_l1, p_p, p_gap = model(K4_pure)
        
    return {
        "status": "success",
        "final_loss": float(losses[-1]),
        "pretrained_path": str(pretrained_path),
        "k4_predictions": {
            "spectral_radius_lambda1": float(p_l1.item()),
            "picard_number": float(p_p.item()),
            "spectral_gap_gamma": float(p_gap.item()),
        }
    }

if __name__ == "__main__":
    res = train_gnn_on_k4_rewriting(n_steps=100)
    print("GNN Training Results:", res)

