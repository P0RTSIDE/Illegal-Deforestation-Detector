"""
Spatial join of detected change polygons against mining and logging permits.

Mining: ANM SIGMINE (Pará)
Logging: GFW managed forest concessions (bbox clip) + optional local SINAFLOR shapefile
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Literal

import pandas as pd
import geopandas as gpd
import requests
from shapely.geometry import Point, box

PermitStatus = Literal[
    "likely_unpermitted",
    "likely_permitted",
    "likely_exceeding_permit",
    "unknown",
]

ANM_PA_URL = "https://dadosabertos.anm.gov.br/SIGMINE/PROCESSOS_MINERARIOS/PA.zip"
ANM_PA_URL_FALLBACK = (
    "https://dadosabertos.anm.gov.br/SIGMINE/PROCESSOS_MINERARIOS/BRASIL.zip"
)

GFW_LOGGING_QUERY_URL = (
    "https://gis-gfw.wri.org/arcgis/rest/services/land_use/MapServer/3/query"
)

ACTIVE_MINING_PHASE_SUBSTRINGS = (
    "LAVRA",
    "CONCESSAO DE LAVRA",
    "REQUERIMENTO DE LAVRA",
    "LICENCIAMENTO",
)

# GFW status values treated as active logging permits
ACTIVE_LOGGING_STATUS = {
    "ACTIVE",
    "IN EFFECT",
    "CURRENT",
    "VALID",
    "OPERATING",
}


def _normalize_text(value: object) -> str:
    import unicodedata

    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode(
        "ascii"
    )
    return text.strip().upper()


def download_sigmine_para(
    dest_dir: Path,
    url: str = ANM_PA_URL,
    force: bool = False,
) -> Path:
    """Download and extract ANM SIGMINE Pará shapefile."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / "PA.zip"

    shp_files = list(dest_dir.glob("**/*.shp"))
    if shp_files and not force:
        return shp_files[0]

    urls = [url]
    if url != ANM_PA_URL_FALLBACK:
        urls.append(ANM_PA_URL_FALLBACK)

    last_error: Exception | None = None
    for try_url in urls:
        try:
            print(f"Downloading SIGMINE from {try_url} ...")
            response = requests.get(try_url, timeout=180)
            response.raise_for_status()
            zip_path.write_bytes(response.content)
            extract_dir = dest_dir / ("brasil" if "BRASIL" in try_url else "pa")
            extract_dir.mkdir(exist_ok=True)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)
            shp_files = list(extract_dir.glob("**/*.shp"))
            if shp_files:
                return shp_files[0]
        except Exception as exc:
            last_error = exc
            continue

    raise RuntimeError(f"Failed to download SIGMINE shapefile: {last_error}")


