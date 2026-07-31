# K3×T² Astrophysics Dashboard — GCP Web Application Specification

**Version:** 1.0  
**Date:** 2026-07-31  
**Target Executors:** Gemini 3.6 Flash (High), Gemini 3.1 Pro  
**Deployment Target:** Google Cloud Platform (Cloud Run + Cloud Storage)

---

## 1. Product Vision

A real-time web dashboard for astrophysicists to visually explore, validate, and compare the K3×T² hypergraph cosmological model against observational data (DESI BAO, NANOGrav PTA, KiDS-1000, Euclid Q1). The dashboard enables interactive parameter exploration, live χ² computation, and publication-ready figure export.

---

## 2. Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Browser (Client)                   │
│  Vite + React + Recharts/Plotly.js                   │
│  - Parameter sliders (Ωm, H0, w0, τ, S8)            │
│  - Real-time χ² readout                              │
│  - Interactive plots (BAO residuals, strain spectra)  │
│  - Data provenance audit panel                       │
└──────────────────┬───────────────────────────────────┘
                   │ HTTPS (JSON API)
┌──────────────────▼───────────────────────────────────┐
│              Cloud Run (Backend API)                  │
│  Python FastAPI                                      │
│  - /api/bao-chi2          (DESI BAO computation)     │
│  - /api/gw-spectrum       (PTA strain prediction)    │
│  - /api/s8-tension        (S8 survey comparison)     │
│  - /api/kids-bmode        (B-mode null test)         │
│  - /api/fisher-hessian    (FIM curvature)            │
│  - /api/data-cartography  (data lake inventory)      │
└──────────────────┬───────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────┐
│           Cloud Storage (Data Lake)                   │
│  gs://socrateai-datalake-.../                        │
│  - desi_dr1/          (BAO measurements)             │
│  - nanograv_15yr/     (PTA free spectrum)             │
│  - euclid_q1/         (FITS catalogs)                │
│  - stream3_euclid_q2/ (KiDS-1000 bandpowers)        │
└──────────────────────────────────────────────────────┘
```

---

## 3. Pages & Components

### Page 1: Mission Control (Home)
**Route:** `/`

**Purpose:** Overview of the K3×T² model status with live health indicators.

**Components:**

| Component | Description | Data Source |
|-----------|-------------|-------------|
| Model Summary Card | Shows MAP cosmology: w0, Ωm, H0, S8, τ, Picard # | Static JSON |
| Data Lake Status | Table showing all 9 survey datasets with sync status | `/api/data-cartography` |
| Evidence Summary | Bayes factor, FIM curvature, χ² per test | Aggregated from all API endpoints |
| Recent Activity Feed | Git commit log from both repos | GitHub API |

**DoD:**
- [ ] Page loads in < 2 seconds
- [ ] All 9 data lake entries displayed with last-sync timestamp
- [ ] Evidence summary shows colored badges: 🟢 (decisive), 🟡 (moderate), 🔴 (inconclusive)
- [ ] Mobile responsive (min-width: 375px)

---

### Page 2: BAO Distance Ladder
**Route:** `/bao`

**Purpose:** Interactive comparison of K3×T² vs ΛCDM vs w0waCDM against DESI BAO data.

**Components:**

| Component | Description |
|-----------|-------------|
| Parameter Panel | Sliders for `Omega_m` (0.1–0.5), `H0` (60–75), `w0` (-1.5–0.0) |
| Distance Plot | D_M/r_s and D_H/r_s vs z, with DESI data points + error bars |
| Residual Plot | (Data - Theory) / σ for each of the 12 bins |
| χ² Readout | Live-updating χ² and χ²/dof as sliders move |
| Model Comparison Table | K3×T², ΛCDM, w0waCDM χ² side by side |

**API Endpoint:** `POST /api/bao-chi2`
```json
// Request
{"Omega_m": 0.300, "H0": 67.40, "w0": -0.99992}

