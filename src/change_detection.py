"""
Baseline spectral change detection using Earth Engine.

Computes NDVI loss between before/after annual composites and vectorizes
significant clearing patches.
"""

from __future__ import annotations

import ee

from src.config import STUDY_AREA, StudyArea
from src.gee_utils import build_before_after_pair, study_area_geometry


# Minimum NDVI drop to flag vegetation loss (tropical forest clearing)
NDVI_LOSS_THRESHOLD = 0.18

# Minimum pre-change NDVI — pixel must have been vegetated
MIN_BEFORE_NDVI = 0.55

# Vectorization scale (m) — 30 m reduces noise vs 10 m native
VECTOR_SCALE_M = 30

# Ignore patches smaller than this (hectares)
MIN_PATCH_AREA_HA = 5.0

# Cap polygons returned via getInfo (GEE response size limit)
MAX_POLYGONS = 250


def compute_ndvi(image: ee.Image) -> ee.Image:
    return image.normalizedDifference(["B8", "B4"]).rename("NDVI")


def build_change_mask(
    area: StudyArea = STUDY_AREA,
    ndvi_loss_threshold: float = NDVI_LOSS_THRESHOLD,
    min_before_ndvi: float = MIN_BEFORE_NDVI,
) -> tuple[ee.Image, ee.Image, ee.Image]:
    """
    Return (before_composite, after_composite, binary_change_mask).
    """
    before, after = build_before_after_pair(area)
    ndvi_before = compute_ndvi(before)
    ndvi_after = compute_ndvi(after)
    ndvi_loss = ndvi_before.subtract(ndvi_after).rename("NDVI_loss")

    was_vegetated = ndvi_before.gt(min_before_ndvi)
    significant_loss = ndvi_loss.gt(ndvi_loss_threshold)
    change = was_vegetated.And(significant_loss).selfMask().rename("change")

    return before, after, change


def change_polygons_fc(
    area: StudyArea = STUDY_AREA,
    max_polygons: int = MAX_POLYGONS,
) -> ee.FeatureCollection:
    """Vectorize change mask and filter by minimum patch area."""
    _, _, change = build_change_mask(area)
    geom = study_area_geometry(area)

    vectors = change.reduceToVectors(
        geometry=geom,
        scale=VECTOR_SCALE_M,
        geometryType="polygon",
        eightConnected=False,
        labelProperty="change",
        maxPixels=1e10,
    )

    def add_metrics(feature: ee.Feature) -> ee.Feature:
        area_ha = feature.geometry().area(maxError=1).divide(10000)
        return feature.set(
            {
                "area_ha": area_ha,
                "method": f"NDVI loss > {NDVI_LOSS_THRESHOLD}, scale {VECTOR_SCALE_M}m",
                "detected_year": area.after_year,
            }
        )

    filtered = (
        vectors.map(add_metrics)
        .filter(ee.Filter.gte("area_ha", MIN_PATCH_AREA_HA))
        .sort("area_ha", False)
        .limit(max_polygons)
    )
    return filtered


def fc_to_geojson_dict(fc: ee.FeatureCollection) -> dict:
    """Download FeatureCollection as GeoJSON-like dict via getInfo()."""
    return fc.getInfo()
