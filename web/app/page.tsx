import Dashboard from "@/components/Dashboard";
import SiteNav from "@/components/SiteNav";
import type { FeatureCollection } from "geojson";
import type { SummaryData } from "@/lib/types";
import { readFile } from "fs/promises";
import path from "path";

async function loadJson<T>(filename: string): Promise<T> {
  const filePath = path.join(process.cwd(), "public", "data", filename);
  const raw = await readFile(filePath, "utf-8");
  return JSON.parse(raw) as T;
}

export default async function HomePage() {
  const [summary, studyArea, flaggedSites, usParks, parkClearings] =
    await Promise.all([
      loadJson<SummaryData>("summary.json"),
      loadJson<FeatureCollection>("study-area.geojson"),
      loadJson<FeatureCollection>("flagged-sites.geojson"),
      loadJson<FeatureCollection>("us-parks.geojson"),
      loadJson<FeatureCollection>("park-clearings.geojson"),
    ]);

  return (
    <>
      <SiteNav active="dashboard" />
      <main>
        <Dashboard
          summary={summary}
          studyArea={studyArea}
          flaggedSites={flaggedSites}
          usParks={usParks}
          parkClearings={parkClearings}
        />
      </main>
    </>
  );
}
