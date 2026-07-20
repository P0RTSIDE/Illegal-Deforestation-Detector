# Web dashboard (Vercel)

Next.js portfolio site with an interactive Leaflet map. Displays flagged clearing polygons color-coded by permit status.

**Important:** Vercel hosts the *visualization only*. The Python ML pipeline (Earth Engine, PyTorch, geopandas) runs locally or in a separate compute environment. Pre-computed GeoJSON/JSON is copied into `public/data/` before deploy.

## Local dev

```bash
cd web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Sync data from Python pipeline

After running change detection + cross-reference:

```bash
# From repo root
python scripts/export_for_web.py
```

This updates `summary.json` from `data/raw/gee_metadata.json` and replaces `flagged-sites.geojson` when live output exists.

## Deploy to Vercel

Set the project's **Root Directory** to `web` so Vercel builds this Next.js app rather than the Python code at the repo root. The framework should be detected as **Next.js**, and no Python environment variables are needed.

### Option A: Vercel dashboard (recommended)

1. Push repo to GitHub.
2. Import the repository at [vercel.com/new](https://vercel.com/new).
3. Set **Root Directory** to `web` before deploying.
4. Deploy.

### Option B: CLI

```bash
cd web
npx vercel
```

Follow prompts. Production: `vercel --prod`.

## Data files

| File | Purpose |
|------|---------|
| `public/data/summary.json` | Stats cards, study area metadata |
| `public/data/study-area.geojson` | AOI boundary (dashed blue) |
| `public/data/flagged-sites.geojson` | Detected clearings with permit status |

Demo polygons ship by default. Replace with real outputs via `export_for_web.py`.

## Map layers

- **Esri World Imagery** (default): good for before/after context
- **OpenStreetMap**: toggle in layer control
- Click polygons for site details popup
