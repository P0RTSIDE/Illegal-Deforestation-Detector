# Web dashboard

Next.js map of flagged clearings. Polygons are colored by permit status. Vercel serves this site only. Earth Engine and the Python pipeline run elsewhere and write GeoJSON into `public/data/` before deploy.

## Local

```bash
cd web
npm install
npm run dev
```

Open http://localhost:3000.

## Sync pipeline output

From the repository root, after change detection and the permit join:

```bash
python scripts/export_for_web.py
```

That refreshes `summary.json` from `data/raw/gee_metadata.json` and replaces `flagged-sites.geojson` when a live output file is present. Demo polygons ship in the repo until that file exists.

## Deploy

Set the Vercel root directory to `web` so the Next.js app builds instead of the Python project. The framework is Next.js. The site does not need Python environment variables.

```bash
cd web
npx vercel
```

Production: `npx vercel --prod`.

## Data files

| File | Purpose |
| --- | --- |
| `public/data/summary.json` | Stats cards and study-area metadata |
| `public/data/study-area.geojson` | AOI boundary |
| `public/data/flagged-sites.geojson` | Detected clearings with permit status |

## Map layers

- Esri World Imagery is the default basemap, for before and after context
- OpenStreetMap is available in the layer control
- A polygon click opens the site details