// Response
{
  "chi2": 8.234,
  "chi2_per_dof": 0.916,
  "theory_values": [7.93, 13.61, ...],
  "residuals": [0.01, 0.01, ...],
  "pulls": [0.07, 0.02, ...]
}
```

**Backend Implementation:**
```python
# File: backend/routers/bao.py
# Use the distance calculator from Experiment 1 in experimentation_plan.md
# Load DESI data once at startup (module-level)
# Return theory predictions and chi2 for any (Omega_m, H0, w0) input
```

**DoD:**
- [ ] Slider changes update plot within 200ms
- [ ] DESI data points rendered with correct error bars from covariance diagonal
- [ ] K3×T² MAP preset button loads default sliders
- [ ] ΛCDM preset button loads Planck bestfit
- [ ] Residual plot shows horizontal zero-line with ±1σ and ±2σ bands
- [ ] χ² readout updates in real-time

**Validation:**
- Set sliders to ΛCDM values. χ² should match Experiment 1 output.
- Set sliders to extreme values (Ωm=0.1). χ² should be very large (>100).

---

### Page 3: Gravitational Wave Spectrum
**Route:** `/gw`

**Purpose:** Compare the K4 Oligon strain spectrum against standard SMBHB, with NANOGrav 15yr data overlay.

**Components:**

| Component | Description |
|-----------|-------------|
| Strain Plot | log-log plot of h_c(f) from 1 nHz to 100 nHz |
| Model Toggle | Checkboxes: SMBHB, K4 Oligon, NANOGrav data, SKA sensitivity |
| Resonance Marker | Vertical line at 24.18 nHz with annotation |
| γ Readout | Displays fitted spectral index for each model |
| Slider: Resonance Amplitude | Scale the Compton bump height |

**API Endpoint:** `GET /api/gw-spectrum`
```json
// Response
{
  "frequencies_hz": [...],
  "h_c_smbhb": [...],
  "h_c_oligon": [...],
  "nanograv_data": {"freqs": [...], "strain": [...], "errors": [...]},
  "ska_sensitivity": [...]
}
```

**Backend Implementation:**
```python
# File: backend/routers/gw_spectrum.py  
# Reuse compute_smbhb_spectrum() and compute_oligon_spectrum() from
# scripts/run_phase8_gw_predictions.py
```

**DoD:**
- [ ] Log-log axes with correct decade ranges
- [ ] 24.18 nHz vertical line renders at correct position
- [ ] Toggle checkboxes show/hide each curve
- [ ] SKA sensitivity band is semi-transparent fill
- [ ] Export button saves the plot as SVG

**Validation:**
- SMBHB curve should follow f^(-2/3) exactly
- Oligon curve should visibly diverge from SMBHB above ~10 nHz
- Compton bump should be visible as a local enhancement near 24.18 nHz

---

### Page 4: S8 Tension Monitor
**Route:** `/s8`

**Purpose:** Visualize the S8 tension across all surveys and the K3×T² prediction.

**Components:**

| Component | Description |
|-----------|-------------|
| Whisker Plot | Horizontal error bars for each survey (KiDS, DES, Planck, Euclid Q1) + K3×T² prediction |
| Tension Calculator | Shows σ-tension between any two selected measurements |
| Joint Posterior | Overlapping Gaussian curves for each survey's S8 posterior |
| Verdict Badge | "Resolves tension" / "Same as ΛCDM" / "Worsens tension" |

**API Endpoint:** `GET /api/s8-tension`
```json
// Response
{
  "surveys": [
    {"name": "KiDS-1000", "s8": 0.759, "sigma": 0.024},
    {"name": "DES-Y3", "s8": 0.776, "sigma": 0.017},
    {"name": "Planck-2018", "s8": 0.832, "sigma": 0.013},
    {"name": "K3xT2 Prediction", "s8": 0.830, "sigma": 0.005}
  ],
  "chi2_k3t2_vs_wl": ...,
  "tension_sigma": ...,
  "verdict": "..."
}
```

**DoD:**
- [ ] All survey measurements displayed with correct error bars
- [ ] K3×T² prediction highlighted in distinct color (blue)
- [ ] Tension in σ displayed as a number between any two clicked surveys
- [ ] Verdict badge renders correctly
- [ ] Data loads from `data/euclid_q2/s8_wl_measurements.json`

---

### Page 5: B-Mode Systematics Panel
**Route:** `/bmode`

**Purpose:** Display the KiDS-1000 B-mode null test results.

**Components:**

| Component | Description |
|-----------|-------------|
| EE vs BB Comparison | Side-by-side band power bar charts per ell-bin |
| BB/EE Ratio Plot | Line chart of B/E ratio vs ell |
| Null Test χ² Card | χ²/dof and p-value |
| Tomo Correlation Heatmap | 5×5 correlation matrix as heatmap |

**API Endpoint:** `GET /api/kids-bmode`

**DoD:**
- [ ] All 8 ell-bins × 5 tomo bins rendered
- [ ] BB values near zero visually distinct from EE values
- [ ] Heatmap colors: blue (negative corr) → white (zero) → red (positive)
- [ ] p-value displayed with interpretation text

---

### Page 6: Data Provenance & Audit
**Route:** `/audit`

**Purpose:** Full transparency on every dataset used, its source, SHA-256 hash, and what it constrains.

**Components:**

| Component | Description |
|-----------|-------------|
| Data Cartography Table | All 9 datasets with source URL, format, hash, and observables |
| Audit Log | Timestamped record of data downloads and integrity checks |
| Warning Flags | Highlight any dataset whose provenance is unclear |

**DoD:**
- [ ] Each dataset row shows: Name, Source URL, Format, Hash, Last Verified date
- [ ] SHA-256 hashes match the audit certificates
- [ ] Warning flag shown for Euclid Q1 S8 (provenance clarification needed)

---

## 4. Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | Vite + React 18 | Fast HMR, modern JS |
| Charts | Plotly.js | Publication-quality interactive plots with log-log support |
| Styling | Vanilla CSS with CSS custom properties | Design system control |
| Backend | Python FastAPI | Async, fast, auto-OpenAPI docs |
| Compute | NumPy + SciPy | Existing codebase compatibility |
| Hosting | Cloud Run (backend) + Cloud Storage (frontend static) | Serverless, auto-scaling |
| CI/CD | Cloud Build → Cloud Run | Automated deployment |
| Auth | None (public read-only dashboard) | Transparency for peer review |

---

## 5. GCP Deployment Specification

### 5.1 Backend (Cloud Run)

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/k3t2-dashboard-api', './backend']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/k3t2-dashboard-api']
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'k3t2-dashboard-api'
      - '--image=gcr.io/$PROJECT_ID/k3t2-dashboard-api'
      - '--region=us-central1'
      - '--platform=managed'
      - '--memory=1Gi'
      - '--cpu=1'
      - '--allow-unauthenticated'
```

