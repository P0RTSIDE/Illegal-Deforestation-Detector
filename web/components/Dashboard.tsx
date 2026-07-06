"use client";

import dynamic from "next/dynamic";
import type { FeatureCollection } from "geojson";
import type { SummaryData } from "@/lib/types";
import { STATUS_COLORS, STATUS_LABELS, type PermitStatus } from "@/lib/types";

const StudyMap = dynamic(() => import("@/components/StudyMap"), {
  ssr: false,
  loading: () => (
    <div
      className="map-wrap"
      style={{
        display: "grid",
        placeItems: "center",
        color: "#94a3b8",
        background: "#121a2b",
      }}
    >
      Loading map...
    </div>
  ),
});

interface DashboardProps {
  summary: SummaryData;
  studyArea: FeatureCollection;
  flaggedSites: FeatureCollection;
}

export default function Dashboard({
  summary,
  studyArea,
  flaggedSites,
}: DashboardProps) {
  const center: [number, number] = [
    (summary.bbox[1] + summary.bbox[3]) / 2,
    (summary.bbox[0] + summary.bbox[2]) / 2,
  ];

  return (
    <>
      <section className="hero">
        <h1>Satellite-Based Illegal Deforestation / Mining Detector</h1>
        <p>
          Change detection on Sentinel-2 imagery cross-referenced against public
          concession boundaries in the Brazilian Amazon. This dashboard shows
          flagged clearings by permit status — a heuristic signal, not a legal
          finding.
        </p>
        <div className="badge-row">
          <span className="badge">{summary.study_area}</span>
          <span className="badge">
            {summary.before_year} → {summary.after_year}
          </span>
          <span className="badge">
            {summary.data_mode === "demo" ? "Demo data" : "Live — NDVI change detection"}
          </span>
          {summary.data_mode === "live" && summary.method && (
            <span className="badge">{summary.method}</span>
          )}
        </div>
      </section>

      <section className="map-section">
        <div className="card">
          <h2>Interactive map</h2>
          <StudyMap
            studyArea={studyArea}
            flaggedSites={flaggedSites}
            center={center}
            bbox={summary.bbox}
          />
        </div>
      </section>

      <div className="summary-row">
        <div className="card">
          <h2>Summary</h2>
          <div className="stats-grid">
            <div className="stat">
              <div className="label">Flagged sites</div>
              <div className="value">{summary.total_flagged_sites}</div>
            </div>
            <div className="stat">
              <div className="label">Flagged area</div>
              <div className="value">
                {summary.total_flagged_area_ha.toFixed(0)} ha
              </div>
            </div>
            <div className="stat">
              <div className="label">S2 scenes (before)</div>
              <div className="value">{summary.before_image_count}</div>
            </div>
            <div className="stat">
              <div className="label">S2 scenes (after)</div>
              <div className="value">{summary.after_image_count}</div>
            </div>
          </div>
        </div>

        <div className="card">
          <h2>Legend</h2>
          <div className="legend">
            {(Object.keys(STATUS_LABELS) as PermitStatus[]).map((status) => (
              <div className="legend-item" key={status}>
                <span
                  className="swatch"
                  style={{ background: STATUS_COLORS[status] }}
                />
                {STATUS_LABELS[status]} ({summary.by_status[status]})
              </div>
            ))}
            <div className="legend-item">
              <span
                className="swatch"
                style={{
                  background: "transparent",
                  border: "2px dashed #38bdf8",
                }}
              />
              Study area boundary
            </div>
          </div>
        </div>
      </div>

      <section className="section">
        <h2>Pipeline progress</h2>
        <div className="steps">
          <div className="step done">
            <div className="step-num">1</div>
            <div>
              <strong>GEE data pull</strong>
              <p>
                Sentinel-2 composites verified ({summary.before_image_count} /{" "}
                {summary.after_image_count} scenes).
              </p>
            </div>
          </div>
          <div className="step active">
            <div className="step-num">2</div>
            <div>
              <strong>Preprocessing + baseline change detection</strong>
              <p>Cloud masking, tiling, NDVI/NBR spectral index differencing.</p>
            </div>
          </div>
          <div className="step">
            <div className="step-num">3</div>
            <div>
              <strong>Learned model (Siamese / U-Net)</strong>
              <p>Train on Hansen labels with spatial hold-out validation.</p>
            </div>
          </div>
          <div className="step">
            <div className="step-num">4</div>
            <div>
              <strong>Concession cross-reference</strong>
              <p>Spatial join vs ANM SIGMINE + GFW layers.</p>
            </div>
          </div>
          <div className="step">
            <div className="step-num">5</div>
            <div>
              <strong>Replace demo map data with live outputs</strong>
              <p>
                Run <code>python scripts/export_for_web.py</code> after inference.
              </p>
            </div>
          </div>
        </div>
      </section>

      <div className="disclaimer">
        <strong>Limitations:</strong> Flagged sites mean &quot;not accounted for
        in available public concession records,&quot; not proven illegality.
        Concession registries are incomplete; garimpo sites often lack formal
        polygons. 10 m Sentinel-2 misses sub-hectare clearings. No field
        verification in v1.
      </div>

      <footer>
        Last updated: {summary.last_updated}. Built with Next.js + Leaflet.
        Python ML pipeline in repo root.
      </footer>
    </>
  );
}
