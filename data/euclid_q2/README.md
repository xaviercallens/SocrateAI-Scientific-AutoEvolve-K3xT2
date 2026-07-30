# stream3_euclid_q2 — Weak Lensing S₈ Data Stream

## Important Note on Euclid Q2

**Euclid Q2 (June 2026) = Galactic Bulge Survey (EGBS)** — stellar microlensing,
NOT cosmic shear. It does not contain weak lensing cosmology data.

The first Euclid **cosmic shear** data release is **Euclid DR1**, scheduled October 2026.

This stream therefore contains the best available precursor weak lensing data:

## Data Contents

| File | Description | Source |
|------|-------------|--------|
| `s8_wl_measurements.json` | Published S₈ constraints from KiDS-1000, DES-Y3, KiDS-Legacy, Planck, Euclid-DR1-forecast | See individual references |
| `kids1000_bandpowers_EE.json` | KiDS-1000 EE bandpower data vector (5 tomo bins × 8 ℓ bins) | Asgari+2021 Table A1 |
| `kids1000_bandpowers_EE.npy` | Same as above, NumPy binary format | Asgari+2021 |
| `s8_joint_covariance.txt` | 4×4 diagonal covariance for joint S₈ analysis | Compiled from published σ values |
| `s8_joint_means.txt` | S₈ mean values vector (KiDS-1000, DES-Y3, KiDS-Legacy, Planck) | Compiled from published values |

## Primary References

1. **KiDS-1000**: Asgari et al. 2021, A&A 645, A104, arXiv:2007.15633
2. **DES-Y3**: Amon et al. 2022, PRD 105, 023514, arXiv:2105.13543  
3. **KiDS-Legacy**: Li et al. 2023, A&A 679, A133, arXiv:2304.00702
4. **Planck 2018**: Planck Collaboration 2020, A&A 641, A6, arXiv:1807.06209
5. **Euclid DR1 forecast**: Euclid Collaboration 2024, arXiv:2405.13491

## Pipeline Integration

These data are consumed by `src/mcmc/s8_likelihood.py` which implements
the Gaussian S₈ likelihood:

    L(S₈_model) = N(S₈_KiDS | 0.759, 0.024²) × N(S₈_DES | 0.776, 0.017²)
