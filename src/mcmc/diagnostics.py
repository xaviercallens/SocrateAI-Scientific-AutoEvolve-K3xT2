"""
Convergence Diagnostics for Multi-Chain MCMC (ST-4)
====================================================
Implements:
    - Gelman-Rubin R̂ (split-R̂, Vehtari et al. 2021)
    - Effective sample size (n_eff)
    - Integrated autocorrelation time
    - Geweke diagnostic
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ConvergenceDiagnostics:
    """Container for all convergence diagnostic results."""
    r_hat: Dict[str, float]              # Gelman-Rubin R̂ per parameter
    n_eff: Dict[str, float]              # Effective sample size per parameter
    autocorrelation_time: Dict[str, float]  # Integrated τ_int per parameter
    geweke_z: Dict[str, float]           # Geweke z-score per parameter
    all_converged: bool                  # True if R̂ < threshold for all params
    convergence_threshold: float = 1.05  # R̂ threshold for convergence

    def summary(self) -> str:
        lines = [
            "╔══════════════════════════════════════════════════════════════╗",
            "║               MCMC Convergence Diagnostics                  ║",
            "╠══════════════════════════════════════════════════════════════╣",
        ]
        for param in self.r_hat:
            r = self.r_hat[param]
            n = self.n_eff.get(param, 0)
            tau = self.autocorrelation_time.get(param, 0)
            gz = self.geweke_z.get(param, 0)
            status = "✅" if r < self.convergence_threshold else "❌"
            lines.append(
                f"║ {status} {param:<18s} R̂={r:.4f}  n_eff={n:>7.0f}  "
                f"τ_int={tau:>6.1f}  Geweke_z={gz:>+6.2f} ║"
            )
        verdict = "✅ CONVERGED" if self.all_converged else "❌ NOT CONVERGED"
        lines.append("╠══════════════════════════════════════════════════════════════╣")
        lines.append(f"║ Overall: {verdict:<50s} ║")
        lines.append("╚══════════════════════════════════════════════════════════════╝")
        return "\n".join(lines)


def compute_gelman_rubin(
    chains: List[np.ndarray],
    param_names: List[str],
    split: bool = True,
) -> Dict[str, float]:
    """
    Compute the Gelman-Rubin R̂ statistic for each parameter.

    Uses split-R̂ (Vehtari et al. 2021): each chain is split in half,
    doubling the effective number of chains for better sensitivity to
    non-stationarity.

    Args:
        chains: List of arrays, each shape (n_samples, n_params).
        param_names: Names for each parameter column.
        split: If True, split each chain in half before computing R̂.

    Returns:
        Dict mapping param name → R̂ value.
    """
    if not chains:
        raise ValueError("No chains provided for R̂ computation.")

    # Optionally split each chain in half
    if split:
        split_chains = []
        for chain in chains:
            n = len(chain)
            mid = n // 2
            split_chains.append(chain[:mid])
            split_chains.append(chain[mid:2 * mid])  # Equal length halves
        chains = split_chains

    m = len(chains)            # Number of (possibly split) chains
    n = min(len(c) for c in chains)  # Minimum chain length
    n_params = chains[0].shape[1]

    r_hat = {}
    for p in range(n_params):
        # Extract parameter p from all chains, truncated to length n
        chain_means = np.array([c[:n, p].mean() for c in chains])
        grand_mean = chain_means.mean()

        # Between-chain variance B
        B = (n / (m - 1)) * np.sum((chain_means - grand_mean) ** 2)

        # Within-chain variance W
        chain_vars = np.array([c[:n, p].var(ddof=1) for c in chains])
        W = chain_vars.mean()

        # Pooled posterior variance estimate
        var_hat = ((n - 1) / n) * W + (1.0 / n) * B

        # R̂
        if W > 0:
            r = np.sqrt(var_hat / W)
        else:
            r = float("inf")

        r_hat[param_names[p]] = float(r)

    return r_hat


def compute_effective_sample_size(
    chains: List[np.ndarray],
    param_names: List[str],
) -> Dict[str, float]:
    """
    Estimate effective sample size (n_eff) using the initial monotone
    sequence estimator (Geyer 1992).

    Args:
        chains: List of arrays, each shape (n_samples, n_params).
        param_names: Names for each parameter column.

    Returns:
        Dict mapping param name → n_eff.
    """
    n_eff = {}
    n_params = chains[0].shape[1]

    for p in range(n_params):
        total_n_eff = 0.0
        for chain in chains:
            samples = chain[:, p]
            n = len(samples)
            if n < 10:
                total_n_eff += n
                continue

            mean = samples.mean()
            var = samples.var()
            if var == 0:
                total_n_eff += n
                continue

            # Compute autocorrelation using FFT
            x = samples - mean
            fft_x = np.fft.fft(x, n=2 * n)
            acf = np.fft.ifft(fft_x * np.conj(fft_x)).real[:n] / (var * n)

            # Sum autocorrelation pairs until negative (Geyer's criterion)
            tau_hat = 1.0
            for k in range(1, n // 2):
                rho_pair = acf[2 * k - 1] + acf[2 * k]
                if rho_pair < 0:
                    break
                tau_hat += 2 * rho_pair

            chain_n_eff = n / tau_hat
            total_n_eff += max(1.0, chain_n_eff)

        n_eff[param_names[p]] = total_n_eff

    return n_eff


def compute_autocorrelation_time(
    chains: List[np.ndarray],
    param_names: List[str],
) -> Dict[str, float]:
    """
    Compute integrated autocorrelation time τ_int for each parameter,
    averaged across chains.
    """
    tau_int = {}
    n_params = chains[0].shape[1]

    for p in range(n_params):
        tau_values = []
        for chain in chains:
            samples = chain[:, p]
            n = len(samples)
            if n < 10:
                tau_values.append(1.0)
                continue

            mean = samples.mean()
            var = samples.var()
            if var == 0:
                tau_values.append(1.0)
                continue

            x = samples - mean
            fft_x = np.fft.fft(x, n=2 * n)
            acf = np.fft.ifft(fft_x * np.conj(fft_x)).real[:n] / (var * n)

            # Integrate until first negative autocorrelation
            tau = 1.0
            for k in range(1, n):
                if acf[k] < 0.05:
                    break
                tau += 2 * acf[k]

            tau_values.append(max(1.0, tau))

        tau_int[param_names[p]] = float(np.mean(tau_values))

    return tau_int


def compute_geweke(
    chains: List[np.ndarray],
    param_names: List[str],
    frac_start: float = 0.1,
    frac_end: float = 0.5,
) -> Dict[str, float]:
    """
    Geweke diagnostic: z-score comparing early vs late portions of each chain.

    |z| < 1.96 indicates stationarity at 95% confidence.

    Args:
        chains: List of arrays.
        param_names: Parameter names.
        frac_start: Fraction of chain for "early" sample (default 10%).
        frac_end: Fraction of chain for "late" sample (default last 50%).

    Returns:
        Dict mapping param name → average absolute z-score across chains.
    """
    geweke_z = {}
    n_params = chains[0].shape[1]

    for p in range(n_params):
        z_scores = []
        for chain in chains:
            n = len(chain)
            n_start = max(1, int(frac_start * n))
            n_end = max(1, int(frac_end * n))

            early = chain[:n_start, p]
            late = chain[-n_end:, p]

            if len(early) < 2 or len(late) < 2:
                z_scores.append(0.0)
                continue

            mean_diff = early.mean() - late.mean()
            se = np.sqrt(early.var() / len(early) + late.var() / len(late))

            if se > 0:
                z_scores.append(mean_diff / se)
            else:
                z_scores.append(0.0)

        geweke_z[param_names[p]] = float(np.mean(np.abs(z_scores)))

    return geweke_z


def run_all_diagnostics(
    chains: List[np.ndarray],
    param_names: List[str],
    convergence_threshold: float = 1.05,
) -> ConvergenceDiagnostics:
    """
    Run all convergence diagnostics on a set of MCMC chains.

    Args:
        chains: List of sample arrays, each shape (n_samples, n_params).
        param_names: Names for each parameter.
        convergence_threshold: R̂ threshold for declaring convergence.

    Returns:
        ConvergenceDiagnostics object with all results.
    """
    logger.info(f"Running convergence diagnostics on {len(chains)} chains...")

    r_hat = compute_gelman_rubin(chains, param_names, split=True)
    n_eff = compute_effective_sample_size(chains, param_names)
    tau_int = compute_autocorrelation_time(chains, param_names)
    geweke = compute_geweke(chains, param_names)

    all_converged = all(r < convergence_threshold for r in r_hat.values())

    diagnostics = ConvergenceDiagnostics(
        r_hat=r_hat,
        n_eff=n_eff,
        autocorrelation_time=tau_int,
        geweke_z=geweke,
        all_converged=all_converged,
        convergence_threshold=convergence_threshold,
    )

    logger.info(f"Convergence: {'✅ PASSED' if all_converged else '❌ FAILED'}")
    for param, r in r_hat.items():
        logger.info(f"  {param}: R̂={r:.4f}, n_eff={n_eff[param]:.0f}")

    return diagnostics
