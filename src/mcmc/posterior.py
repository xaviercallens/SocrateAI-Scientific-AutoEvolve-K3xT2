"""
Posterior Analysis Module (ST-5)
=================================
Extracts publication-ready summary statistics from merged MCMC chains:
    - Point estimates (MAP, median, mean)
    - Credible intervals (68% and 95% HPD)
    - Pairwise posterior correlation matrix
    - JSON export for archiving
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ParameterSummary:
    """Summary statistics for a single parameter."""
    name: str
    mean: float
    median: float
    map_estimate: float            # Maximum a posteriori
    std: float
    hpd_68: Tuple[float, float]    # 68% highest posterior density interval
    hpd_95: Tuple[float, float]    # 95% highest posterior density interval


@dataclass
class PosteriorSummary:
    """Full posterior summary across all parameters."""
    candidate_id: str
    parameters: List[ParameterSummary]
    correlation_matrix: np.ndarray   # Shape (n_params, n_params)
    param_names: List[str]
    n_effective_samples: int
    best_log_likelihood: float
    best_chi2: float

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "candidate_id": self.candidate_id,
            "n_effective_samples": self.n_effective_samples,
            "best_log_likelihood": self.best_log_likelihood,
            "best_chi2": self.best_chi2,
            "parameters": {
                p.name: {
                    "mean": p.mean,
                    "median": p.median,
                    "map": p.map_estimate,
                    "std": p.std,
                    "hpd_68_lo": p.hpd_68[0],
                    "hpd_68_hi": p.hpd_68[1],
                    "hpd_95_lo": p.hpd_95[0],
                    "hpd_95_hi": p.hpd_95[1],
                }
                for p in self.parameters
            },
            "correlation_matrix": self.correlation_matrix.tolist(),
            "param_names": self.param_names,
        }


def compute_hpd(samples: np.ndarray, credible_level: float) -> Tuple[float, float]:
    """
    Compute the Highest Posterior Density (HPD) interval.

    The HPD is the shortest interval containing `credible_level` fraction
    of the samples. This is found by sorting the samples and scanning
    all intervals of the required width.

    Args:
        samples: 1D array of MCMC samples.
        credible_level: Fraction in (0, 1), e.g. 0.68 or 0.95.

    Returns:
        (lower, upper) bounds of the HPD interval.
    """
    sorted_samples = np.sort(samples)
    n = len(sorted_samples)
    interval_size = int(np.ceil(credible_level * n))

    if interval_size >= n:
        return (float(sorted_samples[0]), float(sorted_samples[-1]))

    # Find the shortest interval containing interval_size samples
    widths = sorted_samples[interval_size:] - sorted_samples[:n - interval_size]
    best_idx = int(np.argmin(widths))

    return (float(sorted_samples[best_idx]), float(sorted_samples[best_idx + interval_size]))


def analyze_posterior(
    samples: np.ndarray,
    log_likelihoods: np.ndarray,
    param_names: List[str],
    candidate_id: str = "unknown",
) -> PosteriorSummary:
    """
    Compute full posterior summary from merged MCMC samples.

    Args:
        samples: Array of shape (n_samples, n_params).
        log_likelihoods: Array of shape (n_samples,).
        param_names: Names for each parameter column.
        candidate_id: Identifier string.

    Returns:
        PosteriorSummary with all statistics.
    """
    n_samples, n_params = samples.shape

    # MAP estimate: sample with highest log-likelihood
    map_idx = int(np.argmax(log_likelihoods))
    best_ll = float(log_likelihoods[map_idx])
    best_chi2 = -2.0 * best_ll  # Approximate: ignoring normalization constant

    parameter_summaries = []
    for p in range(n_params):
        col = samples[:, p]

        summary = ParameterSummary(
            name=param_names[p],
            mean=float(np.mean(col)),
            median=float(np.median(col)),
            map_estimate=float(samples[map_idx, p]),
            std=float(np.std(col)),
            hpd_68=compute_hpd(col, 0.68),
            hpd_95=compute_hpd(col, 0.95),
        )
        parameter_summaries.append(summary)

        logger.info(
            f"  {summary.name}: "
            f"mean={summary.mean:.5f} ± {summary.std:.5f}  "
            f"68% HPD=[{summary.hpd_68[0]:.5f}, {summary.hpd_68[1]:.5f}]  "
            f"95% HPD=[{summary.hpd_95[0]:.5f}, {summary.hpd_95[1]:.5f}]"
        )

    # Correlation matrix
    corr = np.corrcoef(samples.T)

    return PosteriorSummary(
        candidate_id=candidate_id,
        parameters=parameter_summaries,
        correlation_matrix=corr,
        param_names=param_names,
        n_effective_samples=n_samples,
        best_log_likelihood=best_ll,
        best_chi2=best_chi2,
    )


def save_posterior(
    posterior: PosteriorSummary,
    output_dir: str = "outputs/mcmc",
    filename: str = "posterior_summary.json",
) -> Path:
    """
    Save posterior summary to JSON.

    Args:
        posterior: PosteriorSummary to save.
        output_dir: Directory path.
        filename: Output filename.

    Returns:
        Path to saved file.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    filepath = out_path / filename

    with open(filepath, "w") as f:
        json.dump(posterior.to_dict(), f, indent=2)

    logger.info(f"Posterior summary saved to {filepath}")
    return filepath


def format_latex_table(posterior: PosteriorSummary) -> str:
    """
    Format posterior summary as a LaTeX table for arXiv preprint.

    Returns:
        LaTeX table string.
    """
    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{K3$\times$T$^2$ MCMC Posterior Summary (DESI DR1 BAO)}",
        r"\label{tab:posterior}",
        r"\begin{tabular}{lcccc}",
        r"\hline",
        r"Parameter & Mean & MAP & 68\% HPD & 95\% HPD \\",
        r"\hline",
    ]

    for p in posterior.parameters:
        lines.append(
            f"${p.name}$ & ${p.mean:.4f} \\pm {p.std:.4f}$ & "
            f"${p.map_estimate:.4f}$ & "
            f"$[{p.hpd_68[0]:.4f}, {p.hpd_68[1]:.4f}]$ & "
            f"$[{p.hpd_95[0]:.4f}, {p.hpd_95[1]:.4f}]$ \\\\"
        )

    lines.extend([
        r"\hline",
        r"\end{tabular}",
        r"\end{table}",
    ])

    return "\n".join(lines)
