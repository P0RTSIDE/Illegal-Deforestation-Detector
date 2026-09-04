"""
Local tree-cover-loss detection from Hansen Global Forest Change tiles.

Used when Earth Engine is unavailable, and as a more complete clearing map
than a capped NDVI pull. Tiles are public 30 m GeoTIFFs.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
import requests
from rasterio.features import shapes
from rasterio.windows import from_bounds
from shapely.geometry import box, shape

from src.config import STUDY_AREA, StudyArea

HANSEN_VERSION = "GFC-2023-v1.11"
HANSEN_BASE = (
    f"https://storage.googleapis.com/earthenginepartners-hansen/{HANSEN_VERSION}"
)

# lossyear encoding: 1 = 2001, 19 = 2019, 23 = 2023
LOSS_YEAR_START = 19
LOSS_YEAR_END = 23

METHOD_LABEL = "Hansen Global Forest Change tree-cover loss 2019-2023, 30 m"


def _tile_label(lat: float, lon: float) -> str:
    """Hansen tile id for the 10-degree cell containing a point (NW corner)."""
    west = int(np.floor(lon / 10.0) * 10)
    north = int(np.ceil(lat / 10.0) * 10)
    if abs(north) < 1e-9:
        north = 0
    ns = "N" if north >= 0 else "S"
    ew = "E" if west >= 0 else "W"
    return f"{abs(north):02d}{ns}_{abs(west):03d}{ew}"


def tiles_for_bbox(bbox: tuple[float, float, float, float]) -> list[str]:
    west, south, east, north = bbox
    lon = int(np.floor(west / 10.0) * 10)
    lon_end = int(np.floor((east - 1e-9) / 10.0) * 10)
    north_edge = int(np.ceil((south + 1e-9) / 10.0) * 10)
    north_end = int(np.ceil(north / 10.0) * 10)
    labels: list[str] = []
    while lon <= lon_end:
        edge = north_edge
        while edge <= north_end:
            ns = "N" if edge >= 0 else "S"
            ew = "E" if lon >= 0 else "W"
            labels.append(f"{abs(edge):02d}{ns}_{abs(lon):03d}{ew}")
            edge += 10
        lon += 10
    return sorted(set(labels))


def _tile_url(layer: str, tile: str) -> str:
    return f"{HANSEN_BASE}/Hansen_{HANSEN_VERSION}_{layer}_{tile}.tif"


def download_lossyear_tile(tile: str, dest_dir: Path, force: bool = False) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"hansen_lossyear_{tile}.tif"
    if dest.exists() and not force:
        return dest

    url = _tile_url("lossyear", tile)
    print(f"Downloading Hansen tile {tile} ...")
    response = requests.get(url, timeout=300, stream=True)
    response.raise_for_status()
    with dest.open("wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
    return dest


def _read_window(path: Path, bbox: tuple[float, float, float, float]):
    west, south, east, north = bbox
    with rasterio.open(path) as src:
        window = from_bounds(west, south, east, north, transform=src.transform)
        window = window.round_offsets().round_lengths()
        data = src.read(1, window=window, boundless=True, fill_value=0)
        transform = src.window_transform(window)
    return data, transform


def change_polygons_geojson(
    area: StudyArea = STUDY_AREA,
    dest_dir: Path | None = None,
    min_patch_area_ha: float = 2.0,
    max_polygons: int = 1200,
    year_start: int = LOSS_YEAR_START,
    year_end: int = LOSS_YEAR_END,
) -> dict:
    """
    Vectorize Hansen loss pixels in the study bbox for the configured years.
    """
    if dest_dir is None:
        dest_dir = Path("data") / "raw" / "hansen"

    tiles = tiles_for_bbox(area.bbox)
    geoms = []
    for tile in tiles:
        path = download_lossyear_tile(tile, dest_dir)
        loss, transform = _read_window(path, area.bbox)
        mask = (loss >= year_start) & (loss <= year_end)
        if not mask.any():
            continue
        for geom, value in shapes(
            mask.astype(np.uint8),
            mask=mask,
            transform=transform,
        ):
            if value != 1:
                continue
            poly = shape(geom)
            if not poly.is_empty:
                geoms.append(poly)

    if not geoms:
        return {"type": "FeatureCollection", "features": []}

    gdf = gpd.GeoDataFrame(geometry=geoms, crs="EPSG:4326")
    gdf["geometry"] = gdf.geometry.buffer(0)
    clip = box(*area.bbox)
    gdf = gdf[gdf.intersects(clip)].copy()
    gdf["geometry"] = gdf.geometry.intersection(clip)
    gdf = gdf[~gdf.geometry.is_empty]

    metric = gdf.to_crs("EPSG:3857")
    gdf["area_ha"] = metric.area / 10000.0
    gdf = gdf[gdf["area_ha"] >= min_patch_area_ha]
    gdf = gdf.sort_values("area_ha", ascending=False).head(max_polygons)
    gdf["geometry"] = gdf.geometry.simplify(0.0002, preserve_topology=True)
    gdf["method"] = METHOD_LABEL
    gdf["detected_year"] = area.after_year

    return gdf.__geo_interface__
