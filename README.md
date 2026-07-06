# Satellite-Based Illegal Deforestation / Mining Detector

Portfolio project combining **Sentinel-2 change detection** with **public concession/permit cross-referencing** to flag likely unpermitted land clearing in the Brazilian Amazon.

> **Important:** This system produces *heuristic flags* based on incomplete public records. "Outside a concession boundary" means "not accounted for in available registries" — not proven illegality. See limitations in `reports/writeup.md` (coming) and `data/DATA_NOTES.md`.

## Study area

**Southern Pará (Novo Progresso corridor)** — a ~55 × 45 km pilot AOI with high DETER alert density and documented illegal mining pressure.

| Parameter | Value |
|-----------|-------|
| BBox (W,S,E,N) | -56.30, -7.90, -55.25, -7.05 |
| Before year | 2019 |
| After year | 2023 |
| Config | `src/config.py` |

## Quick start

### 1. Prerequisites

- Python 3.10+
- [Google Earth Engine account](https://signup.earthengine.google.com/) (free non-commercial)
- A Google Cloud project registered for Earth Engine: [register here](https://code.earthengine.google.com/register)

### 2. Install

```bash
cd deforestation-detector
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 3. Authenticate Earth Engine

```bash
python scripts/authenticate_gee.py
# Or: earthengine authenticate
```

### 4. Configure project ID

```bash
copy .env.example .env
# Edit .env → GEE_PROJECT_ID=your-gcp-project-id
```

### 5. Test the data pipeline (no model code yet)

```bash
python scripts/test_gee_pull.py
```

This verifies Sentinel-2 collections return images for 2019 and 2023 and writes `data/raw/gee_metadata.json`.

To export full composites to Google Drive:

```bash
python scripts/test_gee_pull.py --export-drive
```

Monitor tasks at [code.earthengine.google.com/tasks](https://code.earthengine.google.com/tasks).

## Repo structure

```
deforestation-detector/
  data/
    raw/                  # GEE exports, concession shapefiles
    processed/            # aligned image pairs, tiled patches
    DATA_NOTES.md         # data sources, licensing, caveats
  notebooks/
    01_gee_data_pull.ipynb
    02_preprocessing_and_tiling.ipynb      (planned)
    03_change_detection_model.ipynb        (planned)
    04_concession_crossref.ipynb           (planned)
    05_validation_against_hansen.ipynb     (planned)
  src/
    config.py             # study area, bands, GEE collection IDs
    gee_utils.py            # Earth Engine auth, composites, export
    preprocessing.py        (planned)
    dataset.py              (planned)
    model.py                (planned)
    train.py                (planned)
    inference.py            (planned)
    geo_crossref.py         (planned)
  scripts/
    authenticate_gee.py
    test_gee_pull.py
    export_for_web.py       # copy pipeline outputs → web/public/data/
  web/                      # Next.js dashboard (deploy to Vercel)
    app/
    components/
    public/data/            # GeoJSON + summary JSON for the map
  reports/
    figures/
  requirements.txt
  README.md
```

## Web dashboard (Vercel)

The portfolio site lives in **`web/`** — a Next.js app with an interactive satellite map and flagged-site popups. Vercel hosts the visualization; the Python pipeline runs locally and feeds it pre-computed GeoJSON.

```bash
# Preview locally
cd web
npm install
npm run dev
```

```bash
# Sync GEE metadata (and live outputs when ready)
python scripts/export_for_web.py
```

**Deploy:** Push to GitHub → [vercel.com/new](https://vercel.com/new) → set **Root Directory** to `web`. See `web/README.md`.

The map currently shows **demo polygons** until you run change detection + `export_for_web.py` with real `flagged_sites.geojson`.

## What to do next (ML pipeline)

| Step | Action | Command / file |
|------|--------|----------------|
| 1 ✅ | GEE pipeline verified | `python scripts/test_gee_pull.py` |
| 2 | Export image composites | `python scripts/test_gee_pull.py --export-drive` |
| 3 | Download ANM SIGMINE Pará | See `data/DATA_NOTES.md` → `data/raw/concessions/` |
| 4 | Preprocess + tile rasters | Notebook `02_preprocessing_and_tiling.ipynb` |
| 5 | Baseline NDVI/NBR change map | Before any CNN — interpretable baseline |
| 6 | Concession spatial join | `geo_crossref.py` / notebook 04 |
| 7 | Push results to website | `python scripts/export_for_web.py` → redeploy Vercel |

## Methodology (build order)

1. **Data acquisition** — GEE Sentinel-2 before/after median composites ✅
2. **Preprocessing** — cloud masking, tiling, normalization ← **you are here**
3. **Change detection** — spectral index baseline (NDVI/NBR diff) *then* learned Siamese/U-Net
4. **Concession cross-reference** — spatial join detected polygons vs ANM SIGMINE / GFW layers
5. **Validation** — DETER/PRODES + Hansen sanity checks
6. **Output** — sync results to web dashboard + deploy to Vercel

## Data sources (summary)

| Data | Source | Notes |
|------|--------|-------|
| Sentinel-2 L2A | GEE `COPERNICUS/S2_SR_HARMONIZED` | 10 m, free |
| Cloud mask | GEE `COPERNICUS/S2_CLOUD_PROBABILITY` | s2cloudless |
| Mining permits | [ANM SIGMINE](https://app.anm.gov.br/dadosabertos/SIGMINE/) | Daily updates, authoritative for Brazil |
| Logging permits | GFW / IBAMA SINAFLOR | Messier; see DATA_NOTES |
| Validation | INPE DETER/PRODES, Hansen GFC | Alert vs annual vs 30 m labels |

Full download steps and licensing: **`data/DATA_NOTES.md`**.

## Limitations (read before demoing)

- 10 m Sentinel-2 misses small-scale clearings (<0.5 ha)
- Cloud cover in tropical Amazon creates temporal gaps
- Concession registries are incomplete; garimpo often unregistered
- Heuristic flags ≠ legal findings; no field verification in v1
- Hansen labels (30 m) are imperfect training targets for a 10 m model

## License

Code: MIT (add `LICENSE` file before publishing).  
Data: each source has its own license — see `data/DATA_NOTES.md`.
