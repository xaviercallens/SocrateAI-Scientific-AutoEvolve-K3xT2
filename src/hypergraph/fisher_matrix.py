import torch
import numpy as np
from typing import Callable, List, Dict, Any

class FisherInformationTopology:
    """
    Computes the Fisher Information Matrix (FIM) for the K3xT2 moduli space
    to validate the mathematical stability of topological vacua (e.g. positive curvature).
    
    Ported from Stream 4 (recovered from outputs/phase8/fisher_curvature_results.json).
    """
    def __init__(self, log_likelihood_fn: Callable):
        self.log_likelihood = log_likelihood_fn

    def compute_fisher_matrix(self, theta_map: torch.Tensor, epsilon: float = 1e-4) -> torch.Tensor:
        """
        Computes the FIM at the MAP estimate using finite differences of the log-likelihood.
        F_{ij} = - \partial^2 \ln L / \partial \theta_i \partial \theta_j
        """
        n_params = len(theta_map)
        fisher = torch.zeros((n_params, n_params))
        
        # Central difference approximation for the Hessian
        ll_center = self.log_likelihood(theta_map)
        
        for i in range(n_params):
            for j in range(i, n_params):
                theta_fwd_i = theta_map.clone()
                theta_fwd_i[i] += epsilon
                
                theta_bwd_i = theta_map.clone()
                theta_bwd_i[i] -= epsilon
                
                if i == j:
                    ll_fwd = self.log_likelihood(theta_fwd_i)
                    ll_bwd = self.log_likelihood(theta_bwd_i)
                    fisher[i, i] = -(ll_fwd - 2 * ll_center + ll_bwd) / (epsilon ** 2)
                else:
                    theta_fwd_j = theta_map.clone()
                    theta_fwd_j[j] += epsilon
                    
                    theta_fwd_ij = theta_fwd_i.clone()
                    theta_fwd_ij[j] += epsilon
                    
                    ll_fwd_i = self.log_likelihood(theta_fwd_i)
                    ll_fwd_j = self.log_likelihood(theta_fwd_j)
                    ll_fwd_ij = self.log_likelihood(theta_fwd_ij)
                    
                    cross_deriv = (ll_fwd_ij - ll_fwd_i - ll_fwd_j + ll_center) / (epsilon ** 2)
                    fisher[i, j] = -cross_deriv
                    fisher[j, i] = -cross_deriv
                    
        return fisher

    def validate_vacuum_stability(self, theta_map: torch.Tensor, param_names: List[str]) -> Dict[str, Any]:
        """
        Validates if the topological vacuum is stable by checking if the FIM is positive definite.
        """
        fisher = self.compute_fisher_matrix(theta_map)
        eigenvalues = torch.linalg.eigvalsh(fisher)
        
        is_stable = torch.all(eigenvalues > 0).item()
        
        return {
            "test": "Fisher Information Matrix Curvature Test",
            "evaluation_point": theta_map.tolist(),
            "fisher_eigenvalues": eigenvalues.tolist(),
            "stability_verdict": "CONFIRMED: mathematically stable topological vacuum (positive curvature)." if is_stable else "UNSTABLE: Negative curvature detected.",
            "is_stable": is_stable
        }
