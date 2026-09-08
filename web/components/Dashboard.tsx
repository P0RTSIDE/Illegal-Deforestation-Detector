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
        color: "#a8b5ae",
        background: "#141e1b",
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
  parkClearings: FeatureCollection;
}

export default function Dashboard({
  summary,
  studyArea,
  flaggedSites,
  usParks,
  parkClearings,
}: DashboardProps) {
  const [region, setRegion] = useState<MapRegion>("brazil");
  const parkClearingCount = parkClearings.features.length;

  const center: [number, number] = [
    (summary.bbox[1] + summary.bbox[3]) / 2,
    (summary.bbox[0] + summary.bbox[2]) / 2,
  ];

  return (
    <>
      <section className="hero">
        <p className="eyebrow">Brazilian Amazon study</p>
        <h1>Forest clearing and permit map</h1>
        <p>
          Satellite data flags vegetation loss in Southern Pará, then each
          patch is checked against public mining and logging permit records.
          Colored shapes are research flags, not court rulings. Click any shape
          for details and sources.
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

      <aside className="callout callout-warn" aria-label="How to read bare ground">
        <p className="callout-label">Why some yellow or dry ground is not tagged</p>
        <p>
          Bare, tan, or yellow ground is not a flag by itself. This region is
          wet tropical forest. Bright soil usually means pasture, a road, or an
          older clearing, not a dry climate. Shapes mark tree cover that was
          lost between {summary.before_year} and {summary.after_year}. Land
          cleared before {summary.before_year} can look more barren than a
          newer grassy patch and still stay untagged.
        </p>
      </aside>

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
            <h3>Untagged yellow ground</h3>
            <p>
              A yellow or dead-looking strip with no overlay was usually
              already cleared before {summary.before_year}, or was never forest
              in the baseline. The photo shows how the land looks now. The
              overlay only shows recent canopy loss.
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
            Switch regions with the buttons below. Use the layer control in the
            top right to change the base map or hide a layer. Zoom in to inspect
            individual sites.
          </p>
          <aside className="callout callout-warn callout-compact">
            <p className="callout-label">Untagged yellow or dry ground</p>
            <p>
              If a bright strip has no colored shape, it was likely cleared
              before {summary.before_year}, or was never forest. Newer
              clearings can look slightly green as grass returns and still be
              tagged. Older bare ground can look worse and still be skipped.
            </p>
          </aside>
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
            parkClearings={parkClearings}
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
              <div className="label">
                {(summary.method ?? "").toLowerCase().includes("hansen")
                  ? "Change source"
                  : `Satellite scenes (${summary.before_year})`}
              </div>
              <div className="value">
                {(summary.method ?? "").toLowerCase().includes("hansen")
                  ? "Hansen GFC"
                  : summary.before_image_count}
              </div>
            </div>
            <div className="stat">
              <div className="label">
                {(summary.method ?? "").toLowerCase().includes("hansen")
                  ? "Loss years"
                  : `Satellite scenes (${summary.after_year})`}
              </div>
              <div className="value">
                {(summary.method ?? "").toLowerCase().includes("hansen")
                  ? `${summary.before_year} to ${summary.after_year}`
                  : summary.after_image_count}
              </div>
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
                logging pressure. Red shapes show {parkClearingCount} tree-cover
                loss patches detected inside those park boundaries. Switch to the
                US view or use the layer control to show them.
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
          <li>
            <a
              href={DATA_SOURCES.hansen.url}
              target="_blank"
              rel="noopener noreferrer"
            >
              {DATA_SOURCES.hansen.name}
            </a>
            : {DATA_SOURCES.hansen.role}
          </li>
        </ul>
        <p>
          Want the full technical walkthrough? See the{" "}
          <Link href="/methodology">Methodology</Link> page.
        </p>
      </section>

      <div className="disclaimer">
        <strong>Limits of this map:</strong> Flagged areas are automated hints
        from satellite imagery and incomplete public permit records. They are
        not legal findings and have not been verified on the ground. Yellow or
        dry-looking ground without a shape is often older clearing or a road,
        not a missed detection from {summary.before_year} to{" "}
        {summary.after_year}. Small clearings and informal mining sites are
        easy to miss.
      </div>

      <footer>
        Last updated {summary.last_updated}. Public satellite and permit data
        only.
      </footer>
    </>
  );
}
