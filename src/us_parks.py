"""
US protected-area study definitions and National Park Service boundary access.

The Brazilian pipeline cross-references clearings against permit registries. US
national parks are not in those registries, so the relevant signal here is
different: vegetation loss detected inside a protected park boundary, where
mining and logging are generally prohibited.

Each park reuses the shared StudyArea structure so it can flow through the same
Sentinel-2 change-detection code as the Amazon AOI.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import requests

from src.config import StudyArea

# NPS park boundary polygons (public ArcGIS REST service, queried by unit code)
NPS_BOUNDARY_URL = (
    "https://services1.arcgis.com/fBc8EJBxQRMcHlei/arcgis/rest/services/"
    "NPS_Land_Resources_Division_Boundary_and_Tract_Data_Service/FeatureServer/2/query"
)


@dataclass(frozen=True)
class Park:
    study_area: StudyArea
    unit_code: str
    threat: str  # "mining" or "logging"
    description: str
    source_url: str
    extra_unit_codes: tuple[str, ...] = ()


def _study_area(name: str, bbox: tuple[float, float, float, float]) -> StudyArea:
    return StudyArea(
        name=name,
        description=name,
        bbox=bbox,
        before_year=2019,
        after_year=2023,
    )


# Bounding boxes are drawn tightly around each unit. Boundary polygons from NPS
# are used to clip detections to the actual protected area when available.
US_PARKS: list[Park] = [
    Park(
        study_area=_study_area(
            "Redwood National and State Parks", (-124.20, 41.05, -123.80, 41.45)
        ),
        unit_code="REDW",
        threat="logging",
        description="Old-growth redwoods targeted by illegal logging and burl poaching.",
        source_url="https://www.nps.gov/redw/index.htm",
    ),
    Park(
        study_area=_study_area(
            "Olympic National Park", (-124.30, 47.45, -123.20, 48.10)
        ),
        unit_code="OLYM",
        threat="logging",
        description="Old-growth cedar and bigleaf maple targeted by timber poaching.",
        source_url="https://www.nps.gov/olym/index.htm",
    ),
    Park(
        study_area=_study_area(
            "Death Valley National Park", (-117.60, 35.70, -116.30, 37.10)
        ),
        unit_code="DEVA",
        threat="mining",
        description="Legacy mining district with ongoing unauthorized digging.",
        source_url="https://www.nps.gov/deva/index.htm",
    ),
    Park(
        study_area=_study_area(
            "Mojave National Preserve", (-116.20, 34.70, -115.00, 35.55)
        ),
        unit_code="MOJA",
        threat="mining",
        description="Many old mining claims and unauthorized mineral prospecting.",
        source_url="https://www.nps.gov/moja/index.htm",
    ),
    Park(
        study_area=_study_area(
            "Sequoia and Kings Canyon National Parks", (-118.95, 36.30, -118.30, 37.15)
        ),
        unit_code="SEKI",
        extra_unit_codes=("SEQU", "KICA"),
        threat="logging",
        description="Remote groves cleared for illegal cultivation that damages forest.",
        source_url="https://www.nps.gov/seki/index.htm",
    ),
    Park(
        study_area=_study_area(
            "Wrangell-St. Elias National Park and Preserve",
            (-143.20, 61.35, -142.30, 61.65),
        ),
        unit_code="WRST",
        threat="mining",
        description="Historic and active mining districts such as Kennecott.",
        source_url="https://www.nps.gov/wrst/index.htm",
    ),
    Park(
        study_area=_study_area(
            "Great Smoky Mountains National Park", (-84.00, 35.40, -83.00, 35.80)
        ),
        unit_code="GRSM",
        threat="logging",
        description="Illegal harvesting of forest products such as ginseng and galax.",
        source_url="https://www.nps.gov/grsm/index.htm",
    ),
]


def fetch_park_boundary(
    unit_code: str,
    dest_path: Path,
    force: bool = False,
    extra_unit_codes: tuple[str, ...] = (),
) -> Path:
    """Download an NPS park boundary polygon as GeoJSON, cached to dest_path."""
    if dest_path.exists() and not force:
        return dest_path

    codes = (unit_code, *extra_unit_codes)
    where = " OR ".join(f"UNIT_CODE='{code}'" for code in codes)
    params = {
        "where": where,
        "outFields": "UNIT_CODE,UNIT_NAME",
        "returnGeometry": "true",
        "outSR": 4326,
        "f": "geojson",
    }
    response = requests.get(NPS_BOUNDARY_URL, params=params, timeout=180)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("features"):
        raise RuntimeError(f"No NPS boundary returned for unit {unit_code}")

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with dest_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f)
    return dest_path
