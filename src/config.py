"""
Study-area configuration for the Brazilian Amazon pilot.

All coordinates are WGS84 (EPSG:4326). The test bounding box is intentionally
small (~400 km²) so the first GEE export completes quickly.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StudyArea:
    name: str
    description: str
    # [west, south, east, north]
    bbox: tuple[float, float, float, float]
    before_year: int
    after_year: int
    crs: str = "EPSG:4326"


# Southern Pará — Novo Progresso / BR-163 corridor
# High deforestation + illegal mining pressure; well covered by DETER/PRODES.
SOUTHERN_PARA = StudyArea(
    name="Southern Pará (Novo Progresso corridor)",
    description=(
        "Expanded AOI along the BR-163 highway around Novo Progresso, Pará. "
        "Frequent DETER alerts and documented illegal mining (e.g., Morro dos "
        "Garimpeiros). ~265 km × 245 km extent."
    ),
    bbox=(-57.00, -8.60, -54.60, -6.40),
    before_year=2019,
    after_year=2023,
)

# Default study area for this repo
STUDY_AREA = SOUTHERN_PARA

# Sentinel-2 bands used throughout the pipeline
S2_BANDS = ["B2", "B3", "B4", "B8", "B11", "B12"]

# GEE collection IDs
S2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"
S2_CLOUD_PROB_COLLECTION = "COPERNICUS/S2_CLOUD_PROBABILITY"

# Cloud masking — pixels above this probability are masked out
CLOUD_PROB_THRESHOLD = 40

# Export scale (meters) — Sentinel-2 native 10 m for visible/NIR bands
EXPORT_SCALE_M = 10
