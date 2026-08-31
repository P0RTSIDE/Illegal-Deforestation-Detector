"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useState } from "react";
import type { FeatureCollection } from "geojson";
import type { SummaryData } from "@/lib/types";
import { STATUS_COLORS, type PermitStatus } from "@/lib/types";
import type { MapRegion } from "@/components/StudyMap";
import {
  STATUS_LABELS_PLAIN,
  STATUS_DESCRIPTIONS,
  DATA_SOURCES,
} from "@/lib/copy";

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
  usParks: FeatureCollection;
}

export default function Dashboard({
  summary,
  studyArea,
  flaggedSites,
  usParks,
}: DashboardProps) {
  const [region, setRegion] = useState<MapRegion>("brazil");

  const center: [number, number] = [
    (summary.bbox[1] + summary.bbox[3]) / 2,
    (summary.bbox[0] + summary.bbox[2]) / 2,
  ];

  return (
    <>
      <section className="hero">
        <h1>Forest Clearing &amp; Permit Map</h1>
        <p>
          This map shows places where satellite images detected vegetation loss
          in the Brazilian Amazon, then checks those spots against public mining
          and logging permit records. Colored shapes are flagged areas, not court
          rulings. Click any shape for details and data sources.
        </p>
        <div className="badge-row">
          <span className="badge">{summary.study_area}</span>
          <span className="badge">
            Comparing {summary.before_year} to {summary.after_year}
          </span>
          <span className="badge">
            {summary.data_mode === "demo"
              ? "Sample data"
              : "Live satellite analysis"}
          </span>
        </div>
      </section>

      <section className="card how-to-read">
        <h2>How to read the map</h2>
        <div className="how-to-grid">
          <div>
            <h3>Colored shapes</h3>
            <p>
              Each colored polygon is a patch where satellite data shows likely
              vegetation loss between {summary.before_year} and{" "}
              {summary.after_year}. Bigger shapes mean larger cleared areas.
            </p>
          </div>
          <div>
            <h3>Blue dashed box</h3>
            <p>
              The blue outline is the study region we analyzed. Only clearings
              inside this box are shown.
            </p>
          </div>
          <div>
            <h3>Click a shape</h3>
            <p>
              Click any flagged area to open a popup with plain-language status,
              cleared area size, detection method, and links to the public data
              behind the flag.
            </p>
          </div>
          <div>
            <h3>What this is not</h3>
            <p>
              This tool does not prove illegal activity. It highlights clearings
              that are not explained by available public permit records, or that
              may not match those records.
            </p>
          </div>
        </div>
      </section>

      <section className="map-section">
        <div className="card">
          <h2>Interactive map</h2>
          <p className="card-intro">
            Use the buttons below to move between the Amazon study area and a
            reference layer of US protected parks with illegal mining or logging
            pressure. Use the layer control (top right) to switch base maps or
            hide a layer, and zoom in to inspect individual sites.
          </p>
          <div className="region-switch" role="group" aria-label="Map region">
            <button
              type="button"
              className={`region-btn${region === "brazil" ? " active" : ""}`}
              onClick={() => setRegion("brazil")}
              aria-pressed={region === "brazil"}
            >
              Brazil: Amazon study area
            </button>
            <button
              type="button"
              className={`region-btn${region === "usa" ? " active" : ""}`}
              onClick={() => setRegion("usa")}
              aria-pressed={region === "usa"}
            >
              US: protected parks
            </button>
          </div>
          <StudyMap
            studyArea={studyArea}
            flaggedSites={flaggedSites}
            usParks={usParks}
            center={center}
            bbox={summary.bbox}
            region={region}
          />
        </div>
      </section>

      <div className="summary-row">
        <div className="card">
          <h2>At a glance</h2>
          <div className="stats-grid">
            <div className="stat">
              <div className="label">Flagged areas</div>
              <div className="value">{summary.total_flagged_sites}</div>
            </div>
            <div className="stat">
              <div className="label">Total cleared area</div>
              <div className="value">
                {summary.total_flagged_area_ha.toFixed(0)} ha
              </div>
            </div>
            <div className="stat">
              <div className="label">Satellite scenes ({summary.before_year})</div>
              <div className="value">{summary.before_image_count}</div>
            </div>
            <div className="stat">
              <div className="label">Satellite scenes ({summary.after_year})</div>
              <div className="value">{summary.after_image_count}</div>
            </div>
          </div>
        </div>

        <div className="card">
          <h2>What the colors mean</h2>
          <div className="legend legend-detailed">
            {(Object.keys(STATUS_LABELS_PLAIN) as PermitStatus[]).map(
              (status) => (
                <div className="legend-block" key={status}>
                  <div className="legend-item">
                    <span
                      className="swatch"
                      style={{ background: STATUS_COLORS[status] }}
                    />
                    <strong>{STATUS_LABELS_PLAIN[status]}</strong>
                    <span className="legend-count">
                      ({summary.by_status[status]})
                    </span>
                  </div>
                  <p className="legend-desc">{STATUS_DESCRIPTIONS[status]}</p>
                </div>
              )
            )}
            <div className="legend-block">
              <div className="legend-item">
                <span
                  className="swatch"
                  style={{
                    background: "transparent",
                    border: "2px dashed #38bdf8",
                  }}
                />
                <strong>Study area boundary</strong>
              </div>
              <p className="legend-desc">
                The region covered by this analysis. The map zooms to this box
                on load.
              </p>
            </div>
            <div className="legend-block">
              <div className="legend-item">
                <span
                  className="swatch swatch-dot"
                  style={{ background: "#f59e0b" }}
                />
                <strong>US park: illegal mining</strong>
              </div>
              <div className="legend-item">
                <span
                  className="swatch swatch-dot"
                  style={{ background: "#a855f7" }}
                />
                <strong>US park: illegal logging</strong>
              </div>
              <p className="legend-desc">
                Dots mark US protected areas with documented illegal mining or
                logging pressure. This is a reference layer for context, not part
                of the Amazon satellite analysis. Switch to the US view or use
                the layer control to show them.
              </p>
            </div>
          </div>
        </div>
      </div>

      <section className="card sources-card">
        <h2>Public data behind this map</h2>
        <ul className="sources-list">
          <li>
            <a
              href={DATA_SOURCES.sentinel2.url}
              target="_blank"
              rel="noopener noreferrer"
            >
              {DATA_SOURCES.sentinel2.name}
            </a>
            : {DATA_SOURCES.sentinel2.role}
          </li>
          <li>
            <a
              href={DATA_SOURCES.anm_sigmine.url}
              target="_blank"
              rel="noopener noreferrer"
            >
              {DATA_SOURCES.anm_sigmine.name}
            </a>
            : {DATA_SOURCES.anm_sigmine.role}
          </li>
          <li>
            <a
              href={DATA_SOURCES.gfw_logging.url}
              target="_blank"
              rel="noopener noreferrer"
            >
              {DATA_SOURCES.gfw_logging.name}
            </a>
            : {DATA_SOURCES.gfw_logging.role}
          </li>
        </ul>
        <p>
          Want the full technical walkthrough? See the{" "}
          <Link href="/methodology">Methodology</Link> page.
        </p>
      </section>

      <div className="disclaimer">
        <strong>Important:</strong> Flagged areas are automated hints based on
        satellite imagery and incomplete public permit databases. They are not
        legal findings and have not been verified on the ground. Small clearings
        and informal mining sites are easy to miss.
      </div>

      <footer>
        Last updated: {summary.last_updated}. Built with Next.js and Leaflet.
      </footer>
    </>
  );
}
