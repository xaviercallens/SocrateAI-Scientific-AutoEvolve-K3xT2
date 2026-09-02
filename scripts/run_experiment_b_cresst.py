#!/usr/bin/env python3
"""
Expérience B (v2) : Estimation Paramétrique de Faisabilité — Recherche
Balistique BPS dans les Bolomètres Cryogéniques
====================================================================
Corrections appliquées par rapport à v1 (audit peer_review.md) :
  V-B1: Résolution de la contradiction énergie (recul nucléaire 185 keV
        vs fenêtre 15-80 eV). Le recul correct est ~185 keV pour un
        objet macroscopique. La fenêtre 15-80 eV était erronée.
  V-B2: Ré-étiqueté comme "Estimation Paramétrique" (pas de data-mining).
  V-B3: Géométrie collinéaire modélisée à partir de la tour CRESST-III.
  V-B4: Exposition requise clairement étiquetée comme non réalisable.

NOTE: Ce script est une ESTIMATION PARAMÉTRIQUE de faisabilité.
Il ne traite AUCUNE donnée CRESST-III réelle.
"""

import json
import logging
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

OUT_DIR = Path("outputs/experiments")
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR = Path("paper/figures")

# Physical constants
c_mks = 2.998e8         # m/s
G_N = 6.674e-11         # N m² / kg²