def _load_vector_file(path: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4674")
    gdf = gdf.to_crs("EPSG:4326")
    gdf["geometry"] = gdf.geometry.make_valid()
    return gdf


def load_mining_concessions(shp_path: Path) -> gpd.GeoDataFrame:
    return _load_vector_file(shp_path)


def _find_local_logging_files(logging_dir: Path) -> list[Path]:
    patterns = ["**/*.shp", "**/*.geojson", "**/*.gpkg"]
    files: list[Path] = []
    for pattern in patterns:
        files.extend(logging_dir.glob(pattern))
    return sorted(set(files))


def fetch_gfw_logging_by_bbox(
    bbox: tuple[float, float, float, float],
    dest_path: Path,
    force: bool = False,
    page_size: int = 1000,
) -> Path:
    """
    Download GFW managed forest (logging) concessions intersecting the study bbox.
    Saves GeoJSON to dest_path.
    """
    if dest_path.exists() and not force:
        print(f"Using cached logging concessions: {dest_path}")
        return dest_path

    west, south, east, north = bbox
    geometry = json.dumps(
        {
            "xmin": west,
            "ymin": south,
            "xmax": east,
            "ymax": north,
            "spatialReference": {"wkid": 4326},
        }
    )

    features: list[dict] = []
    offset = 0

    while True:
        params = {
            "where": "1=1",
            "geometry": geometry,
            "geometryType": "esriGeometryEnvelope",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": page_size,
            "outSR": 4326,
        }
        print(f"Fetching GFW logging concessions (offset {offset}) ...")
        response = requests.get(GFW_LOGGING_QUERY_URL, params=params, timeout=180)
        response.raise_for_status()
        try:
            payload = response.json()
        except requests.exceptions.JSONDecodeError as exc:
            snippet = response.text[:200].replace("\n", " ")
            raise RuntimeError(
                f"GFW logging API returned non-JSON response ({response.status_code}): {snippet}"
            ) from exc
        batch = payload.get("features", [])
        if not batch:
            break
        features.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with dest_path.open("w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)

    print(f"Saved {len(features)} logging concession polygons to {dest_path}")
    return dest_path


def load_logging_concessions(
    logging_dir: Path,
    bbox: tuple[float, float, float, float],
    force_download: bool = False,
) -> gpd.GeoDataFrame:
    """
    Load logging permits from cached GFW GeoJSON and/or local SINAFLOR files.
    """
    frames: list[gpd.GeoDataFrame] = []
    gfw_path = logging_dir / "gfw_logging_aoi.geojson"

    try:
        fetch_gfw_logging_by_bbox(bbox, gfw_path, force=force_download)
        gfw_gdf = gpd.read_file(gfw_path)
        if not gfw_gdf.empty:
            gfw_gdf["permit_source"] = "gfw_logging"
            frames.append(gfw_gdf)
    except Exception as exc:
        print(f"Warning: GFW logging download failed: {exc}")

    for path in _find_local_logging_files(logging_dir):
        if path == gfw_path:
            continue
        try:
            local_gdf = _load_vector_file(path)
            local_gdf["permit_source"] = f"local:{path.stem}"
            frames.append(local_gdf)
            print(f"Loaded local logging layer: {path}")
        except Exception as exc:
            print(f"Warning: could not read {path}: {exc}")

    if not frames:
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    merged = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs="EPSG:4326")
    merged["geometry"] = merged.geometry.make_valid()
    study_box = box(*bbox)
    merged = merged[merged.intersects(study_box)].copy()
    return merged

def _matches_at_point(
    centroid: Point,
    concessions: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    if concessions.empty:
        return concessions

    matches = concessions[concessions.contains(centroid)]
    if matches.empty:
        buffer_gdf = gpd.GeoDataFrame(geometry=[centroid.buffer(0.001)], crs="EPSG:4326")
        matches = gpd.sjoin(concessions, buffer_gdf, predicate="intersects")
        if not matches.empty:
            matches = matches.drop(
                columns=[c for c in matches.columns if c.startswith("index_")],
                errors="ignore",
            )
    return matches


def _phase_column(gdf: gpd.GeoDataFrame) -> str | None:
    for col in ("FASE", "fase", "DSProcesso", "PROCESSO"):
        if col in gdf.columns:
            return col
    return None


def _parse_area_ha(matches: gpd.GeoDataFrame) -> float | None:
    for col in ("AREA_HA", "AREA_HECTARES", "QT_AREA_HA", "area_ha"):
        if col in matches.columns:
            try:
                return float(matches[col].astype(float).max())
            except (TypeError, ValueError):
                continue
    return None


def classify_mining_site(
    centroid: Point,
    mining: gpd.GeoDataFrame,
    area_ha: float,
) -> tuple[PermitStatus, str] | None:
    """Return classification if mining layer matches, else None."""
    matches = _matches_at_point(centroid, mining)
    if matches.empty:
        return None

    phase_col = _phase_column(matches)
    if phase_col:
        phases = {_normalize_text(v) for v in matches[phase_col].dropna().unique()}
        if any(any(sub in phase for sub in ACTIVE_MINING_PHASE_SUBSTRINGS) for phase in phases):
            permit_area = _parse_area_ha(matches)
            if permit_area is not None and area_ha > permit_area * 1.5:
                return (
                    "likely_exceeding_permit",
                    f"Inside SIGMINE mining permit but clearing ({area_ha:.1f} ha) "
                    f"exceeds registered area ({permit_area:.1f} ha).",
                )
            return (
                "likely_permitted",
                f"Inside active SIGMINE mining permit (phase: {', '.join(sorted(phases))}).",
            )
        return (
            "unknown",
            f"Inside SIGMINE polygon but phase not clearly active: {', '.join(sorted(phases))}.",
        )

    return (
        "unknown",
        f"Inside SIGMINE mining polygon ({len(matches)} overlap); phase field not found.",
    )


def classify_logging_site(
    centroid: Point,
    logging: gpd.GeoDataFrame,
    area_ha: float,
) -> tuple[PermitStatus, str] | None:
    """Return classification if logging layer matches, else None."""
    matches = _matches_at_point(centroid, logging)
    if matches.empty:
        return None

    status_col = "status" if "status" in matches.columns else None
    if status_col:
        statuses = {_normalize_text(v) for v in matches[status_col].dropna().unique()}
        inactive_markers = {"INACTIVE", "EXPIRED", "CANCELLED", "SUSPENDED"}
        if statuses and statuses.isdisjoint(ACTIVE_LOGGING_STATUS) and statuses & inactive_markers:
            return (
                "unknown",
                f"Inside logging concession with inactive status: {', '.join(sorted(statuses))}.",
            )

    permit_area = _parse_area_ha(matches)
    if permit_area is not None and area_ha > permit_area * 1.5:
        name = matches["name"].iloc[0] if "name" in matches.columns else "logging concession"
        return (
            "likely_exceeding_permit",
            f"Inside logging permit '{name}' but clearing ({area_ha:.1f} ha) "
            f"exceeds registered area ({permit_area:.1f} ha).",
        )

    name = matches["name"].iloc[0] if "name" in matches.columns else "logging concession"
    source = matches["permit_source"].iloc[0] if "permit_source" in matches.columns else "logging layer"
    auth_type = matches["type"].iloc[0] if "type" in matches.columns else "managed forest"
    return (
        "likely_permitted",
        f"Inside logging permit '{name}' ({auth_type}) from {source}.",
    )


def classify_site(
    centroid: Point,
    mining: gpd.GeoDataFrame,
    logging: gpd.GeoDataFrame,
    area_ha: float,
) -> tuple[PermitStatus, str, str]:
    """
    Classify against mining then logging permits.
    Returns (status, notes, matched_permit_type).
    """
    mining_result = classify_mining_site(centroid, mining, area_ha)
    if mining_result and mining_result[0] in ("likely_permitted", "likely_exceeding_permit"):
        return mining_result[0], mining_result[1], "mining"

    logging_result = classify_logging_site(centroid, logging, area_ha)
    if logging_result and logging_result[0] in ("likely_permitted", "likely_exceeding_permit"):
        return logging_result[0], logging_result[1], "logging"

    if mining_result and mining_result[0] == "unknown":
        if logging_result:
            return (
                "unknown",
                f"{mining_result[1]} Also: {logging_result[1]}",
                "mining+logging",
            )
        return mining_result[0], mining_result[1], "mining"

    if logging_result and logging_result[0] == "unknown":
        return logging_result[0], logging_result[1], "logging"

    if mining_result or logging_result:
        return (
            "unknown",
            "Partial overlap with permit records; could not confirm active authorization.",
            "mining+logging",
        )

    return (
        "likely_unpermitted",
        "Outside ANM SIGMINE mining permits and GFW logging concessions in this study area.",
        "none",
    )


def cross_reference_geojson(
    geojson: dict,
    mining: gpd.GeoDataFrame,
    logging: gpd.GeoDataFrame,
) -> dict:
    """Add permit_status, notes, and matched_permit_type to each feature."""
    gdf = gpd.GeoDataFrame.from_features(geojson["features"], crs="EPSG:4326")

    statuses: list[str] = []
    notes: list[str] = []
    names: list[str] = []
    permit_types: list[str] = []

    for idx, row in gdf.iterrows():
        centroid = row.geometry.centroid
        area_ha = float(row.get("area_ha", row.geometry.area * 111000 * 111000 / 10000))
        status, note, permit_type = classify_site(centroid, mining, logging, area_ha)
        statuses.append(status)
        notes.append(note)
        permit_types.append(permit_type)
        names.append(f"Clearing patch {idx + 1}")

    gdf["permit_status"] = statuses
    gdf["notes"] = notes
    gdf["matched_permit_type"] = permit_types
    gdf["name"] = names
    gdf["id"] = [f"live-{i + 1:04d}" for i in range(len(gdf))]

    return gdf.__geo_interface__


# Backward-compatible alias
load_concessions = load_mining_concessions
