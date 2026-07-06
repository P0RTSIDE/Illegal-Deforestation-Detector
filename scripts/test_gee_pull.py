#!/usr/bin/env python3
"""
Verify the GEE data pipeline end-to-end without downloading full rasters.

Checks:
  1. Earth Engine initializes with your Cloud project
  2. Sentinel-2 collections return images for before/after years
  3. Metadata is written to data/raw/gee_metadata.json

Optional: pass --export-drive to start a Drive export of both composites.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from repo root without installing the package
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv

from src.config import STUDY_AREA
from src.gee_utils import (
    build_before_after_pair,
    export_image_to_drive,
    get_composite_metadata,
    initialize_ee,
    save_metadata,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Test GEE Sentinel-2 pull for study area")
    parser.add_argument(
        "--export-drive",
        action="store_true",
        help="Start Google Drive exports for before/after composites (async)",
    )
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")

    print(f"Study area: {STUDY_AREA.name}")
    print(f"BBox (W,S,E,N): {STUDY_AREA.bbox}")
    print(f"Years: {STUDY_AREA.before_year} (before) -> {STUDY_AREA.after_year} (after)")
    print()

    print("Initializing Earth Engine...")
    initialize_ee()

    print("Querying Sentinel-2 collection sizes (this may take ~30s)...")
    metadata = get_composite_metadata(STUDY_AREA)

    print("\n--- Pipeline check ---")
    print(f"  Before ({metadata['before_year']}): {metadata['before_image_count']} scenes")
    print(f"  After  ({metadata['after_year']}): {metadata['after_image_count']} scenes")
    print(f"  Bands: {', '.join(metadata['bands'])}")
    print(f"  Cloud mask threshold: {metadata['cloud_prob_threshold']}%")

    if metadata["before_image_count"] == 0 or metadata["after_image_count"] == 0:
        print("\nWARNING: One or both years returned zero images.")
        print("Try widening the bbox or lowering the cloud filter in gee_utils.py.")

    out_path = REPO_ROOT / "data" / "raw" / "gee_metadata.json"
    save_metadata(out_path, metadata)
    print(f"\nMetadata saved to {out_path}")

    if args.export_drive:
        print("\nStarting Drive exports...")
        before, after = build_before_after_pair(STUDY_AREA)
        t1 = export_image_to_drive(
            before,
            description=f"s2_{STUDY_AREA.before_year}_before",
        )
        t2 = export_image_to_drive(
            after,
            description=f"s2_{STUDY_AREA.after_year}_after",
        )
        print(f"  Task 1: {t1.id} — monitor at https://code.earthengine.google.com/tasks")
        print(f"  Task 2: {t2.id}")

    print("\nPipeline check complete.")


if __name__ == "__main__":
    main()
