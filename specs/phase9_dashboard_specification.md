# 📊 Phase 9-3: K3×T² Validation Dashboard — GCP Web Application Specification

> **Version**: 1.0.0  
> **Date**: 2026-07-31  
> **Audience**: Web developers, physicists, mathematicians  
> **Model Tier**: Gemini 3.6 Flash (High) / Gemini 3.1 Pro  
> **Deployment Target**: Google Cloud Platform (Cloud Run or App Engine)

---

## 1. Purpose

Build a **live, interactive web dashboard** that:
- Displays the current state of all 7 experimental validation workstreams
- Visualizes real Euclid Q1, DESI, NANOGrav, and KiDS-1000 data from the GCP Data Lake
- Shows the Lean 4 formal proof status with live compilation output
- Provides publication-quality interactive plots for physicists
- Enables mathematicians to inspect the Hodge diamond, moduli space, and FIM eigenvalues

---

## 2. Architecture

```
┌─────────────────────────────────────┐
│        Cloud Run (Frontend)         │
│  Next.js 14 / React + D3.js + KaTeX│
│  Port 8080, served via Cloud Run    │
└──────────┬──────────────────────────┘
           │ REST API calls
┌──────────▼──────────────────────────┐
│      Cloud Run (Backend API)        │
│  Python FastAPI + astropy + numpy   │
│  Reads from GCS bucket via gcsfs    │
└──────────┬──────────────────────────┘
           │ gcsfs / gcloud
┌──────────▼──────────────────────────┐
│     GCS Data Lake                   │
│  gs://socrateai-datalake-.../       │
│  (euclid_q1, desi_dr1, nanograv,   │
│   mcmc_posteriors, audit, etc.)     │
└─────────────────────────────────────┘
```

---

## 3. Dashboard Pages & Components

### Page 1: Mission Control (`/`)

**Purpose**: High-level status of all workstreams and key metrics at a glance.

| Component | Type | Data Source | Description |
|-----------|------|-------------|-------------|
| Workstream Status Board | Card grid (7 cards) | `outputs/wsN/` status files | Each card shows: WS name, status (⏳/✅/❌), last run timestamp, key metric |
| Key Metrics Banner | KPI strip | Computed | $S_8$ tension (σ), $\chi^2_{\text{DESI}}$, Bayes factor, Lean proof count |
| Data Lake Health | Status indicators | GCS API | Online/offline status for each data lake prefix |
| Audit Certificate | Expandable card | `gs://.../audit/euclid_q1_data_audit_certificate.md` | Shows SHA-256 hashes and verification status |

**DoD**:
- [ ] Page renders at `/` with all 7 workstream cards
- [ ] Cards reflect actual file existence in `outputs/wsN/`
- [ ] KPI strip shows 4 numeric values
- [ ] Mobile-responsive layout (Tailwind CSS grid)

**Test**:
```bash
curl http://localhost:8080/ | grep "Workstream 1"
# Expected: 200 OK with HTML containing workstream cards
```

---

### Page 2: Observational Data Explorer (`/data`)

**Purpose**: Interactive visualization of all real observational datasets.

| Panel | Visualization | Data Source | Interactivity |
|-------|---------------|-------------|---------------|
| A: Euclid Q1 Sky Map | RA/Dec scatter plot | `euclid_q1/tile_*/EUC_MER_FINAL-CAT_*.fits` | Hover to see object ID, flux, photo-z |
| B: DESI BAO Distance Ladder | $D_M/r_d$ and $D_H/r_d$ vs redshift | `stream3_desi_dr1/desi_2024_gaussian_bao_*_mean.txt` | Toggle SDSS DR12/DR16 overlays |
| C: NANOGrav Free Spectrum | $\log_{10}A$ vs frequency (14 bins) | `nanograv_15yr/15yr_emp_distr.json` | Overlay K3×T² prediction with $\gamma$ slider |
| D: KiDS-1000 Band Powers | $C_\ell^{EE}$ vs $\ell$ | `stream3_euclid_q2/kids1000_bandpowers_EE.npy` | Overlay K3×T² prediction at variable $S_8$ |

