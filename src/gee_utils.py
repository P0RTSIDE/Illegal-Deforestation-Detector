"""
Google Earth Engine helpers for Sentinel-2 composite building and export.

Usage (after authentication):
    python scripts/test_gee_pull.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

import ee

from src.config import (
    CLOUD_PROB_THRESHOLD,
    EXPORT_SCALE_M,
    S2_BANDS,
    S2_CLOUD_PROB_COLLECTION,
    S2_COLLECTION,
    STUDY_AREA,
    StudyArea,
)

# Project ID can be set via environment variable or .env file
GEE_PROJECT_ENV = "GEE_PROJECT_ID"


def get_project_id() -> str | None:
    """Return the Google Cloud project ID used for ee.Initialize()."""
    return os.environ.get(GEE_PROJECT_ENV)


def initialize_ee(project: str | None = None) -> None:
    """
    Initialize the Earth Engine Python client.

    Requires prior authentication via `ee.Authenticate()` or
    `earthengine authenticate` in a terminal.
    """
    project = project or get_project_id()
    if not project:
        raise ValueError(
            f"Set the {GEE_PROJECT_ENV} environment variable to your "
            "Google Cloud project ID (registered at "
            "https://code.earthengine.google.com/register)."
        )
    ee.Initialize(project=project)


def study_area_geometry(area: StudyArea = STUDY_AREA) -> ee.Geometry:
    """Convert a StudyArea bbox to an ee.Geometry rectangle."""
    west, south, east, north = area.bbox
    return ee.Geometry.Rectangle([west, south, east, north], proj=area.crs, geodesic=False)


def _mask_s2_clouds(image: ee.Image) -> ee.Image:
    """
    Mask clouds/shadows using the Scene Classification Layer (SCL).

    More reliable than joining s2cloudless per scene — some tiles lack a
    matching COPERNICUS/S2_CLOUD_PROBABILITY entry.
    """
    scl = image.select("SCL")
    # 4=vegetation, 5=bare, 6=water, 7=unclassified (low cloud)
    clear = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)).Or(scl.eq(7))
    return image.updateMask(clear)


def get_s2_collection(
    area: StudyArea,
    year: int,
    bands: Iterable[str] = S2_BANDS,
) -> ee.ImageCollection:
    """
    Return a cloud-masked Sentinel-2 L2A collection for one calendar year.

    Uses the full calendar year to maximize clear observations in tropical AOI.
    """
    geom = study_area_geometry(area)
    start = f"{year}-01-01"
    end = f"{year}-12-31"

    collection = (
        ee.ImageCollection(S2_COLLECTION)
        .filterBounds(geom)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80))
        .map(_mask_s2_clouds)
        .select(list(bands))
    )
    return collection


def build_annual_median_composite(
    area: StudyArea,
    year: int,
    bands: Iterable[str] = S2_BANDS,
) -> ee.Image:
    """Median composite for a calendar year — reduces residual cloud noise."""
    collection = get_s2_collection(area, year, bands=bands)
    composite = collection.median().clip(study_area_geometry(area))
    return composite.set(
        {
            "year": year,
            "study_area": area.name,
            "bands": list(bands),
        }
    )


def build_before_after_pair(
    area: StudyArea = STUDY_AREA,
    bands: Iterable[str] = S2_BANDS,
) -> tuple[ee.Image, ee.Image]:
    """Return (before, after) median composites for the configured years."""
    before = build_annual_median_composite(area, area.before_year, bands=bands)
    after = build_annual_median_composite(area, area.after_year, bands=bands)
    return before, after


def export_image_to_drive(
    image: ee.Image,
    description: str,
    folder: str = "deforestation-detector",
    region: StudyArea = STUDY_AREA,
    scale: int = EXPORT_SCALE_M,
    max_pixels: int = 1e9,
) -> ee.batch.Task:
    """
    Start a Drive export task. Poll with task.status() or monitor in GEE Code Editor.
    """
    task = ee.batch.Export.image.toDrive(
        image=image,
        description=description,
        folder=folder,
        region=study_area_geometry(region),
        scale=scale,
        maxPixels=max_pixels,
        fileFormat="GeoTIFF",
        crs="EPSG:4326",
    )
    task.start()
    return task


def get_composite_metadata(
    area: StudyArea = STUDY_AREA,
) -> dict:
    """
    Lightweight sanity check — returns image counts per year without downloading rasters.
    Useful to verify the pipeline before starting an export.
    """
    before_count = get_s2_collection(area, area.before_year).size().getInfo()
    after_count = get_s2_collection(area, area.after_year).size().getInfo()

    return {
        "study_area": area.name,
        "bbox": area.bbox,
        "before_year": area.before_year,
        "after_year": area.after_year,
        "before_image_count": before_count,
        "after_image_count": after_count,
        "bands": list(S2_BANDS),
        "cloud_prob_threshold": CLOUD_PROB_THRESHOLD,
    }


def save_metadata(path: Path, metadata: dict) -> None:
    """Write metadata JSON for reproducibility."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