### 5.2 Frontend (Cloud Storage + CDN)

```bash
# Deploy frontend static build to GCS
npm run build
gsutil -m rsync -r dist/ gs://k3t2-dashboard-static/
```

### 5.3 Estimated Cost

| Resource | Monthly Cost |
|----------|-------------|
| Cloud Run (backend, low traffic) | ~$5–15 |
| Cloud Storage (static frontend) | ~$0.50 |
| Cloud Storage (data lake, existing) | Already budgeted |
| Cloud CDN (optional) | ~$1–5 |
| **Total** | **~$7–21/month** |

---

## 6. Directory Structure

```
dashboard/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt          # fastapi, uvicorn, numpy, scipy, astropy
│   ├── main.py                   # FastAPI app entry
│   ├── routers/
│   │   ├── bao.py                # /api/bao-chi2
│   │   ├── gw_spectrum.py        # /api/gw-spectrum
│   │   ├── s8_tension.py         # /api/s8-tension
│   │   ├── kids_bmode.py         # /api/kids-bmode
│   │   ├── fisher.py             # /api/fisher-hessian
│   │   └── cartography.py        # /api/data-cartography
│   └── core/
│       ├── cosmology.py          # Friedmann solver, distance calculator
│       ├── data_loader.py        # Load DESI, KiDS, etc. from GCS or local
│       └── config.py             # MAP_COSMOLOGY constants
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── pages/
│   │   │   ├── MissionControl.jsx
│   │   │   ├── BAOLadder.jsx
│   │   │   ├── GWSpectrum.jsx
│   │   │   ├── S8Tension.jsx
│   │   │   ├── BMode.jsx
│   │   │   └── Audit.jsx
│   │   ├── components/
│   │   │   ├── ParameterSlider.jsx
│   │   │   ├── Chi2Readout.jsx
│   │   │   ├── ModelToggle.jsx
│   │   │   ├── WhiskerPlot.jsx
│   │   │   └── Heatmap.jsx
│   │   └── styles/
│   │       └── index.css
│   └── public/
│       └── favicon.svg
├── cloudbuild.yaml
└── README.md
```

