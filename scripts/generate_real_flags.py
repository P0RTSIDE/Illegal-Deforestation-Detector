#!/usr/bin/env python3
"""
Generate real flagged clearing polygons from Sentinel-2 NDVI change detection
and cross-reference against mining (ANM SIGMINE) and logging (GFW) permits.

Outputs:
  data/processed/flagged_sites.geojson
  data/processed/detection_summary.json

Then run: python scripts/export_for_web.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

from src.change_detection import (
    MIN_PATCH_AREA_HA,
    NDVI_LOSS_THRESHOLD,
    VECTOR_SCALE_M,
    change_polygons_fc,
    fc_to_geojson_dict,
)
from src.config import STUDY_AREA
from src.gee_utils import get_composite_metadata, initialize_ee, save_metadata
from src.geo_crossref import (
    cross_reference_geojson,
    download_sigmine_para,
    load_logging_concessions,
    load_mining_concessions,
)

PROCESSED = REPO_ROOT / "data" / "processed"
RAW = REPO_ROOT / "data" / "raw"
MINING_DIR = RAW / "concessions" / "anm_sigmine_pa"
LOGGING_DIR = RAW / "concessions" / "logging"


def write_outputs(geojson: dict, meta: dict, mining, logging) -> None:
    flagged = cross_reference_geojson(geojson, mining, logging)

    out_path = PROCESSED / "flagged_sites.geojson"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(flagged, f)

    features = flagged.get("features", [])
    status_counts = Counter(f["properties"]["permit_status"] for f in features)
    total_area = sum(float(f["properties"].get("area_ha", 0)) for f in features)

    summary = {
        "study_area": STUDY_AREA.name,
        "bbox": list(STUDY_AREA.bbox),
        "before_year": STUDY_AREA.before_year,
        "after_year": STUDY_AREA.after_year,
        "before_image_count": meta["before_image_count"],
        "after_image_count": meta["after_image_count"],
        "total_flagged_sites": len(features),
        "total_flagged_area_ha": round(total_area, 1),
        "by_status": {
            "likely_unpermitted": status_counts.get("likely_unpermitted", 0),
            "likely_exceeding_permit": status_counts.get("likely_exceeding_permit", 0),
            "likely_permitted": status_counts.get("likely_permitted", 0),
            "unknown": status_counts.get("unknown", 0),
        },
        "data_mode": "live",
        "method": (
            f"NDVI loss > {NDVI_LOSS_THRESHOLD}, min {MIN_PATCH_AREA_HA} ha, {VECTOR_SCALE_M}m; "
            "cross-ref vs ANM SIGMINE + GFW logging"
        ),
        "last_updated": date.today().isoformat(),
    }

    summary_path = PROCESSED / "detection_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print()
    print("--- Results ---")
    print(f"  Flagged sites: {summary['total_flagged_sites']}")
    print(f"  Total area: {summary['total_flagged_area_ha']} ha")
    print(f"  By status: {dict(status_counts)}")
    print(f"  Wrote {out_path}")
    print(f"  Wrote {summary_path}")
    print()
    print("Next: python scripts/export_for_web.py")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-gee",
        action="store_true",
        help="Reuse data/processed/raw_change.geojson (skip Earth Engine)",
    )
    args = parser.parse_args()
    load_dotenv(REPO_ROOT / ".env")
    PROCESSED.mkdir(parents=True, exist_ok=True)

    print(f"Study area: {STUDY_AREA.name}")
    print(f"NDVI loss threshold: {NDVI_LOSS_THRESHOLD}")
    print(f"Min patch area: {MIN_PATCH_AREA_HA} ha")
    print(f"Vector scale: {VECTOR_SCALE_M} m")
    print()

    meta_path = RAW / "gee_metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        meta = {"before_image_count": 0, "after_image_count": 0}

    raw_path = PROCESSED / "raw_change.geojson"

    if args.skip_gee and raw_path.exists():
        print(f"Reusing cached change polygons from {raw_path}")
        geojson = json.loads(raw_path.read_text(encoding="utf-8"))
    else:
        print("Initializing Earth Engine...")
        initialize_ee()

        print("Updating GEE metadata...")
        meta = get_composite_metadata(STUDY_AREA)
        save_metadata(meta_path, meta)

        print("Computing change polygons in GEE (may take 1-3 minutes)...")
        fc = change_polygons_fc(STUDY_AREA)
        count = fc.size().getInfo()
        print(f"  Polygons after filter: {count}")

        if count == 0:
            print("No change polygons found. Try lowering NDVI_LOSS_THRESHOLD or MIN_PATCH_AREA_HA.")
            sys.exit(1)

        print("Downloading polygon geometries from GEE...")
        geojson = fc_to_geojson_dict(fc)
        with raw_path.open("w", encoding="utf-8") as f:
            json.dump(geojson, f)
        print(f"  Cached raw change polygons to {raw_path}")

    print("Loading ANM SIGMINE mining permits for Pará...")
    shp_path = download_sigmine_para(MINING_DIR)
    mining = load_mining_concessions(shp_path)
    print(f"  Loaded {len(mining)} mining permit polygons")

    print("Loading logging permits for study area...")
    logging = load_logging_concessions(LOGGING_DIR, STUDY_AREA.bbox)
    print(f"  Loaded {len(logging)} logging permit polygons")

    print("Cross-referencing clearings vs mining and logging permits...")
    write_outputs(geojson, meta, mining, logging)


if __name__ == "__main__":
    main()
