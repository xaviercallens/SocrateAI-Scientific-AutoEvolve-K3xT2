#!/usr/bin/env python3
"""
Expérience A : Pipeline TDA (Topological Data Analysis) sur Euclid Q1
=====================================================================
Calcule les diagrammes de persistance H₀ et H₁ et la transformée de
caractéristique d'Euler χ(ν) sur les coordonnées angulaires réelles
des 80 376 galaxies Euclid Q1 MER.

Hypothèse K3×T² : La toile cosmique doit conserver l'empreinte des
b₂(K3) = 22 cycles non triviaux et des 24 nœuds nodaux de Kummer,
ce qui se manifeste comme un pic de la caractéristique d'Euler
χ ≈ 24.0 au seuil critique de filtration.
"""

import glob
import json
import logging
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from astropy.io import fits
from scipy.spatial import Delaunay

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

OUT_DIR = Path("outputs/tda_euclid")
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR = Path("paper/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

def load_euclid_q1_coordinates():
    """Load RA, Dec from all 3 Euclid Q1 MER FINAL-CAT FITS tiles."""
    fits_files = sorted(glob.glob("data/euclid_q1/tile_*/EUC_MER_FINAL-CAT_*.fits"))
    all_ra, all_dec = [], []
    for fp in fits_files:
        with fits.open(fp) as hdul:
            tbl = hdul[1].data
            ra = np.asarray(tbl["RIGHT_ASCENSION"], dtype=float)
            dec = np.asarray(tbl["DECLINATION"], dtype=float)
            mask = np.isfinite(ra) & np.isfinite(dec)
            all_ra.append(ra[mask])
            all_dec.append(dec[mask])
            logger.info(f"  Loaded {np.sum(mask)} galaxies from {Path(fp).name}")
    ra = np.concatenate(all_ra)
    dec = np.concatenate(all_dec)
    logger.info(f"Total: {len(ra)} galaxies with valid coordinates")
    return ra, dec

def compute_persistent_homology(points_2d, max_edge=0.02, n_subsample=5000):
    """
    Compute Rips complex persistent homology on a subsample of 2D angular positions.
    Uses gudhi for H₀ (connected components) and H₁ (loops/cycles).
    """
    import gudhi

    # Subsample for computational feasibility
    np.random.seed(42)
    idx = np.random.choice(len(points_2d), size=min(n_subsample, len(points_2d)), replace=False)
    pts = points_2d[idx]

    logger.info(f"Computing Rips complex on {len(pts)} subsampled points (max_edge={max_edge} deg)...")

    rips = gudhi.RipsComplex(points=pts.tolist(), max_edge_length=max_edge)
    simplex_tree = rips.create_simplex_tree(max_dimension=2)
    logger.info(f"  Simplex tree: {simplex_tree.num_simplices()} simplices, dim={simplex_tree.dimension()}")

    persistence = simplex_tree.persistence()
    logger.info(f"  Computed {len(persistence)} persistence pairs")

    # Separate by dimension
    h0_pairs = [(b, d) for dim, (b, d) in persistence if dim == 0 and d != float('inf')]
    h1_pairs = [(b, d) for dim, (b, d) in persistence if dim == 1 and d != float('inf')]
    h0_inf = sum(1 for dim, (b, d) in persistence if dim == 0 and d == float('inf'))

    logger.info(f"  H₀: {len(h0_pairs)} finite pairs + {h0_inf} essential (connected components)")
    logger.info(f"  H₁: {len(h1_pairs)} finite pairs (loops/cycles)")

    return h0_pairs, h1_pairs, h0_inf, persistence

def euler_characteristic_transform(points_2d, n_thresholds=50, n_subsample=8000):
    """
    Compute the Euler Characteristic Transform χ(ν) as a function of
    density threshold ν using the Alpha complex filtration.

    For a K3 surface, the expected Euler characteristic is χ = 24.
    """
    import gudhi

    np.random.seed(42)
    idx = np.random.choice(len(points_2d), size=min(n_subsample, len(points_2d)), replace=False)
    pts = points_2d[idx]

    logger.info(f"Computing Alpha complex filtration on {len(pts)} points...")
    alpha = gudhi.AlphaComplex(points=pts.tolist())
    st = alpha.create_simplex_tree()
    logger.info(f"  Alpha simplex tree: {st.num_simplices()} simplices")

    # Get all filtration values
    all_simplices = list(st.get_simplices())  # [(simplex_list, filt_value), ...]
    filt_values = sorted(set(fv for _, fv in all_simplices if fv > 0))
    if not filt_values:
        logger.warning("No positive filtration values found")
        return np.array([]), np.array([])

    thresholds = np.linspace(filt_values[0], min(filt_values[-1], 0.001), n_thresholds)
    chi_values = []

    for nu in thresholds:
        n0 = sum(1 for s, fv in all_simplices if len(s) == 1 and fv <= nu)
        n1 = sum(1 for s, fv in all_simplices if len(s) == 2 and fv <= nu)
        n2 = sum(1 for s, fv in all_simplices if len(s) == 3 and fv <= nu)
        chi = n0 - n1 + n2
        chi_values.append(chi)

    return thresholds, np.array(chi_values)


def main():
    logger.info("=" * 70)
    logger.info("  Expérience A : Pipeline TDA sur Catalogue Euclid Q1 MER")
    logger.info("=" * 70)

    # 1. Load real galaxy coordinates
    ra, dec = load_euclid_q1_coordinates()
    points_2d = np.column_stack([ra, dec])

    # 2. Compute persistent homology (H₀, H₁)
    h0_pairs, h1_pairs, h0_inf, persistence = compute_persistent_homology(points_2d, max_edge=0.015, n_subsample=4000)

    # 3. Compute Euler Characteristic Transform
    thresholds, chi_values = euler_characteristic_transform(points_2d, n_thresholds=40, n_subsample=5000)

    # 4. Betti number analysis
    # At various filtration scales, count surviving features
    if h1_pairs:
        h1_lifetimes = np.array([d - b for b, d in h1_pairs])
        h1_births = np.array([b for b, d in h1_pairs])
        mean_h1_lifetime = float(np.mean(h1_lifetimes))
        max_h1_lifetime = float(np.max(h1_lifetimes))
        n_persistent_h1 = int(np.sum(h1_lifetimes > np.median(h1_lifetimes)))
    else:
        h1_lifetimes = np.array([])
        mean_h1_lifetime = 0.0
        max_h1_lifetime = 0.0
        n_persistent_h1 = 0

    # K3 topological signature check
    chi_max = float(np.max(chi_values)) if len(chi_values) > 0 else 0
    chi_target = 24.0
    chi_deviation = abs(chi_max - chi_target) / chi_target * 100 if chi_target > 0 else float('inf')

    logger.info(f"\n--- Topological Invariant Analysis ---")
    logger.info(f"  H₁ persistent cycles: {len(h1_pairs)} total, {n_persistent_h1} above-median lifetime")
    logger.info(f"  H₁ mean lifetime: {mean_h1_lifetime:.6f}")
    logger.info(f"  H₁ max lifetime:  {max_h1_lifetime:.6f}")
    logger.info(f"  Euler characteristic peak: χ_max = {chi_max:.1f}")
    logger.info(f"  K3 target χ = 24: deviation = {chi_deviation:.1f}%")
    logger.info(f"  b₂(K3) = 22 cycles: observed H₁ persistent = {n_persistent_h1}")

    # Save results
    results = {
        "total_galaxies": len(ra),
        "subsample_rips": 4000,
        "subsample_alpha": 5000,
        "H0_finite_pairs": len(h0_pairs),
        "H0_essential": h0_inf,
        "H1_total_cycles": len(h1_pairs),
        "H1_persistent_above_median": n_persistent_h1,
        "H1_mean_lifetime": round(mean_h1_lifetime, 6),
        "H1_max_lifetime": round(max_h1_lifetime, 6),
        "euler_char_peak": round(chi_max, 1),
        "euler_char_k3_target": chi_target,
        "euler_char_deviation_pct": round(chi_deviation, 1),
    }
    with open(OUT_DIR / "tda_euclid_q1_results.json", "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved to {OUT_DIR / 'tda_euclid_q1_results.json'}")

    # ─── Plot: 4-panel TDA diagnostic ─────────────────────────────────────
    fig, axes = plt.subplots(2, 2, figsize=(13, 10))

    # Panel A: Galaxy sky map
    ax = axes[0, 0]
    ax.scatter(ra[::10], dec[::10], s=0.3, alpha=0.3, color='navy')
    ax.set_xlabel("RA [deg]", fontsize=11)
    ax.set_ylabel("Dec [deg]", fontsize=11)
    ax.set_title("Panel A: Euclid Q1 Galaxy Sky Map (80,376 MER)", fontsize=11, fontweight='bold')
    ax.grid(True, ls=':', alpha=0.4)

    # Panel B: Persistence diagram (H₀ and H₁)
    ax = axes[0, 1]
    if h0_pairs:
        b0 = [b for b, d in h0_pairs]
        d0 = [d for b, d in h0_pairs]
        ax.scatter(b0, d0, s=8, alpha=0.4, color='#1f77b4', label=f'$H_0$ ({len(h0_pairs)})')
    if h1_pairs:
        b1 = [b for b, d in h1_pairs]
        d1 = [d for b, d in h1_pairs]
        ax.scatter(b1, d1, s=12, alpha=0.6, color='#d62728', marker='^', label=f'$H_1$ ({len(h1_pairs)})')
    lim = ax.get_xlim()[1]
    ax.plot([0, lim], [0, lim], 'k--', lw=0.8, alpha=0.5)
    ax.set_xlabel("Birth", fontsize=11)
    ax.set_ylabel("Death", fontsize=11)
    ax.set_title("Panel B: Persistence Diagram ($H_0, H_1$)", fontsize=11, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, ls=':', alpha=0.4)

    # Panel C: H₁ lifetime histogram
    ax = axes[1, 0]
    if len(h1_lifetimes) > 0:
        ax.hist(h1_lifetimes, bins=30, color='#d62728', alpha=0.7, edgecolor='black', lw=0.5)
        ax.axvline(np.median(h1_lifetimes), color='black', ls='--', lw=1.5, label=f'Median = {np.median(h1_lifetimes):.5f}')
        ax.legend(fontsize=10)
    ax.set_xlabel("$H_1$ Lifetime (death − birth)", fontsize=11)
    ax.set_ylabel("Count", fontsize=11)
    ax.set_title(f"Panel C: $H_1$ Cycle Lifetime Distribution ($n = {len(h1_pairs)}$)", fontsize=11, fontweight='bold')
    ax.grid(True, ls=':', alpha=0.4)

    # Panel D: Euler Characteristic Transform
    ax = axes[1, 1]
    if len(thresholds) > 0:
        ax.plot(thresholds * 1000, chi_values, 'b-', lw=2)
        ax.axhline(24, color='#d62728', ls='--', lw=1.5, label='$\\chi(K3) = 24$ (Kummer)')
        ax.legend(fontsize=10)
    ax.set_xlabel("Filtration threshold $\\nu$ [×10³ deg²]", fontsize=11)
    ax.set_ylabel("$\\chi(\\nu)$ (Euler Characteristic)", fontsize=11)
    ax.set_title("Panel D: Euler Characteristic Transform $\\chi(\\nu)$", fontsize=11, fontweight='bold')
    ax.grid(True, ls=':', alpha=0.4)

    plt.suptitle("Topological Data Analysis: Euclid Q1 Persistent Homology & Euler Transform",
                 fontsize=13, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "tda_euclid_q1_persistence.pdf", dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"Figure saved to {FIG_DIR / 'tda_euclid_q1_persistence.pdf'}")

if __name__ == "__main__":
    main()
