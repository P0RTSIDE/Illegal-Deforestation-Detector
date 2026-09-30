# Clearing and Permit Map

Pairs satellite change detection with public concession records to flag land clearing that does not match an available mining or logging permit. The pilot area is the Brazilian Amazon. A second mode looks for vegetation loss inside US national park boundaries.

Live dashboard: [illegal-deforestation-detector.vercel.app](https://illegal-deforestation-detector.vercel.app/).

Flags are heuristic and depend on incomplete public records. A clearing outside a concession boundary means it is not accounted for in the registries used here. It is not a legal finding. Details are in `data/DATA_NOTES.md`.

## Study area

Southern Pará, along the Novo Progresso corridor: a pilot box of about 55 by 45 km with high DETER alert density and documented mining pressure.

| Parameter | Value |
| --- | --- |
| BBox (W, S, E, N) | -56.30, -7.90, -55.25, -7.05 |
| Before year | 2019 |
| After year | 2023 |
| Config | `src/config.py` |

US park boundaries are defined in `src/us_parks.py`. Parks are not checked against mining permits. The signal there is vegetation loss inside a protected boundary.

## Method

1. **Imagery.** Google Earth Engine builds Sentinel-2 median composites for the before and after years (`src/gee_utils.py`). When Earth Engine is unavailable, Hansen Global Forest Change tiles supply a 30 m tree-cover-loss map (`src/hansen_change.py`).
2. **Spectral change.** A pixel is flagged when it was vegetated before and then loses NDVI or NBR past a fixed threshold. Small holes are closed, patches under an area floor are dropped, and the mask is vectorized (`src/change_detection.py`). Thresholds and the hectare floor are constants in that module.
3. **Permit join.** Detected polygons are compared with ANM SIGMINE mining permits for Pará and Global Forest Watch logging concessions, plus an optional local IBAMA SINAFLOR shapefile (`src/geo_crossref.py`). Status labels distinguish no permit found, overlap with a registered permit, possible exceedance, and unclear match.
4. **Context layers.** INPE DETER and PRODES, and Hansen Global Forest Change, are the external checks described in `data/DATA_NOTES.md`.
5. **Map.** `scripts/generate_real_flags.py` writes GeoJSON under `data/processed/`. `scripts/export_for_web.py` copies that into the Next.js app in `web/`. Park runs use `scripts/generate_park_flags.py`.

The shipped detector is this spectral baseline. `src/model.py` is not used by the pipeline.

## Run the pipeline

Python 3.10 or newer, a Google Earth Engine account, and a Google Cloud project registered for Earth Engine.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r python/requirements.txt
python scripts/authenticate_gee.py
```

On Windows, activate with `.venv\Scripts\activate`.

Copy `.env.example` to `.env` and set `GEE_PROJECT_ID`.

```bash
python scripts/test_gee_pull.py
python scripts/generate_real_flags.py
python scripts/export_for_web.py
```

`test_gee_pull.py` checks that Sentinel-2 returns imagery for 2019 and 2023 and writes `data/raw/gee_metadata.json`. `--export-drive` sends full composites to Google Drive. Tasks show up at [code.earthengine.google.com/tasks](https://code.earthengine.google.com/tasks).

## Dashboard

The site in `web/` is a Next.js map (Leaflet) with permit-status coloring and site popups. Vercel hosts that visualization. The Python pipeline runs separately and feeds it precomputed GeoJSON.

```bash
cd web
npm install
npm run dev
```

Open http://localhost:3000. On Vercel, set the project root directory to `web`. See `web/README.md`.

Until `export_for_web.py` has real output, the map shows the demo polygons that ship in the repo.

## Repository layout

```
src/           config, Earth Engine helpers, NDVI/NBR change, Hansen tiles, permit join, US parks
scripts/       auth, GEE smoke test, flag generation, export into web/public/data
web/           Next.js dashboard
data/          raw exports, processed GeoJSON, DATA_NOTES.md
python/        requirements.txt
```

## Data sources

| Data | Source | Notes |
| --- | --- | --- |
| Sentinel-2 L2A | GEE `COPERNICUS/S2_SR_HARMONIZED` | 10 m, free |
| Cloud mask | GEE `COPERNICUS/S2_CLOUD_PROBABILITY` | s2cloudless |
| Mining permits | [ANM SIGMINE](https://app.anm.gov.br/dadosabertos/SIGMINE/) | Daily updates, authoritative for Brazil |
| Logging permits | GFW managed forests, optional IBAMA SINAFLOR | See DATA_NOTES |
| Validation context | INPE DETER/PRODES, Hansen GFC | Alert, annual, and 30 m products |
| US parks | National Park Service boundaries via `src/us_parks.py` | Protected-area mode |

Download steps and licensing: `data/DATA_NOTES.md`.

## Limitations

- 10 m Sentinel-2 misses clearings smaller than about half a hectare. The vector step also drops patches under its hectare floor.
- Cloud cover in the Amazon leaves gaps in the composite years.
- Concession registries are incomplete. Informal mining is often unregistered, so "no permit found" is not proof of illegality.
- Hansen labels are 30 m and are a different product from the 10 m Sentinel-2 mask.
- There is no field check in this version.

## License

No license file is included with this repository. Each data source keeps its own terms. See `data/DATA_NOTES.md`.