**DoD**:
- [ ] All 4 panels render with real data (not mock)
- [ ] D3.js or Plotly.js used for interactive plots
- [ ] KaTeX renders all mathematical labels ($S_8$, $C_\ell$, etc.)
- [ ] Panel C has a working $\gamma$ slider that updates the model curve in real-time

**Test**:
```bash
# API endpoint returns real data
curl http://localhost:8080/api/euclid_q1/sky_coords | python -c "import json,sys; d=json.load(sys.stdin); assert len(d['ra']) > 80000"
```

---

### Page 3: Moduli Space & Hodge Diamond (`/math`)

**Purpose**: Interactive mathematical visualization for algebraic geometers.

| Panel | Visualization | Description |
|-------|---------------|-------------|
| A: Hodge Diamond | Diamond-shaped grid | Shows $h^{p,q}$ values for Cooper $s_{10}$ with Picard number highlighted |
| B: Moduli Space Trajectory | 3D scatter (Plotly) | 300-generation evolutionary trajectory through $(\tau, cs_1, cs_2)$ space |
| C: Fisher Information Ellipsoids | 2D contour plot | 5D FIM eigenvalue decomposition projected onto principal axes |
| D: Lean 4 Proof Status | Code block + status | Live display of `GeneratedK3.lean` with syntax highlighting; theorem status table |

**DoD**:
- [ ] Hodge Diamond renders correctly with $h^{1,1} = 20$, $h^{2,0} = h^{0,2} = 1$
- [ ] 3D trajectory uses real checkpoint data from GCS
- [ ] Lean 4 code displayed with proper syntax highlighting (Prism.js or similar)
- [ ] Theorem status table: for each theorem, show ✅ proven / ⚠️ sorry / ❌ missing

**Test**:
```bash
curl http://localhost:8080/api/lean_status | python -c "import json,sys; d=json.load(sys.stdin); assert d['total_theorems'] >= 0"
```

---

### Page 4: $S_8$ Tension Resolution Dashboard (`/s8`)

**Purpose**: Single-page deep dive into the $S_8$ weak lensing tension.

| Panel | Visualization | Description |
|-------|---------------|-------------|
| A: Multi-Survey $S_8$ Comparison | Horizontal whisker plot | KiDS-1000, DES-Y3, Planck 2018, Euclid Q1, K3×T² prediction — all with error bars |
| B: $\chi^2(S_8)$ Profile | Line plot | From WS1 output: $\chi^2$ as function of $S_8$ with minimum marked |
| C: Posterior Overlay | Filled curves | Gaussian posteriors for each survey overlaid, K3×T² prediction as vertical line |
| D: Tension Matrix | Heatmap | Pairwise tension in $\sigma$ between all surveys |

**DoD**:
- [ ] Panel A shows ≥ 4 surveys with correct central values and error bars
- [ ] Panel D is a symmetric heatmap with color scale
- [ ] All values match the audit certificate and published literature
- [ ] KaTeX labels render correctly

**Test**:
```bash
# Verify S8 values are correct
curl http://localhost:8080/api/s8_surveys | python -c "
import json,sys; d=json.load(sys.stdin)
assert abs(d['euclid_q1']['mean'] - 0.828) < 0.001
assert abs(d['k3t2']['mean'] - 0.830) < 0.001
"
```

---

### Page 5: Gravitational Wave Predictions (`/gw`)

**Purpose**: Interactive exploration of the K3×T² GW signature.

| Panel | Visualization | Description |
|-------|---------------|-------------|
| A: Characteristic Strain Spectrum | Log-log plot | $h_c(f)$ for K3×T² Oligon vs SMBHB, with SKA/LISA sensitivity curves |
| B: 24.18 nHz Resonance Zoom | Zoomed log-log plot | Focus on the Compton resonance bin with NANOGrav data overlay |
| C: Hexadecapole Map | Mollweide projection | Simulated $C_\ell$ sky map at $\ell = 4$ showing Oligon web pattern |
| D: Model Parameters | Editable form | Sliders for $\gamma$, bump amplitude, bump width — live update of Panel A |

