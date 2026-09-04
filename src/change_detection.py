"""
Baseline spectral change detection using Earth Engine.

Flags pixels that lose vegetation between before/after annual composites using
NDVI and NBR, fills small holes in those patches, then vectorizes them.
"""

from __future__ import annotations

import math

import ee

from src.config import STUDY_AREA, StudyArea
from src.gee_utils import build_before_after_pair, study_area_geometry


# Vegetation index drop needed to flag a pixel
NDVI_LOSS_THRESHOLD = 0.12
NBR_LOSS_THRESHOLD = 0.10

# Pixel must have been vegetated before the change
MIN_BEFORE_NDVI = 0.40

# Vectorization scale (m). 30 m keeps large-area downloads practical.
VECTOR_SCALE_M = 30

# Ignore patches smaller than this (hectares)
MIN_PATCH_AREA_HA = 2.0

# Parks use a lower floor so smaller interior clearings are kept
PARK_MIN_PATCH_AREA_HA = 0.5

# Cap polygons returned via getInfo (GEE response size limit)
MAX_POLYGONS = 1200
PARK_MAX_POLYGONS = 200

# Split large AOIs so vectorization stays within GEE limits
TILE_SPAN_DEG = 0.9

# Page size when downloading FeatureCollections
DOWNLOAD_PAGE_SIZE = 200


def compute_ndvi(image: ee.Image) -> ee.Image:
    return image.normalizedDifference(["B8", "B4"]).rename("NDVI")


def compute_nbr(image: ee.Image) -> ee.Image:
    return image.normalizedDifference(["B8", "B12"]).rename("NBR")


def _close_mask(change: ee.Image) -> ee.Image:
    """Fill one-pixel holes so a visible clearing stays one polygon."""
    filled = change.focal_max(radius=1, kernelType="square", units="pixels")
    return filled.focal_min(radius=1, kernelType="square", units="pixels")


def build_change_mask(
    area: StudyArea = STUDY_AREA,
    ndvi_loss_threshold: float = NDVI_LOSS_THRESHOLD,
    nbr_loss_threshold: float = NBR_LOSS_THRESHOLD,
    min_before_ndvi: float = MIN_BEFORE_NDVI,
) -> tuple[ee.Image, ee.Image, ee.Image]:
    """
    Return (before_composite, after_composite, binary_change_mask).
    """
    before, after = build_before_after_pair(area)
    ndvi_before = compute_ndvi(before)
    ndvi_after = compute_ndvi(after)
    nbr_before = compute_nbr(before)
    nbr_after = compute_nbr(after)

    ndvi_loss = ndvi_before.subtract(ndvi_after)
    nbr_loss = nbr_before.subtract(nbr_after)

    was_vegetated = ndvi_before.gt(min_before_ndvi)
    significant_loss = ndvi_loss.gt(ndvi_loss_threshold).Or(
        nbr_loss.gt(nbr_loss_threshold)
    )
    change = was_vegetated.And(significant_loss).selfMask().rename("change")
    change = _close_mask(change).selfMask().rename("change")

    return before, after, change


def _tile_bboxes(
    bbox: tuple[float, float, float, float],
    max_span: float = TILE_SPAN_DEG,
) -> list[tuple[float, float, float, float]]:
    west, south, east, north = bbox
    width = east - west
    height = north - south
    n_cols = max(1, math.ceil(width / max_span))
    n_rows = max(1, math.ceil(height / max_span))
    dw = width / n_cols
    dh = height / n_rows
    tiles: list[tuple[float, float, float, float]] = []
    for i in range(n_cols):
        for j in range(n_rows):
            tiles.append(
                (
                    west + i * dw,
                    south + j * dh,
                    west + (i + 1) * dw,
                    south + (j + 1) * dh,
                )
            )
    return tiles


def _method_label() -> str:
    return (
        f"NDVI loss > {NDVI_LOSS_THRESHOLD} or NBR loss > {NBR_LOSS_THRESHOLD}, "
        f"scale {VECTOR_SCALE_M}m"
    )


def change_polygons_fc(
    area: StudyArea = STUDY_AREA,
    max_polygons: int = MAX_POLYGONS,
    min_patch_area_ha: float = MIN_PATCH_AREA_HA,
) -> ee.FeatureCollection:
    """Vectorize the change mask and keep patches above the area floor."""
    _, _, change = build_change_mask(area)

    collections: list[ee.FeatureCollection] = []
    for tile in _tile_bboxes(area.bbox):
        tile_geom = ee.Geometry.Rectangle(list(tile), proj=area.crs, geodesic=False)
        collections.append(
            change.reduceToVectors(
                geometry=tile_geom,
                scale=VECTOR_SCALE_M,
                geometryType="polygon",
                eightConnected=True,
                labelProperty="change",
                maxPixels=1e10,
            )
        )

    vectors = (
        collections[0]
        if len(collections) == 1
        else ee.FeatureCollection(collections).flatten()
    )

    def add_metrics(feature: ee.Feature) -> ee.Feature:
        area_ha = feature.geometry().area(maxError=1).divide(10000)
        return feature.set(
            {
                "area_ha": area_ha,
                "method": _method_label(),
                "detected_year": area.after_year,
            }
        )

    return (
        vectors.map(add_metrics)
        .filter(ee.Filter.gte("area_ha", min_patch_area_ha))
        .sort("area_ha", False)
        .limit(max_polygons)
    )


def fc_to_geojson_dict(
    fc: ee.FeatureCollection,
    page_size: int = DOWNLOAD_PAGE_SIZE,
) -> dict:
    """Download a FeatureCollection as GeoJSON, paging if needed."""
    total = int(fc.size().getInfo() or 0)
    if total == 0:
        return {"type": "FeatureCollection", "features": []}
    if total <= page_size:
        return fc.getInfo()

    features: list[dict] = []
    for start in range(0, total, page_size):
        chunk = ee.FeatureCollection(fc.toList(page_size, start)).getInfo()
        features.extend(chunk.get("features", []))
    return {"type": "FeatureCollection", "features": features}
