#!/usr/bin/env python3
"""
Detect vegetation loss inside US protected parks and build map overlays.

For each park, this runs the same Sentinel-2 NDVI change detection used for the
Amazon AOI, then clips detections to the National Park Service boundary polygon.
Clearings inside a protected boundary are the signal, since mining and logging
in these parks are generally prohibited.

Outputs:
  data/processed/park_clearings.geojson
  data/processed/park_detection_summary.json

Then run: python scripts/export_for_web.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
import geopandas as gpd
from shapely.geometry import shape

from src.change_detection import (
    NBR_LOSS_THRESHOLD,
    NDVI_LOSS_THRESHOLD,
    PARK_MAX_POLYGONS,
    PARK_MIN_PATCH_AREA_HA,
    VECTOR_SCALE_M,
    change_polygons_fc,
    fc_to_geojson_dict,
)
from src.gee_utils import initialize_ee
from src.hansen_change import METHOD_LABEL as HANSEN_METHOD
from src.hansen_change import change_polygons_geojson as hansen_polygons_geojson
from src.us_parks import US_PARKS, fetch_park_boundary

PROCESSED = REPO_ROOT / "data" / "processed"
BOUNDARIES = REPO_ROOT / "data" / "raw" / "park_boundaries"


def _load_boundary(unit_code: str):
    """Return a single unioned park boundary geometry, or None if unavailable."""
    try:
        path = BOUNDARIES / f"{unit_code}.geojson"
        park = next((p for p in US_PARKS if p.unit_code == unit_code), None)
        extra = park.extra_unit_codes if park else ()
        fetch_park_boundary(unit_code, path, extra_unit_codes=extra)
        gdf = gpd.read_file(path)
        if gdf.empty:
            return None
        return gdf.to_crs("EPSG:4326").union_all()
    except Exception as exc:
        print(f"  Boundary unavailable for {unit_code}: {exc}")
        return None


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    PROCESSED.mkdir(parents=True, exist_ok=True)

    use_gee = True
    try:
        print("Initializing Earth Engine...")
        initialize_ee()
    except Exception as exc:
        print(f"Earth Engine unavailable ({exc}). Using Hansen tree-cover loss tiles.")
        use_gee = False

    all_features: list[dict] = []
    per_park: dict[str, int] = {}
    used_hansen = False

    for park in US_PARKS:
        area = park.study_area
        print(f"\nPark: {area.name} ({park.unit_code})")

        features: list[dict] = []
        if use_gee:
            try:
                fc = change_polygons_fc(
                    area,
                    max_polygons=PARK_MAX_POLYGONS,
                    min_patch_area_ha=PARK_MIN_PATCH_AREA_HA,
                )
                count = fc.size().getInfo()
                print(f"  Change polygons before boundary clip: {count}")
                features = fc_to_geojson_dict(fc).get("features", []) if count else []
            except Exception as exc:
                print(f"  Earth Engine detection failed for {park.unit_code}: {exc}")
                features = []

        if not features:
            print("  Detecting from Hansen tree-cover loss tiles...")
            used_hansen = True
            features = hansen_polygons_geojson(
                area,
                dest_dir=REPO_ROOT / "data" / "raw" / "hansen",
                min_patch_area_ha=PARK_MIN_PATCH_AREA_HA,
                max_polygons=PARK_MAX_POLYGONS,
            ).get("features", [])
            print(f"  Change polygons before boundary clip: {len(features)}")

        boundary = _load_boundary(park.unit_code)
        clipped = boundary is not None

        kept: list[dict] = []
        for feature in features:
            geometry = shape(feature["geometry"])
            if boundary is not None and not boundary.intersects(geometry.centroid):
                continue
            props = feature.setdefault("properties", {})
            props.update(
                {
                    "park_name": area.name,
                    "park_unit": park.unit_code,
                    "threat": park.threat,
                    "boundary_clipped": clipped,
                    "detected_year": area.after_year,
                }
            )
            kept.append(feature)

        for i, feature in enumerate(kept):
            feature["properties"]["id"] = f"{park.unit_code.lower()}-{i + 1:04d}"
            feature["properties"]["name"] = f"{area.name} clearing {i + 1}"

        all_features.extend(kept)
        per_park[park.unit_code] = len(kept)
        print(f"  Kept {len(kept)} clearings ({'inside boundary' if clipped else 'boundary unavailable, using bbox'})")

    out = {"type": "FeatureCollection", "features": all_features}
    out_path = PROCESSED / "park_clearings.geojson"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(out, f)

    summary = {
        "parks": per_park,
        "total_clearings": len(all_features),
        "method": (
            f"{HANSEN_METHOD}, min {PARK_MIN_PATCH_AREA_HA} ha; "
            "clipped to NPS boundary where available"
            if used_hansen
            else (
                f"NDVI loss > {NDVI_LOSS_THRESHOLD} or NBR loss > {NBR_LOSS_THRESHOLD}, "
                f"min {PARK_MIN_PATCH_AREA_HA} ha, {VECTOR_SCALE_M}m; "
                "clipped to NPS boundary where available"
            )
        ),
        "last_updated": date.today().isoformat(),
    }
    summary_path = PROCESSED / "park_detection_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\nWrote {len(all_features)} park clearings to {out_path}")
    print(f"Wrote {summary_path}")
    print("\nNext: python scripts/export_for_web.py")


if __name__ == "__main__":
    main()