def main():
    logger.info("=" * 70)
    logger.info("  Expérience B (v2) : Estimation Paramétrique — Faisabilité")
    logger.info("  Recherche Balistique BPS dans Bolomètres Cryogéniques")
    logger.info("  [Correction : PAS de data-mining, estimation théorique]")
    logger.info("=" * 70)

    # ─── K3xT2 BPS relic parameters ──────────────────────────────────────
    M_relic_ug = 21.76
    M_relic_kg = M_relic_ug * 1e-9  # kg
    v_halo = 220e3                   # m/s
    v_esc = 544e3                    # m/s

    # ─── CRESST-III detector geometry (V-B3 fix: realistic geometry) ──────
    # CRESST-III: 10 CaWO₄ detector modules in a tower arrangement
    # Each module: ~24g crystal, cylindrical, ∅40mm × h20mm
    crystal_diameter_m = 0.040
    crystal_height_m = 0.020
    crystal_mass_kg = 0.024
    crystal_spacing_m = 0.030       # 3 cm center-to-center vertical
    n_crystals = 10
    threshold_eV = 30.0             # Corrected: realistic phonon threshold
    exposure_kg_day = 5.6           # Total CRESST-III Run 34 exposure

    # V-B3 fix: Model the collinear probability from the real tower geometry
    # A relic traversing the tower must intercept ≥3 crystals in a vertical stack
    # Cross-section of each crystal: π(d/2)² ≈ 12.57 cm²
    A_crystal_cm2 = np.pi * (crystal_diameter_m * 100 / 2)**2
    # Tower total height: n × spacing
    tower_height_m = n_crystals * crystal_spacing_m
    # Solid angle subtended by the crystal from 1 crystal-spacing above
    # = A_crystal / (4π × d²)
    # For ≥3 collinear hits, the relic must pass through a cylinder of
    # diameter 40mm and length ≥ 3×30mm = 90mm
    # Probability of intercepting ≥3 in a row, averaged over isotropic directions:
    # This is geometric: ~(crystal_area / tower_cross_section_at_angle)
    # For a vertical stack, near-vertical trajectories have high probability,
    # but at angle θ from vertical, the effective overlap drops as cos(θ)
    # Integrate over 2π solid angle: P(≥3) ≈ (A_crystal / (4π d²))² for uncorrelated
    f_collinear = (A_crystal_cm2 / (4 * np.pi * (crystal_spacing_m * 100)**2))**2
    # But crystals are aligned, so vertical trajectories always hit all: add a factor
    # for the solid-angle cone within which all ≥3 crystals are intercepted
    omega_cone = A_crystal_cm2 / (crystal_spacing_m * 100)**2  # sr ~ 0.14
    f_collinear = omega_cone / (4 * np.pi)  # fraction of sky
    logger.info(f"Collinear cone solid angle: Ω = {omega_cone:.4f} sr")
    logger.info(f"Collinear fraction: f = Ω/(4π) = {f_collinear:.4f} ({f_collinear*100:.2f}%)")

    # ─── Timing signature ─────────────────────────────────────────────────
    delta_t = crystal_spacing_m / v_halo
    delta_t_ns = delta_t * 1e9

    logger.info(f"\nBPS Relic Mass: M = {M_relic_ug} μg = {M_relic_kg:.3e} kg")
    logger.info(f"Halo velocity: v = {v_halo/1e3:.0f} km/s")
    logger.info(f"Crystal spacing: Δz = {crystal_spacing_m*100:.0f} cm")
    logger.info(f"Inter-crystal delay: Δt = {delta_t_ns:.1f} ns")

    # ─── Number density and flux ──────────────────────────────────────────
    rho_dm_local = 0.3  # GeV/cm³
    rho_dm_local_kg = rho_dm_local * 1.783e-27  # kg/cm³
    n_relic = rho_dm_local_kg / M_relic_kg
    flux = n_relic * v_halo * 1e2  # per cm² per second
    logger.info(f"Local DM density: ρ = {rho_dm_local} GeV/cm³")
    logger.info(f"BPS relic number density: n = {n_relic:.3e} /cm³")
    logger.info(f"BPS relic flux: Φ = {flux:.3e} /cm²/s")

    # ─── V-B1 fix: Correct energy deposit ─────────────────────────────────
    # For a macroscopic BPS relic (M >> m_nucleus), the elastic nuclear recoil
    # energy is E_r = 2 m_N v² (max head-on transfer).
    # For W (A=184): m_W = 184 × 1.66e-27 = 3.05e-25 kg
    m_W_kg = 184 * 1.66e-27
    m_Ca_kg = 40 * 1.66e-27
    m_O_kg = 16 * 1.66e-27

    E_recoil_W = 2 * m_W_kg * v_halo**2 / 1.602e-19   # eV
    E_recoil_Ca = 2 * m_Ca_kg * v_halo**2 / 1.602e-19  # eV
    E_recoil_O = 2 * m_O_kg * v_halo**2 / 1.602e-19    # eV

    logger.info(f"\n--- V-B1 Corrected Energy Deposit ---")
    logger.info(f"  IMPORTANT: Previous 15-80 eV window was ERRONEOUS.")
    logger.info(f"  A macroscopic (M >> m_nucleus) relic deposits maximum recoil:")
    logger.info(f"    W nucleus:  E_r = {E_recoil_W:.0f} eV = {E_recoil_W/1e3:.1f} keV")
    logger.info(f"    Ca nucleus: E_r = {E_recoil_Ca:.0f} eV = {E_recoil_Ca/1e3:.1f} keV")
    logger.info(f"    O nucleus:  E_r = {E_recoil_O:.0f} eV = {E_recoil_O/1e3:.1f} keV")
    logger.info(f"  These are ABOVE any cryogenic threshold. The signal is a")
    logger.info(f"  ~100-200 keV nuclear recoil cascade, NOT a sub-100 eV phonon event.")
    logger.info(f"  Analysis window should be 10-500 keV, not 15-80 eV.")

    # Corrected analysis window
    E_window_low = 10e3    # eV (10 keV)
    E_window_high = 500e3  # eV (500 keV)

    # ─── Event rate ────────────────────────────────────────────────────────
    # Single crystal rate
    rate_single_per_crystal = flux * A_crystal_cm2  # events / crystal / second
    rate_total = rate_single_per_crystal * n_crystals
    rate_collinear = flux * A_crystal_cm2 * f_collinear  # ≥3-crystal coincidence per second
    rate_collinear_per_day = rate_collinear * 86400

    logger.info(f"\n--- Event Rate ---")
    logger.info(f"  Single-crystal rate: {rate_single_per_crystal:.3e} /crystal/s")
    logger.info(f"  Total (all crystals): {rate_total:.3e} /s")
    logger.info(f"  Collinear (≥3 crystals): {rate_collinear:.3e} /s = {rate_collinear_per_day:.6f} /day")

    # ─── Expected events in archive ───────────────────────────────────────
    n_days = exposure_kg_day / (n_crystals * crystal_mass_kg)
    n_events_single = rate_total * n_days * 86400
    n_events_collinear = rate_collinear * n_days * 86400

    logger.info(f"\n--- Expected Events (CRESST-III Run 34: {exposure_kg_day} kg·day) ---")
    logger.info(f"  Effective days: {n_days:.1f}")
    logger.info(f"  Single-crystal events: {n_events_single:.4f}")
    logger.info(f"  Collinear events: {n_events_collinear:.6f}")

    # ─── V-B4: Required exposure for detection ────────────────────────────
    # Need ~3 events for 3σ Poisson significance (bkg ≈ 0 with timing cut)
    n_target = 3.0
    if rate_collinear > 0:
        t_required_s = n_target / rate_collinear
        t_required_days = t_required_s / 86400
        exposure_required = t_required_days * n_crystals * crystal_mass_kg
    else:
        exposure_required = float('inf')
        t_required_days = float('inf')

    logger.info(f"\n--- V-B4: Required Exposure for 3-event Detection ---")
    logger.info(f"  Required observation time: {t_required_days:.0f} days = {t_required_days/365.25:.0f} years")
    logger.info(f"  Required exposure: {exposure_required:.0f} kg·days = {exposure_required/1e3:.0f} t·days")
    logger.info(f"  VERDICT: {'FEASIBLE' if exposure_required < 1e6 else 'NOT FEASIBLE'} with current technology")
    logger.info(f"  (For reference: XENON1T = ~1 t·yr ≈ 365 t·days; DARWIN = ~200 t·yr)")

    # ─── Background in corrected window ───────────────────────────────────
    bkg_rate_keV = 3.0  # events / keV / kg / day (flat background at 10-500 keV)
    bkg_window = bkg_rate_keV * (E_window_high - E_window_low) / 1e3 * exposure_kg_day
    logger.info(f"\n--- Background (corrected 10-500 keV window) ---")
    logger.info(f"  Background rate: ~{bkg_rate_keV} /keV/kg/day")
    logger.info(f"  Events in window: {bkg_window:.0f}")
    logger.info(f"  After multi-crystal timing cut (Δt = {delta_t_ns:.0f} ns): ~{bkg_window * 1e-5:.3f}")

    # ─── Save results ─────────────────────────────────────────────────────
    results = {
        "version": "v2_audited",
        "type": "PARAMETRIC_ESTIMATION_NOT_DATA_MINING",
        "M_relic_ug": M_relic_ug,
        "v_halo_km_s": v_halo / 1e3,
        "delta_t_ns": round(delta_t_ns, 1),
        "collinear_fraction": round(f_collinear, 5),
        "collinear_cone_sr": round(omega_cone, 4),
        "energy_deposit": {
            "NOTE": "V-B1 CORRECTED: Macroscopic relic deposits ~100-200 keV nuclear recoil, NOT 15-80 eV",
            "E_recoil_W_keV": round(E_recoil_W / 1e3, 1),
            "E_recoil_Ca_keV": round(E_recoil_Ca / 1e3, 1),
            "E_recoil_O_keV": round(E_recoil_O / 1e3, 1),
            "analysis_window_keV": [E_window_low / 1e3, E_window_high / 1e3],
        },
        "flux_per_cm2_s": f"{flux:.3e}",
        "rate_single_per_s": f"{rate_total:.3e}",
        "rate_collinear_per_day": round(rate_collinear_per_day, 8),
        "n_expected_single": round(n_events_single, 4),
        "n_expected_collinear": round(n_events_collinear, 6),
        "exposure_required_kg_day": round(exposure_required, 0) if np.isfinite(exposure_required) else "INFINITE",
        "feasibility": "NOT FEASIBLE with current cryogenic detector technology",
    }
    with open(OUT_DIR / "cresst_ballistic_estimation_v2.json", "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"\nResults saved to {OUT_DIR / 'cresst_ballistic_estimation_v2.json'}")

    # ─── Plot ─────────────────────────────────────────────────────────────
    v_arr = np.linspace(50e3, v_esc, 200)
    v0 = 220e3
    f_v = 4 * np.pi * v_arr**2 * np.exp(-v_arr**2 / v0**2) / (np.pi * v0**2)**1.5
    f_v[v_arr > v_esc] = 0
    f_v /= np.trapezoid(f_v, v_arr)
    dt_arr = crystal_spacing_m / v_arr * 1e9

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # Panel A: Velocity distribution
    ax = axes[0]
    ax.plot(v_arr / 1e3, f_v * 1e3, 'b-', lw=2)
    ax.axvline(220, color='#d62728', ls='--', lw=1.5, label='$v_{\\rm halo} = 220$ km/s')
    ax.axvline(544, color='gray', ls=':', lw=1, label='$v_{\\rm esc} = 544$ km/s')
    ax.set_xlabel("Velocity $v$ [km/s]", fontsize=12)
    ax.set_ylabel("$f(v)$ [$10^{-3}$ s/m]", fontsize=12)
    ax.set_title("Panel A: Halo Velocity Distribution", fontsize=11, fontweight='bold')
    ax.legend(fontsize=9)
    ax.grid(True, ls=':', alpha=0.4)

    # Panel B: Timing delay
    ax = axes[1]
    ax.plot(v_arr / 1e3, dt_arr, 'k-', lw=2)
    ax.axhline(delta_t_ns, color='#d62728', ls='--', lw=1.5,
               label=f'$\\Delta t({v_halo/1e3:.0f}$ km/s$) = {delta_t_ns:.0f}$ ns')
    ax.fill_between(v_arr / 1e3, dt_arr, alpha=0.1, color='#1f77b4')
    ax.set_xlabel("Velocity $v$ [km/s]", fontsize=12)
    ax.set_ylabel("Inter-crystal delay $\\Delta t$ [ns]", fontsize=12)
    ax.set_title("Panel B: Timing Signature (3 cm spacing)", fontsize=11, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, ls=':', alpha=0.4)
    ax.set_ylim(0, 600)

    # Panel C: CORRECTED energy deposit (V-B1 fix)
    ax = axes[2]
    # Show nuclear recoil spectrum for all 3 targets in CaWO₄
    for label, E_max, color in [
        ("W ($A=184$)", E_recoil_W, '#1f77b4'),
        ("Ca ($A=40$)", E_recoil_Ca, '#ff7f0e'),
        ("O ($A=16$)", E_recoil_O, '#2ca02c')
    ]:
        E_arr = np.linspace(0.1e3, E_max * 1.2, 200)
        # Flat differential rate up to kinematic maximum
        spectrum = np.where(E_arr <= E_max, 1.0 / E_max, 0.0)
        ax.fill_between(E_arr / 1e3, spectrum * 1e3, alpha=0.2, color=color)
        ax.plot(E_arr / 1e3, spectrum * 1e3, '-', color=color, lw=1.5, label=label)
    ax.axvspan(E_window_low / 1e3, E_window_high / 1e3, alpha=0.08, color='gray',
               label=f'Window [{E_window_low/1e3:.0f}–{E_window_high/1e3:.0f}] keV')
    ax.set_xlabel("Nuclear Recoil Energy $E_r$ [keV]", fontsize=12)
    ax.set_ylabel("$dR/dE_r$ [$10^{-3}$ arb.]", fontsize=12)
    ax.set_title("Panel C: Corrected Recoil Spectrum (V-B1)", fontsize=11, fontweight='bold')
    ax.legend(fontsize=8, loc='upper right')
    ax.grid(True, ls=':', alpha=0.4)
    ax.set_xlim(0, 250)

    plt.suptitle(
        f"Parametric Feasibility Estimate: BPS Relic Search "
        f"($M = {M_relic_ug}\\,\\mu$g, $\\Phi \\sim {flux:.0e}$ cm$^{{-2}}$s$^{{-1}}$)",
        fontsize=12, fontweight='bold')
    plt.tight_layout()
    plt.savefig(FIG_DIR / "experiment_b_cresst_ballistic_v2.pdf", dpi=300)
    plt.close()
    logger.info(f"Figure saved to {FIG_DIR / 'experiment_b_cresst_ballistic_v2.pdf'}")


if __name__ == "__main__":
    main()
