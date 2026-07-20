# Data sources & licensing notes

Study area: **Brazilian Amazon — Southern Pará (Novo Progresso corridor)**

This document records exact download steps, licensing, and known quality caveats.
Update it whenever you pull a new snapshot of concession or validation data.

---

## 1. Satellite imagery (Sentinel-2 L2A)

| Field | Value |
|-------|-------|
| Collection | `COPERNICUS/S2_SR_HARMONIZED` (surface reflectance, harmonized with L1C) |
| Cloud mask | `COPERNICUS/S2_CLOUD_PROBABILITY` via s2cloudless (threshold: 40%) |
| Bands | B2, B3, B4, B8 (10 m); B11, B12 (20 m, resampled on export) |
| Access | [Google Earth Engine Python API](https://developers.google.com/earth-engine/guides/python_install) |
| License | Copernicus Sentinel data — free, open ([terms](https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice)) |
| GEE terms | Non-commercial use free; [EE TOS](https://earthengine.google.com/terms/) |

### Pull strategy (this repo)

- **Before composite**: annual median of cloud-masked scenes for `before_year` (default 2019)
- **After composite**: same for `after_year` (default 2023)
- **Pilot AOI**: ~55 × 45 km bbox around Novo Progresso, Pará (`src/config.py`)

### Known limitations

- Tropical cloud cover leaves gaps even with median compositing; expect 5–15% masked pixels.
- 10 m resolution misses sub-hectare clearings and narrow mining trails.
- Annual medians blur rapid events; DETER alerts provide higher-temporal-resolution validation.

---

## 2. Mining concessions / permits (primary: ANM SIGMINE)

| Field | Value |
|-------|-------|
| Authority | Agência Nacional de Mineração (ANM) |
| Dataset | SIGMINE — active mineral processes (polygons) |
| Update frequency | **Daily** |
| CRS | SIRGAS 2000 (geographic) |
| License | [ODbL](http://www.opendefinition.org/licenses/odc-odbl) |

### Download steps

1. **State-level shapefile (recommended for pilot)** — Pará only (~10 MB):
   ```
   https://app.anm.gov.br/dadosabertos/SIGMINE/PROCESSOS_MINERARIOS/PA.zip
   ```
2. **Full Brazil** (~120 MB):
   ```
   https://app.anm.gov.br/dadosabertos/SIGMINE/PROCESSOS_MINERARIOS/BRASIL.zip
   ```
3. Unzip to `data/raw/concessions/anm_sigmine_pa/`
4. Key attribute fields (verify in shapefile): process number, phase (`FASE`), substance, holder name, area.

### REST / WMS (alternative)

- ArcGIS REST: `https://geo.anm.gov.br/arcgis/rest/services/SIGMINE/dados_anm/MapServer`
- Portal: [ANM Geoinformação Mineral](https://app.anm.gov.br/portal-da-geoinformacao-mineral/)

### Quality caveats

- Polygons represent **mineral rights applications/concessions**, not necessarily active mining.
- Includes areas "em disponibilidade" (available for bidding) — not permitted extraction.
- Garimpo (artisanal) sites may lack formal polygons entirely.
- Geometry quality varies; self-intersections and slivers are common — run `make_valid()` before joins.

---

## 3. Logging / forest management permits

### 3a. IBAMA SINAFLOR — forest management in Legal Amazon

| Field | Value |
|-------|-------|
| Authority | IBAMA (via SINAFLOR) |
| Content | Authorized forest management plans, harvesting permits |
| Access | [SINAFLOR portal](http://siscom.ibama.gov.br/) — no bulk shapefile as clean as SIGMINE |
| GFW mirror | See §4 below |

**Caveat**: Bulk geospatial export from SINAFLOR is cumbersome. For the pilot, use GFW aggregated layers or manually export a subset from [SINAFLOR Geo](http://siscom.ibama.gov.br/geoserver).

### 3b. Federal forest concessions (SFB)

| Field | Value |
|-------|-------|
| Authority | Serviço Florestal Brasileiro (SFB) |
| Content | Federal public forest concessions (limited extent in Amazon) |
| Portal | [dados.florestal.gov.br](https://dados.florestal.gov.br/) |
| Format | Mostly PDF/tabular reports; **few federal concessions exist** — small overlap with our AOI |

**Caveat**: Federal forest concessions are rare in Southern Pará. Most logging permits are state-level or illegal. Do not treat absence from SFB data as evidence of illegality.

---

## 4. Global Forest Watch aggregated layers (cross-check / gap-fill)

GFW compiles concession data from multiple government sources into consistent layers.

| Layer | GFW Open Data | ArcGIS REST |
|-------|---------------|-------------|
| Mining concessions (global) | [data.globalforestwatch.org](https://data.globalforestwatch.org/) | Search "mining concessions" |
| Logging concessions (Brazil) | Same portal | `gis-gfw.wri.org/arcgis/rest/services/commodities/MapServer` |

### Download via Open Data Portal

1. Visit [https://data.globalforestwatch.org/](https://data.globalforestwatch.org/)
2. Search "mining concessions" or "logging concessions"
3. Filter country = Brazil (or download global and clip to AOI)
4. Save to `data/raw/concessions/gfw/`

### Quality caveats

- **Often outdated** relative to ANM/IBAMA source systems (months to years lag).
- Aggregated global schema loses country-specific permit metadata (phase, dates, area limits).
- Use GFW for quick prototyping; use **ANM SIGMINE as authoritative** for mining cross-reference in Brazil.

---

## 5. Validation / ground-truth labels

### 5a. Hansen Global Forest Change (tree cover loss)

| Field | Value |
|-------|-------|
| GEE asset | `UMD/hansen/global_forest_change_2023_v1` (update version as new releases ship) |
| Band | `loss` (1 = loss detected 2000–2023), `lossyear` |
| License | CC BY 4.0 |
| Use | Imperfect training labels for supervised change model; 30 m resolution |

### 5b. INPE DETER (near-real-time alerts)

| Field | Value |
|-------|-------|
| Content | Bi-weekly deforestation/degredation alerts, Legal Amazon |
| Download | [terrabrasilis.dpi.inpe.br/downloads](https://terrabrasilis.dpi.inpe.br/downloads/) |
| WFS | `https://terrabrasilis.dpi.inpe.br/geoserver/deter-amz/wfs` |
| Layer | `deter_public` |
| Example WFS query (2019 alerts, shapefile zip) | See TerraBrasilis WFS docs |

```text
https://terrabrasilis.dpi.inpe.br/geoserver/deter-amz/wfs
  ?service=WFS&version=2.0.0&request=GetFeature
  &typeName=deter_public
  &CQL_FILTER=view_date BETWEEN '2019-01-01' AND '2019-12-31'
  &outputFormat=SHAPE-ZIP&srsName=EPSG:4674
```

**Caveat**: DETER alerts are **detection hints**, not confirmed illegal activity. Cloud gaps and minimum mapping unit (~3 ha) apply.

### 5c. INPE PRODES (annual confirmed deforestation)

| Field | Value |
|-------|-------|
| Content | Annual deforestation polygons, official Brazilian statistics |
| Download | [terrabrasilis.dpi.inpe.br/downloads](https://terrabrasilis.dpi.inpe.br/downloads/) → Amazônia Legal – PRODES |
| Use | Sanity-check total detected change area against official increments |

---

## 6. Recommended download order for pilot

1. ✅ GEE Sentinel-2 composites — `python scripts/test_gee_pull.py`
2. ANM SIGMINE Pará shapefile → `data/raw/concessions/anm_sigmine_pa/`
3. GFW mining concessions (Brazil clip) → `data/raw/concessions/gfw/` (cross-check)
4. DETER 2019–2023 alerts via WFS → `data/raw/validation/deter/`
5. Hansen tree-cover-loss via GEE export (notebook 05) → `data/raw/validation/hansen/`

---

## 7. Cross-reference logic (implemented in `src/geo_crossref.py`)

Each detected change polygon is classified heuristically against **mining** (ANM SIGMINE) and **logging** (GFW + optional SINAFLOR):

| Status | Rule |
|--------|------|
| `likely_permitted` | Centroid inside an active mining permit (SIGMINE phase match) or inside an active GFW logging concession |
| `likely_unpermitted` | Centroid outside all mining and logging permit polygons loaded for the study area |
| `likely_exceeding_permit` | Inside a permit but cleared area exceeds registered limit (when area field is present) |
| `unknown` | Partial overlap, inactive permit status, or ambiguous registry metadata |

Additional output field: `matched_permit_type` = `mining`, `logging`, `mining+logging`, or `none`.

**This is not a legal determination.** Public concession registries are incomplete and often stale. GFW logging coverage for Brazil may lag IBAMA SINAFLOR. Flagged sites mean "not accounted for in available public records," not proven illegality.

---

## 8. File inventory (fill in as you download)

| Path | Source | Date pulled | Notes |
|------|--------|-------------|-------|
| `data/raw/gee_metadata.json` | GEE API | (auto) | Collection size sanity check |
| `data/raw/concessions/anm_sigmine_pa/` | ANM | | Mining permits (Pará) |
| `data/raw/concessions/logging/gfw_logging_aoi.geojson` | GFW ArcGIS REST | | Logging concessions clipped to AOI |
| `data/raw/concessions/logging/sinaflor/` | IBAMA SINAFLOR | | Optional manual shapefile drop |
| `data/raw/validation/deter/` | INPE | | |
| `data/raw/validation/hansen/` | UMD/GFW | | |
