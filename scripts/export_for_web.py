#!/usr/bin/env python3
"""
Copy pipeline outputs into web/public/data/ for Vercel deployment.

Run after change detection + concession cross-reference produces real GeoJSON.
Until then, the web app ships with demo polygons in web/public/data/.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DATA = REPO_ROOT / "web" / "public" / "data"
RAW = REPO_ROOT / "data" / "raw"
PROCESSED = REPO_ROOT / "data" / "processed"


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def export_gee_metadata() -> None:
    """Merge GEE metadata into summary.json."""
    meta_path = RAW / "gee_metadata.json"
    summary_path = WEB_DATA / "summary.json"

    if not meta_path.exists():
        print(f"Skip: {meta_path} not found (run test_gee_pull.py first)")
        return

    meta = _load_json(meta_path)
    summary = _load_json(summary_path) if summary_path.exists() else {}

    summary.update(
        {
            "study_area": meta.get("study_area", summary.get("study_area")),
            "bbox": meta.get("bbox", summary.get("bbox")),
            "before_year": meta.get("before_year"),
            "after_year": meta.get("after_year"),
            "before_image_count": meta.get("before_image_count"),
            "after_image_count": meta.get("after_image_count"),
            "last_updated": date.today().isoformat(),
        }
    )

    WEB_DATA.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Updated {summary_path}")


def export_live_flagged_sites() -> None:
    """Replace demo flagged sites when pipeline output exists."""
    candidates = [
        PROCESSED / "flagged_sites.geojson",
        RAW / "flagged_sites.geojson",
        REPO_ROOT / "reports" / "flagged_sites.geojson",
    ]

    summary_path = WEB_DATA / "summary.json"
    detection_summary = PROCESSED / "detection_summary.json"

    for src in candidates:
        if src.exists():
            dst = WEB_DATA / "flagged-sites.geojson"
            shutil.copy2(src, dst)
            print(f"Copied {src} -> {dst}")

            if detection_summary.exists():
                summary = _load_json(detection_summary)
                WEB_DATA.mkdir(parents=True, exist_ok=True)
                with summary_path.open("w", encoding="utf-8") as f:
                    json.dump(summary, f, indent=2)
                print(f"Updated {summary_path} from detection_summary.json")
            elif summary_path.exists():
                summary = _load_json(summary_path)
                summary["data_mode"] = "live"
                summary["last_updated"] = date.today().isoformat()
                with summary_path.open("w", encoding="utf-8") as f:
                    json.dump(summary, f, indent=2)
            return

    print("No live flagged_sites.geojson found — keeping demo map data.")


def export_park_clearings() -> None:
    """Copy detected US park clearings, or ensure an empty overlay exists."""
    src = PROCESSED / "park_clearings.geojson"
    dst = WEB_DATA / "park-clearings.geojson"

    if src.exists():
        shutil.copy2(src, dst)
        print(f"Copied {src} -> {dst}")
    elif not dst.exists():
        WEB_DATA.mkdir(parents=True, exist_ok=True)
        with dst.open("w", encoding="utf-8") as f:
            json.dump({"type": "FeatureCollection", "features": []}, f)
        print(f"Wrote empty {dst} (run generate_park_flags.py for real detections)")


def export_study_area() -> None:
    """Write study-area boundary from config, keeping it in sync on each run."""
    dst = WEB_DATA / "study-area.geojson"

    sys.path.insert(0, str(REPO_ROOT))
    from src.config import STUDY_AREA

    west, south, east, north = STUDY_AREA.bbox
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "Study area AOI",
                    "study_area": STUDY_AREA.name,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [west, south],
                            [east, south],
                            [east, north],
                            [west, north],
                            [west, south],
                        ]
                    ],
                },
            }
        ],
    }
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)
    print(f"Wrote {dst}")


def main() -> None:
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    export_study_area()
    export_gee_metadata()
    export_live_flagged_sites()
    export_park_clearings()
    print("\nWeb data export complete. Deploy with: cd web && npm run build")


if __name__ == "__main__":
    main()