---

## 7. Implementation Order for Low-Tier Models

### Sprint 1: Backend API (Estimated: 2–3 hours)
1. Create `backend/core/cosmology.py` — the Friedmann E(z) solver and distance calculator. **Test:** Unit test that DM/rs at z=0.51 for ΛCDM gives ~13.6.
2. Create `backend/core/data_loader.py` — load DESI, KiDS, S8 data from local files. **Test:** Assert shapes are correct.
3. Create `backend/routers/bao.py` — the `/api/bao-chi2` endpoint. **Test:** `curl localhost:8000/api/bao-chi2?Omega_m=0.3&H0=67.4&w0=-1.0` returns valid JSON with χ² > 0.
4. Create remaining routers (`gw_spectrum.py`, `s8_tension.py`, `kids_bmode.py`).
5. Create `backend/main.py` with CORS middleware.
6. **Test:** `uvicorn main:app --reload` starts without errors. All endpoints return valid JSON.

### Sprint 2: Frontend Shell (Estimated: 2–3 hours)
1. `npx -y create-vite@latest ./ --template react` in `dashboard/frontend/`.
2. Install Plotly: `npm install plotly.js-dist-min react-plotly.js react-router-dom`.
3. Create `App.jsx` with React Router and 6 routes.
4. Create `MissionControl.jsx` with static cards.
5. **Test:** `npm run dev` shows the home page with navigation.

### Sprint 3: Interactive Pages (Estimated: 3–4 hours)
1. `BAOLadder.jsx` — sliders + Plotly chart + real-time API calls.
2. `GWSpectrum.jsx` — log-log Plotly chart with toggles.
3. `S8Tension.jsx` — whisker plot + Gaussian overlay.
4. `BMode.jsx` — bar charts + heatmap.
5. `Audit.jsx` — static data table.
6. **Test:** Each page fetches from the backend and renders data.

### Sprint 4: Deploy (Estimated: 1 hour)
1. Write Dockerfile for backend.
2. Write `cloudbuild.yaml`.
3. `gcloud builds submit`.
4. Test deployed URL.

---

## 8. Global DoD for Full Dashboard

- [ ] All 6 pages load without console errors
- [ ] All API endpoints return valid JSON within 500ms
- [ ] BAO page sliders update the plot within 200ms
- [ ] GW spectrum renders correctly on log-log axes
- [ ] S8 whisker plot displays all 4+ surveys
- [ ] B-mode heatmap renders 5×5 matrix
- [ ] Audit page lists all 9 datasets with hashes
- [ ] Mobile responsive (tested at 375px width)
- [ ] Deployed on Cloud Run with public URL
- [ ] README.md in `dashboard/` explains how to run locally

---

## 9. Design Aesthetics Requirements

- **Dark theme** with deep navy background (`#0a0e27`) and subtle star-field CSS animation
- **Accent color palette:** Cyan (`#00d4ff`) for K3×T², Gold (`#ffd700`) for ΛCDM, Coral (`#ff6b6b`) for data points
- **Typography:** Inter (Google Fonts) for UI, JetBrains Mono for numerical readouts
- **Cards:** Glassmorphism effect with `backdrop-filter: blur(10px)` and subtle border glow
- **Charts:** Dark background Plotly theme with grid lines at 20% opacity
- **Transitions:** 300ms ease-out on all interactive elements
- **Status badges:** Pulsing glow animation for live data
