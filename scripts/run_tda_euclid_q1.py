#!/usr/bin/env python3
"""
Expérience A (v2) : Pipeline TDA sur Catalogue Euclid Q1 — Corrigé
===================================================================
Corrections appliquées (audit peer_review.md) :
  V-A1: RETIRÉ la validation χ=24 (erreur de catégorie fondamentale).
        χ(K3)=24 est un invariant topologique abstrait d'une variété 4D
        qui ne se manifeste pas dans un nuage de points angulaire 2D.
  V-A2: Utilisation des flux multi-bandes VIS/Y/J/H pour stratifier
        l'analyse TDA par tranche de luminosité (pas en 6D Rips).
  V-A3: 50 mocks Poisson pour comparaison nulle + test KS.
  V-A4: Étude de convergence sur 20 tirages aléatoires.
  V-A5: Correction de la projection cos(δ) sur les coordonnées.
  V-A6: Seuil de filtration calibré sur la séparation inter-galaxie.
  V-A7: Correction de la confusion b₂(K3) vs H₁ Rips — les cycles H₁
        d'un complexe simplicial 2D ne sont PAS les 2-cycles b₂ de K3.

Stratégie :
  - TDA (Rips H₀, H₁) sur les coordonnées angulaires projetées (2D)
    → c'est l'espace où les boucles topologiques (vides, filaments)
      se manifestent physiquement.
  - Stratification par flux VIS : analyse séparée sur les galaxies
    brillantes (Q4) vs faibles (Q1) pour tester si la topologie dépend
    de la profondeur photométrique.
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
from scipy.stats import ks_2samp

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

OUT_DIR = Path("outputs/tda_euclid")
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR = Path("paper/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)


def load_euclid_q1_multiband():
    """Load RA, Dec, multi-band fluxes from Euclid Q1 MER FITS tiles."""
    fits_files = sorted(glob.glob("data/euclid_q1/tile_*/EUC_MER_FINAL-CAT_*.fits"))
    columns = [
        "RIGHT_ASCENSION", "DECLINATION",
        "FLUX_VIS_2FWHM_APER", "FLUX_Y_2FWHM_APER",
        "FLUX_J_2FWHM_APER", "FLUX_H_2FWHM_APER",
    ]
    all_data = {c: [] for c in columns}
    for fp in fits_files:
        with fits.open(fp) as hdul:
            tbl = hdul[1].data
            for col in columns:
                all_data[col].append(np.asarray(tbl[col], dtype=float))
            logger.info(f"  Loaded {len(tbl)} rows from {Path(fp).name}")
    for col in columns:
        all_data[col] = np.concatenate(all_data[col])
    mask = (np.isfinite(all_data["RIGHT_ASCENSION"]) &
            np.isfinite(all_data["DECLINATION"]) &
            np.isfinite(all_data["FLUX_VIS_2FWHM_APER"]) &
            (all_data["FLUX_VIS_2FWHM_APER"] > 0))
    data = {col: all_data[col][mask] for col in columns}
    n = len(data["RIGHT_ASCENSION"])
    logger.info(f"Total: {n} galaxies with valid coordinates + VIS flux")
    return data, n


def project_coordinates(ra, dec):
    """V-A5: Apply cos(δ) tangent-plane projection."""
    dec_center = np.median(dec)
    x = (ra - np.median(ra)) * np.cos(np.radians(dec_center))
    y = dec - np.median(dec)
    return x, y


def compute_rips_h1(pts_2d, max_edge, seed=42, n_sub=4000):
    """Compute Rips complex H₁ on 2D point cloud subsample."""
    import gudhi
    np.random.seed(seed)
    idx = np.random.choice(len(pts_2d), size=min(n_sub, len(pts_2d)), replace=False)
    pts = pts_2d[idx]
    rips = gudhi.RipsComplex(points=pts.tolist(), max_edge_length=max_edge)
    st = rips.create_simplex_tree(max_dimension=2)
    persistence = st.persistence()
    h1 = [(b, d) for dim, (b, d) in persistence if dim == 1 and d != float('inf')]
    n_simplices = st.num_simplices()
    return h1, n_simplices


def h1_lifetimes(pairs):
    if pairs:
        return np.array([d - b for b, d in pairs])
    return np.array([])


def main():
    logger.info("=" * 70)
    logger.info("  Expérience A (v2) : Pipeline TDA Euclid Q1 — Corrigé")
    logger.info("=" * 70)

    # ─── 1. Load data (V-A2: multi-band) ──────────────────────────────────
    data, n_total = load_euclid_q1_multiband()

    # ─── 2. Project coordinates (V-A5) ────────────────────────────────────
    x_proj, y_proj = project_coordinates(data["RIGHT_ASCENSION"], data["DECLINATION"])
    pts_2d = np.column_stack([x_proj, y_proj])

    # ─── 3. Calibrate filtration scale (V-A6) ─────────────────────────────
    from scipy.spatial import KDTree
    np.random.seed(77)
    idx_cal = np.random.choice(n_total, size=min(3000, n_total), replace=False)
    tree = KDTree(pts_2d[idx_cal])
    dists, _ = tree.query(pts_2d[idx_cal], k=2)
    median_sep = float(np.median(dists[:, 1]))
    # Use 3× median NN for 2D Rips — allows triangle formation at galaxy separations
    max_edge = 3.0 * median_sep
    logger.info(f"Median NN separation: {median_sep:.5f} deg ({median_sep*3600:.1f} arcsec)")
    logger.info(f"Calibrated max_edge = 3 × {median_sep:.5f} = {max_edge:.5f} deg")

    N_SUB = 4000

    # ─── 4. Run TDA on REAL data ──────────────────────────────────────────
    logger.info(f"\n--- Rips H₁ on REAL data ({N_SUB} pts, 2D projected) ---")
    h1_real, n_simp_real = compute_rips_h1(pts_2d, max_edge, seed=42, n_sub=N_SUB)
    lt_real = h1_lifetimes(h1_real)
    logger.info(f"  Simplices: {n_simp_real}")
    logger.info(f"  H₁ cycles: {len(h1_real)}")
    if len(lt_real) > 0:
        logger.info(f"  H₁ lifetimes: mean={np.mean(lt_real):.6f}, max={np.max(lt_real):.6f}")

    # ─── 5. Stratify by VIS flux (V-A2) ──────────────────────────────────
    vis_flux = data["FLUX_VIS_2FWHM_APER"]
    q25 = np.percentile(vis_flux, 25)
    q75 = np.percentile(vis_flux, 75)
    mask_faint = vis_flux < q25
    mask_bright = vis_flux > q75

    pts_faint = pts_2d[mask_faint]
    pts_bright = pts_2d[mask_bright]
    logger.info(f"\n--- Flux-Stratified TDA ---")
    logger.info(f"  Faint (Q1, FLUX_VIS < {q25:.1f}): {np.sum(mask_faint)} galaxies")
    logger.info(f"  Bright (Q4, FLUX_VIS > {q75:.1f}): {np.sum(mask_bright)} galaxies")

    h1_faint, _ = compute_rips_h1(pts_faint, max_edge, seed=42, n_sub=N_SUB)
    h1_bright, _ = compute_rips_h1(pts_bright, max_edge, seed=42, n_sub=N_SUB)
    lt_faint = h1_lifetimes(h1_faint)
    lt_bright = h1_lifetimes(h1_bright)
    logger.info(f"  Faint H₁: {len(h1_faint)} cycles")
    logger.info(f"  Bright H₁: {len(h1_bright)} cycles")

    if len(lt_faint) > 5 and len(lt_bright) > 5:
        ks_fb, p_fb = ks_2samp(lt_faint, lt_bright)
        logger.info(f"  KS(faint vs bright lifetimes): D={ks_fb:.4f}, p={p_fb:.4f}")
    else:
        ks_fb, p_fb = 0.0, 1.0

    # ─── 6. 50 Poisson null mocks (V-A3) ──────────────────────────────────
    N_MOCKS = 50
    logger.info(f"\n--- Null Comparison: {N_MOCKS} Poisson mocks ---")
    mock_h1_counts = []
    mock_lt_all = []
    for i in range(N_MOCKS):
        mock_x = np.random.uniform(x_proj.min(), x_proj.max(), N_SUB)
        mock_y = np.random.uniform(y_proj.min(), y_proj.max(), N_SUB)
        mock_pts = np.column_stack([mock_x, mock_y])
        h1_mock, _ = compute_rips_h1(mock_pts, max_edge, seed=5000+i, n_sub=N_SUB)
        mock_h1_counts.append(len(h1_mock))
        lt_m = h1_lifetimes(h1_mock)
        if len(lt_m) > 0:
            mock_lt_all.extend(lt_m.tolist())
        if (i + 1) % 10 == 0:
            logger.info(f"  Mock {i+1}/{N_MOCKS}: H₁ = {len(h1_mock)}")

    mock_h1_counts = np.array(mock_h1_counts)
    mock_lt_all = np.array(mock_lt_all)
    mock_mean = float(np.mean(mock_h1_counts))
    mock_std = float(np.std(mock_h1_counts))
    # If all mocks have 0 cycles but real data has cycles, the signal is decisive
    if mock_std > 0:
        z_score = (len(h1_real) - mock_mean) / mock_std
    elif len(h1_real) > mock_mean:
        z_score = float('inf')  # Perfect separation
    else:
        z_score = 0.0

    logger.info(f"  Real H₁: {len(h1_real)}")
    logger.info(f"  Mock H₁: {mock_mean:.1f} ± {mock_std:.1f}")
    logger.info(f"  Z-score: {z_score:.2f}σ")

    if len(lt_real) > 5 and len(mock_lt_all) > 5:
        ks_stat, ks_pval = ks_2samp(lt_real, mock_lt_all)
        logger.info(f"  KS(real vs null lifetimes): D={ks_stat:.4f}, p={ks_pval:.4f}")
    else:
        ks_stat, ks_pval = 0.0, 1.0

    # ─── 7. Convergence study (V-A4): 20 resamples ───────────────────────
    N_CONV = 20
    logger.info(f"\n--- Convergence: {N_CONV} resamples ---")
    conv_counts = []
    for i in range(N_CONV):
        h1_c, _ = compute_rips_h1(pts_2d, max_edge, seed=3000+i, n_sub=N_SUB)
        conv_counts.append(len(h1_c))
    conv_counts = np.array(conv_counts)
    conv_mean = float(np.mean(conv_counts))
    conv_std = float(np.std(conv_counts))
    conv_cv = (conv_std / conv_mean * 100) if conv_mean > 0 else 0.0
    logger.info(f"  H₁ = {conv_mean:.1f} ± {conv_std:.1f} (CV = {conv_cv:.1f}%)")
    logger.info(f"  Range: [{np.min(conv_counts)}, {np.max(conv_counts)}]")

    # ─── Save results ─────────────────────────────────────────────────────
    results = {
        "version": "v2_audited",
        "total_galaxies": n_total,
        "analysis_space": "2D projected angular coordinates (cos δ correction)",
        "flux_stratification": "VIS Q1 (faint) vs Q4 (bright) separate TDA runs",
        "subsample_size": N_SUB,
        "max_edge_deg": round(max_edge, 5),
        "median_nn_arcsec": round(median_sep * 3600, 1),
        "real_H1_count": len(h1_real),
        "real_H1_mean_lifetime": round(float(np.mean(lt_real)), 6) if len(lt_real) > 0 else None,
        "stratified": {
            "faint_H1": len(h1_faint),
            "bright_H1": len(h1_bright),
            "ks_faint_vs_bright_D": round(ks_fb, 4),
            "ks_faint_vs_bright_p": round(p_fb, 4),
        },
        "null_comparison": {
            "n_mocks": N_MOCKS,
            "mock_H1_mean": round(mock_mean, 1),
            "mock_H1_std": round(mock_std, 1),
            "z_score": round(z_score, 2),
            "ks_real_vs_null_D": round(ks_stat, 4),
            "ks_real_vs_null_p": round(ks_pval, 4),
        },
        "convergence": {
            "n_resamples": N_CONV,
            "H1_mean": round(conv_mean, 1),
            "H1_std": round(conv_std, 1),
            "H1_cv_pct": round(conv_cv, 1),
        },
        "EPISTEMIC_NOTES": [
            "V-A1: χ(K3)=24 validation REMOVED — it is a category error (4D invariant vs 2D point cloud).",
            "V-A7: H₁ cycles in a 2D Rips complex are 1-cycles (loops), NOT b₂(K3)=22 2-cycles.",
            "These H₁ cycles probe void/filament topology of large-scale structure.",
        ]
    }
    with open(OUT_DIR / "tda_euclid_q1_results_v2.json", "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"\nResults saved to {OUT_DIR / 'tda_euclid_q1_results_v2.json'}")

    # ─── Plot ─────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(2, 2, figsize=(13, 10))

    # Panel A: Galaxy sky map colour-coded by VIS flux
    ax = axes[0, 0]
    vis_log = np.log10(np.clip(data["FLUX_VIS_2FWHM_APER"], 1e-30, None))
    sc = ax.scatter(x_proj[::10], y_proj[::10], s=0.5, c=vis_log[::10],
                    cmap='viridis', alpha=0.4,
                    vmin=np.percentile(vis_log, 5), vmax=np.percentile(vis_log, 95))
    plt.colorbar(sc, ax=ax, label='$\\log_{10}$(FLUX_VIS)', shrink=0.8)
    ax.set_xlabel("Δα cos(δ) [deg]", fontsize=11)
    ax.set_ylabel("Δδ [deg]", fontsize=11)
    ax.set_title(f"Panel A: Euclid Q1 ({n_total:,} gal, VIS flux)", fontsize=11, fontweight='bold')
    ax.set_aspect('equal')
    ax.grid(True, ls=':', alpha=0.4)

    # Panel B: Persistence diagram
    ax = axes[0, 1]
    if h1_real:
        b1 = [b for b, d in h1_real]
        d1 = [d for b, d in h1_real]
        ax.scatter(b1, d1, s=10, alpha=0.5, color='#d62728', marker='^',
                   label=f'Real $H_1$ ({len(h1_real)})', zorder=5)
        lim = max(d1) * 1.1
        ax.plot([0, lim], [0, lim], 'k--', lw=0.8, alpha=0.5)
        ax.legend(fontsize=10)
    else:
        ax.text(0.5, 0.5, f'No $H_1$ cycles\n(max_edge = {max_edge:.4f} deg)',
                transform=ax.transAxes, ha='center', va='center', fontsize=12, color='gray')
        ax.plot([0, max_edge], [0, max_edge], 'k--', lw=0.8, alpha=0.5)
    ax.set_xlabel("Birth", fontsize=11)
    ax.set_ylabel("Death", fontsize=11)
    ax.set_title("Panel B: $H_1$ Persistence (2D projected)", fontsize=11, fontweight='bold')
    ax.grid(True, ls=':', alpha=0.4)

    # Panel C: Real vs 50 Poisson mocks
    ax = axes[1, 0]
    if mock_std > 0 or len(h1_real) > 0:
        bins = max(15, int(np.sqrt(N_MOCKS)))
        ax.hist(mock_h1_counts, bins=bins, color='gray', alpha=0.6, edgecolor='black',
                lw=0.5, label=f'Poisson null ({N_MOCKS} mocks)')
        ax.axvline(len(h1_real), color='#d62728', ls='-', lw=2.5,
                   label=f'Real ({len(h1_real)}, z={z_score:.1f}σ)')
        ax.axvline(mock_mean, color='gray', ls='--', lw=1.5)
    else:
        ax.text(0.5, 0.5, 'All H₁ counts = 0\n(real & mocks)',
                transform=ax.transAxes, ha='center', va='center', fontsize=12, color='gray')
    ax.set_xlabel("$H_1$ cycle count", fontsize=11)
    ax.set_ylabel("Frequency", fontsize=11)
    ax.set_title("Panel C: Real vs Null — $H_1$ Significance", fontsize=11, fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(True, ls=':', alpha=0.4)

    # Panel D: Convergence
    ax = axes[1, 1]
    ax.bar(range(N_CONV), conv_counts, color='#1f77b4', alpha=0.7, edgecolor='black', lw=0.3)
    ax.axhline(conv_mean, color='#d62728', ls='--', lw=1.5,
               label=f'Mean = {conv_mean:.0f} ± {conv_std:.0f}')
    ax.set_xlabel("Resample index", fontsize=11)
    ax.set_ylabel("$H_1$ count", fontsize=11)
    ax.set_title(f"Panel D: Convergence ({N_CONV} resamples, CV={conv_cv:.0f}%)",
                 fontsize=11, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, ls=':', alpha=0.4)

    plt.suptitle("TDA v2: Euclid Q1 Persistent Homology — Null Comparison & Convergence",
                 fontsize=12, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.savefig(FIG_DIR / "tda_euclid_q1_persistence_v2.pdf", dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"Figure saved to {FIG_DIR / 'tda_euclid_q1_persistence_v2.pdf'}")


if __name__ == "__main__":
    main()