**DoD**:
- [ ] Panel A shows 3 curves (Oligon, SMBHB, sensitivity)
- [ ] Panel D sliders update Panel A in real-time
- [ ] Panel C renders a Mollweide projection with HEALPix-like grid

---

## 4. Backend API Specification

| Endpoint | Method | Returns | Data Source |
|----------|--------|---------|-------------|
| `/api/health` | GET | `{"status": "ok", "data_lake": true}` | GCS bucket check |
| `/api/euclid_q1/sky_coords` | GET | `{"ra": [...], "dec": [...], "n": 80376}` | FITS catalogs |
| `/api/euclid_q1/morphology` | GET | `{"asymmetry_mean": 0.7663, ...}` | FITS MORPH catalogs |
| `/api/desi/bao_distances` | GET | `{"z": [...], "DM_over_rs": [...], ...}` | BAO mean files |
| `/api/nanograv/free_spectrum` | GET | `{"freq_hz": [...], "log10A": [...]}` | NANOGrav JSON |
| `/api/kids1000/band_powers` | GET | `{"ell": [...], "cl_ee": [...]}` | KiDS NPY files |
| `/api/mcmc/posterior` | GET | `{"tau": {...}, "cs1": {...}, ...}` | Posterior JSONs |
| `/api/lean_status` | GET | `{"total_theorems": N, "sorry_count": M, ...}` | Parse Lean file |
| `/api/s8_surveys` | GET | Multi-survey $S_8$ values | Hardcoded + computed |
| `/api/workstream_status` | GET | `[{"id": 1, "status": "complete", ...}, ...]` | Scan outputs/ |

---

## 5. Deployment Plan (GCP Cloud Run)

### Step 1: Containerize
```dockerfile
FROM python:3.12-slim
RUN pip install fastapi uvicorn astropy numpy scipy gcsfs
COPY backend/ /app/
WORKDIR /app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Step 2: Build & Deploy
```bash
gcloud builds submit --tag gcr.io/gen-lang-client-0625573011/k3t2-dashboard:latest
gcloud run deploy k3t2-dashboard \
  --image gcr.io/gen-lang-client-0625573011/k3t2-dashboard:latest \
  --region us-east4 \
  --allow-unauthenticated \
  --set-env-vars GCS_BUCKET=socrateai-datalake-gen-lang-client-0625573011
```

### Step 3: Custom Domain (Optional)
```bash
gcloud run domain-mappings create --service k3t2-dashboard --domain dashboard.socrateai.org
```

---

## 6. Definition of Done — Full Dashboard

- [ ] All 5 pages render without errors
- [ ] All API endpoints return real data (not mock)
- [ ] All plots use D3.js or Plotly.js (no matplotlib PNGs)
- [ ] KaTeX renders all mathematical notation correctly
- [ ] Dashboard is accessible at a public Cloud Run URL
- [ ] Load time < 3 seconds for each page
- [ ] Mobile-responsive (tested at 375px width)
- [ ] Lighthouse accessibility score ≥ 90

---

## 7. Test Plan for Agents

### Smoke Test (5 minutes)
```bash
# Start dev server
cd dashboard && npm run dev &
sleep 5

# Test all pages
for page in "/" "/data" "/math" "/s8" "/gw"; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000${page})
  echo "Page ${page}: HTTP ${STATUS}"
  [ "${STATUS}" -eq 200 ] || echo "FAIL: ${page}"
done

# Test all API endpoints
for endpoint in health euclid_q1/sky_coords desi/bao_distances nanograv/free_spectrum s8_surveys lean_status workstream_status; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/api/${endpoint})
  echo "API /api/${endpoint}: HTTP ${STATUS}"
done
```

### Data Integrity Test (2 minutes)
```bash
# Verify real data is served, not stubs
python -c "
import requests, json
r = requests.get('http://localhost:8080/api/euclid_q1/sky_coords')
d = r.json()
assert d['n'] == 80376, f'Expected 80376 galaxies, got {d[\"n\"]}'
assert abs(d['ra'][0]) > 0, 'RA values should be non-zero'
print('Data integrity: PASS')
"
```
