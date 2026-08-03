"""
Unit Test Suite for Advanced ML Modules
========================================
Tests:
- Equivariant Graph Neural Network (GNN)
- Symbolic Regression Engine for Lean 4
- Neural ODE Picard-Fuchs Integrator
- Simulation-Based Inference (SBI) logic
"""

import os
import sys
import unittest
import torch
import numpy as np

# Ensure src/ is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from ml_modules.equivariant_gnn import HypergraphGNNPredictor, train_gnn_on_k4_rewriting
from ml_modules.symbolic_regression import SymbolicExpressionLearner, run_symbolic_regression_pipeline
from ml_modules.neural_ode_pf import PicardFuchsODEFunc, EulerNeuralODESolver, run_neural_ode_pf_integration

class TestAdvancedMLModules(unittest.TestCase):

    def test_equivariant_gnn_forward_pass(self):
        """Test GNN forward pass shape and tensor outputs."""
        model = HypergraphGNNPredictor(node_dim=16, hidden_dim=32)
        batch_size = 4
        N = 4 # K4 graph
        
        adj = torch.ones((batch_size, N, N)) - torch.eye(N).unsqueeze(0)
        l1, p, gap = model(adj)
        
        self.assertEqual(l1.shape, (batch_size,))
        self.assertEqual(p.shape, (batch_size,))
        self.assertEqual(gap.shape, (batch_size,))

    def test_equivariant_gnn_training_run(self):
        """Test small training loop of GNN module."""
        res = train_gnn_on_k4_rewriting(n_steps=10)
        self.assertEqual(res["status"], "success")
        self.assertIn("spectral_radius_lambda1", res["k4_predictions"])
        self.assertIn("picard_number", res["k4_predictions"])

    def test_symbolic_regression_fitting(self):
        """Test symbolic expression discovery and Lean 4 code formatting."""
        learner = SymbolicExpressionLearner()
        w0_formula, w0_lean = learner.fit_w0_equation(tau_val=0.50, w0_val=-0.974)
        
        self.assertIn("w0 = -1", w0_formula)
        self.assertIn("def w0_symbolic_formula", w0_lean)
        self.assertIn("theorem w0_exact_stabilization_point", w0_lean)
        
        hex_formula, hex_lean = learner.fit_hexadecapole_equation(gamma_val=4.847, l_val=4)
        self.assertIn("C_l =", hex_formula)
        self.assertIn("def hexadecapole_cl", hex_lean)

    def test_neural_ode_pf_integration(self):
        """Test RK4/Euler integration step and backprop in Neural ODE."""
        ode_func = PicardFuchsODEFunc(hidden_dim=16)
        solver = EulerNeuralODESolver(ode_func)
        
        z_span = torch.linspace(0.001, 0.02, steps=10)
        y0 = torch.tensor([[1.0, 0.0, 0.0]], dtype=torch.float32)
        
        traj = solver.integrate(y0, z_span)
        self.assertEqual(traj.shape, (1, 10, 3))
        
        # Test differentiability
        loss = traj.sum()
        loss.backward()
        
        for param in ode_func.parameters():
            if param.requires_grad:
                self.assertIsNotNone(param.grad)

    def test_neural_ode_pipeline_execution(self):
        """Test full training pipeline execution of Neural ODE."""
        res = run_neural_ode_pf_integration(n_steps=5)
        self.assertEqual(res["status"], "success")
        self.assertGreater(res["integrated_period_integral"], 0.0)

if __name__ == "__main__":
    unittest.main()
