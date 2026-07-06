"""
Spatial join of detected change polygons against ANM SIGMINE mining concessions.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Literal
import unicodedata

import geopandas as gpd
import requests
from shapely.geometry import Point

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

# Substrings matched after ASCII-normalizing SIGMINE FASE values (handles encoding quirks)
ACTIVE_PHASE_SUBSTRINGS = (
    "LAVRA",
    "CONCESSAO DE LAVRA",
    "REQUERIMENTO DE LAVRA",
    "LICENCIAMENTO",
)


def _normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
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


def load_concessions(shp_path: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(shp_path)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4674")
    gdf = gdf.to_crs("EPSG:4326")
    gdf["geometry"] = gdf.geometry.make_valid()
    return gdf


def _phase_column(gdf: gpd.GeoDataFrame) -> str | None:
    for col in ("FASE", "fase", "DSProcesso", "PROCESSO"):
        if col in gdf.columns:
            return col
    return None


def classify_site(
    centroid: Point,
    concessions: gpd.GeoDataFrame,
    area_ha: float,
) -> tuple[PermitStatus, str]:
    """
    Classify a clearing polygon by permit status using centroid within join.
    Returns (status, notes).
    """
    if concessions.empty:
        return "unknown", "No concession layer loaded."

    matches = concessions[concessions.contains(centroid)]
    if matches.empty:
        # Small buffer for geometry edge cases (~100 m)
        buffer_gdf = gpd.GeoDataFrame(
            geometry=[centroid.buffer(0.001)],
            crs="EPSG:4326",
        )
        matches = gpd.sjoin(concessions, buffer_gdf, predicate="intersects")
        if not matches.empty:
            matches = matches.drop(columns=[c for c in matches.columns if c.startswith("index_")], errors="ignore")

    if matches.empty:
        return (
            "likely_unpermitted",
            "Centroid outside all ANM SIGMINE polygons for Pará.",
        )

    phase_col = _phase_column(matches)
    if phase_col:
        phases = {_normalize_text(v) for v in matches[phase_col].dropna().unique()}
        if any(any(sub in phase for sub in ACTIVE_PHASE_SUBSTRINGS) for phase in phases):
            # Rough area check if concession area attribute exists
            area_col = next(
                (c for c in ("AREA_HA", "AREA_HECTARES", "QT_AREA_HA") if c in matches.columns),
                None,
            )
            if area_col is not None:
                try:
                    max_permit = float(matches[area_col].max())
                    if area_ha > max_permit * 1.5:
                        return (
                            "likely_exceeding_permit",
                            f"Inside SIGMINE polygon but clearing ({area_ha:.1f} ha) "
                            f"exceeds registered concession area ({max_permit:.1f} ha).",
                        )
                except (TypeError, ValueError):
                    pass
            return (
                "likely_permitted",
                f"Centroid inside active SIGMINE process (phase: {', '.join(sorted(phases))}).",
            )
        return (
            "unknown",
            f"Inside SIGMINE polygon but phase not clearly active: {', '.join(sorted(phases))}.",
        )

    return (
        "unknown",
        f"Inside SIGMINE polygon ({len(matches)} overlap); phase field not found.",
    )


def cross_reference_geojson(
    geojson: dict,
    concessions: gpd.GeoDataFrame,
) -> dict:
    """Add permit_status and notes to each feature in a GeoJSON FeatureCollection."""
    gdf = gpd.GeoDataFrame.from_features(geojson["features"], crs="EPSG:4326")

    statuses: list[str] = []
    notes: list[str] = []
    names: list[str] = []

    for idx, row in gdf.iterrows():
        centroid = row.geometry.centroid
        area_ha = float(row.get("area_ha", row.geometry.area * 111000 * 111000 / 10000))
        status, note = classify_site(centroid, concessions, area_ha)
        statuses.append(status)
        notes.append(note)
        names.append(f"Clearing patch {idx + 1}")

    gdf["permit_status"] = statuses
    gdf["notes"] = notes
    gdf["name"] = names
    gdf["id"] = [f"live-{i + 1:04d}" for i in range(len(gdf))]

    return gdf.__geo_interface__
