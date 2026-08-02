import torch
import torch.nn as nn


class DifferentiableTopologicalMask(nn.Module):
    """Neural network layer generating adaptive topological mask tensors T_theta."""

    def __init__(self, num_nodes: int, threshold: float = 0.5):
        """Initializes the differentiable topological mask layer.

        Args:
            num_nodes (int): Number of graph nodes.
            threshold (float, optional): Edge cutoff threshold during inference. Defaults to 0.5.
        """
        super().__init__()
        self.threshold = threshold
        self.edge_weights = nn.Parameter(
            torch.ones((num_nodes, num_nodes)) * 0.8)

    def forward(self, adj_matrix: torch.Tensor) -> torch.Tensor:
        """Generates continuous mask tensor T_theta bounded in [0, 1].

        Args:
            adj_matrix (torch.Tensor): Adjacency matrix tensor.

        Returns:
            torch.Tensor: Masked adjacency matrix tensor.
        """
        sigmoid_mask = torch.sigmoid(self.edge_weights)
        if not self.training:
            # Apply hard thresholding during inference
            return (sigmoid_mask > self.threshold).float() * adj_matrix
        return sigmoid_mask * adj_matrix


def topological_relu(
        tensor: torch.Tensor,
        threshold: float = 0.5) -> torch.Tensor:
    """Custom activation function enforcing physical thresholding.

    Args:
        tensor (torch.Tensor): Input tensor.
        threshold (float, optional): Activation threshold. Defaults to 0.5.

    Returns:
        torch.Tensor: Thresholded output tensor.
    """
    return tensor * (tensor > threshold).float()
