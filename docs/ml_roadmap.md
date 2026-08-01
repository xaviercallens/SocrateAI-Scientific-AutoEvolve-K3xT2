# Machine Learning Augmentation Roadmap

This document outlines the strategic integration of advanced Machine Learning (ML) techniques to augment the computational and neuro-symbolic pipelines within the **SocrateAI AlphaEvolve K3×T²** project. These paradigms will accelerate landscape scanning, enable end-to-end differentiable cosmological physics, and fully automate symbolic theorem extraction.

## 1. Simulation-Based Inference (SBI) with Normalizing Flows
- **Objective:** Replace the slow Metropolis-Hastings MCMC landscape scan in Phase 7.
- **Approach:** Use `sbi` to train Normalizing Flows (NFs) on synthetic data generated from the F-term scalar potential and 4D EFT. NFs learn the posterior distribution $p(\theta | x_{obs})$ directly, where $\theta$ are the $T^2$ moduli and $x_{obs}$ are the DESI BAO and Euclid observables.
- **Status:** **In Progress** (Phase 7 SBI pipeline replacement).

## 2. Symbolic Regression (SR) / Inductive Biases
- **Objective:** Bridge numerical evolution and formal Lean 4 verification autonomously.
- **Approach:** Insert a Symbolic Regression module (e.g., PySR) between the numerical `AlphaEvolve` output and the `lean_oracle`. The SR module will observe the numerical behavior (e.g., $w_0$ evolution or hexadecapole signature scaling) and extract exact algebraic expressions.
- **Status:** Planned.

## 3. Equivariant Graph Neural Networks (GNNs)
- **Objective:** Replace deterministic hypergraph rewriting rules with continuous learning.
- **Approach:** Train an Equivariant GNN on the $K_4$ topological seed. The GNN will learn the causal loop sequences $Tr(M^n)$ and map the discrete algebraic properties of the graph directly to the continuous $K3 \times T^2$ geometric metrics (like the Picard $\rho=19$ fixed points), skipping discrete intermediate matrices.
- **Status:** Planned.

## 4. Differentiable Physics & Neural ODEs
- **Objective:** Solve Picard-Fuchs differential equations over the moduli space without numerical instability.
- **Approach:** Use JAX-based Neural ODEs (e.g., `diffrax`) to integrate the cosmological background expansion. This renders the entire universe's evolution end-to-end differentiable, allowing gradient descent to flow from $z=0$ observables all the way back to the Big Bang initial string state.
- **Status:** Planned.

## 5. Spherical CNNs (HEALPix)
- **Objective:** Map the $\ell=4$ hexadecapole anisotropy directly onto simulated skies.
- **Approach:** Utilize `DeepSphere` or similar equivariant networks operating on spherical data to inject the $K_4$ SGWB predictions into synthetic SKA/NANOGrav full-sky maps, ensuring precise extraction of the topological signature from foregrounds.
- **Status:** Planned.
