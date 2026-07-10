import type { Metadata } from "next";
import Link from "next/link";
import SiteNav from "@/components/SiteNav";

export const metadata: Metadata = {
  title: "Methodology | Deforestation Detector",
  description:
    "Technical documentation for Sentinel-2 change detection and public concession cross-referencing in the Brazilian Amazon.",
};

const SOURCE_LINKS = {
  s2: "https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED",
  s2cloud: "https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_CLOUD_PROBABILITY",
  anm: "https://dadosabertos.anm.gov.br/SIGMINE/PROCESSOS_MINERARIOS/",
  deter: "https://terrabrasilis.dpi.inpe.br/downloads/",
  hansen: "https://storage.googleapis.com/earthengine-stac/catalog/UMD_hansen_global_forest_change_2023_v1.json",
  gfw: "https://data.globalforestwatch.org/",
};

export default function MethodologyPage() {
  return (
    <>
      <SiteNav active="methodology" />
      <main className="methodology-page">
        <section className="hero">
          <h1>Methodology</h1>
          <p>
            This page documents the full technical pipeline. The{" "}
            <Link href="/">dashboard</Link> uses plain language; this page is
            for reviewers, researchers, and hiring managers who want implementation
            detail.
          </p>
        </section>

        <section className="card methodology-block">
          <h2>Study area</h2>
          <p>
            <strong>Southern Pará (Novo Progresso corridor)</strong>: a ~115 × 95
            km pilot AOI along the BR-163 highway. The region has high INPE DETER
            alert density and documented pressure from illegal mining and forest
            clearing.
          </p>
          <ul className="method-list">
            <li>Before composite: 2019 annual Sentinel-2 median</li>
            <li>After composite: 2023 annual Sentinel-2 median</li>
            <li>BBox (W,S,E,N): -56.30, -7.90, -55.25, -7.05</li>
          </ul>
        </section>

        <section className="card methodology-block">
          <h2>1. Data acquisition</h2>
          <p>
            Imagery is pulled via the Google Earth Engine Python API from{" "}
            <a href={SOURCE_LINKS.s2} target="_blank" rel="noopener noreferrer">
              <code>COPERNICUS/S2_SR_HARMONIZED</code>
            </a>{" "}
            (Sentinel-2 L2A surface reflectance). Bands B2, B3, B4, B8 (10 m) and
            B11, B12 (20 m SWIR) support vegetation and bare-soil/mining
            discrimination.
          </p>
          <p>
            Cloud masking uses the Sentinel-2 Scene Classification Layer (SCL) on
            each scene before compositing. Annual <strong>median composites</strong>{" "}
            reduce residual cloud noise in this tropical AOI. This is a practical
            trade-off compared with picking two single low-cloud dates.
          </p>
        </section>

        <section className="card methodology-block">
          <h2>2. Preprocessing</h2>
          <ul className="method-list">
            <li>Cloud/shadow masking on each scene before compositing</li>
            <li>Reflectance normalization for model input</li>
            <li>
              Tiling large rasters into fixed-size patches (e.g. 256×256) with
              georeferencing metadata preserved for mapping results back to
              coordinates
            </li>
          </ul>
        </section>

        <section className="card methodology-block">
          <h2>3. Change detection (two approaches)</h2>
          <p>
            Two methods are implemented and compared: a spectral index baseline
            first, then a learned model.
          </p>

          <h3>Baseline: spectral index differencing (currently live on the map)</h3>
          <p>
            Compute NDVI for before and after composites. Flag pixels where
            vegetation index loss exceeds 0.18 and where pre-change NDVI was above
            0.55 (the pixel was vegetated). Vectorize at 30 m and keep patches ≥
            5 ha. Fast, interpretable, and commonly used operationally. Works well
            for forest clearing; weaker on bare-soil mining sites where vegetation
            indices underperform.
          </p>

          <h3>Learned model: Siamese / early-fusion U-Net (planned)</h3>
          <p>
            A convolutional model takes before/after patch pairs and outputs a
            binary change mask. Training labels come from{" "}
            <a href={SOURCE_LINKS.hansen} target="_blank" rel="noopener noreferrer">
              Hansen Global Forest Change
            </a>{" "}
            tree-cover loss (imperfect but usable at portfolio scale). Validation
            uses a <strong>spatial hold-out region</strong>, not random pixel
            splits. Spatial autocorrelation makes random splits misleadingly
            optimistic for geospatial data.
          </p>
          <p>
            Metrics reported for both approaches: IoU and F1, with discussion of
            where the learned model adds value over the index baseline.
          </p>
        </section>

        <section className="card methodology-block">
          <h2>4. Concession cross-referencing</h2>
          <p>
            This is the differentiating step. Change masks are converted to vector
            polygons (raster-to-vector), then spatially joined against{" "}
            <a href={SOURCE_LINKS.anm} target="_blank" rel="noopener noreferrer">
              ANM SIGMINE
            </a>{" "}
            mining permit polygons for Pará using geopandas.
          </p>

          <div className="status-table-wrap">
            <table className="status-table">
              <thead>
                <tr>
                  <th>Classification</th>
                  <th>Rule</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Likely permitted</td>
                  <td>
                    Centroid inside a valid, active concession polygon with
                    matching permit phase
                  </td>
                </tr>
                <tr>
                  <td>Likely unpermitted</td>
                  <td>
                    Centroid outside all concession boundaries in public records
                  </td>
                </tr>
                <tr>
                  <td>Likely exceeding permit</td>
                  <td>
                    Inside a concession but cleared area exceeds registered limit,
                    or change occurs outside the permit&apos;s active date range
                  </td>
                </tr>
                <tr>
                  <td>Unknown</td>
                  <td>
                    Incomplete registry overlap or ambiguous geometry (e.g.
                    garimpo without formal polygons)
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section className="card methodology-block">
          <h2>5. Validation</h2>
          <ul className="method-list">
            <li>
              Compare flagged sites against{" "}
              <a href={SOURCE_LINKS.deter} target="_blank" rel="noopener noreferrer">
                INPE DETER
              </a>{" "}
              near-real-time alerts and PRODES annual deforestation polygons
            </li>
            <li>
              Sanity-check total detected change area against Hansen aggregate
              statistics for the region
            </li>
            <li>
              Where available, cross-check against news-reported or enforcement
              cases in the study area
            </li>
          </ul>
        </section>

        <section className="card methodology-block">
          <h2>Data sources</h2>
          <div className="status-table-wrap">
            <table className="status-table">
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Source</th>
                  <th>Role</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Sentinel-2 L2A</td>
                  <td>
                    <a href={SOURCE_LINKS.s2} target="_blank" rel="noopener noreferrer">
                      Google Earth Engine
                    </a>
                  </td>
                  <td>Before/after imagery</td>
                </tr>
                <tr>
                  <td>Mining concessions</td>
                  <td>
                    <a href={SOURCE_LINKS.anm} target="_blank" rel="noopener noreferrer">
                      ANM SIGMINE
                    </a>{" "}
                    (primary),{" "}
                    <a href={SOURCE_LINKS.gfw} target="_blank" rel="noopener noreferrer">
                      GFW
                    </a>{" "}
                    (cross-check)
                  </td>
                  <td>Permit boundaries</td>
                </tr>
                <tr>
                  <td>Logging permits</td>
                  <td>IBAMA SINAFLOR / GFW</td>
                  <td>Permit boundaries</td>
                </tr>
                <tr>
                  <td>Tree cover loss</td>
                  <td>
                    <a href={SOURCE_LINKS.hansen} target="_blank" rel="noopener noreferrer">
                      Hansen GFC (UMD)
                    </a>
                  </td>
                  <td>Training / validation labels</td>
                </tr>
                <tr>
                  <td>Deforestation alerts</td>
                  <td>
                    <a href={SOURCE_LINKS.deter} target="_blank" rel="noopener noreferrer">
                      INPE DETER / PRODES
                    </a>
                  </td>
                  <td>Operational validation</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section className="card methodology-block">
          <h2>Tech stack</h2>
          <ul className="method-list inline-tags">
            <li>Python</li>
            <li>Earth Engine API</li>
            <li>PyTorch</li>
            <li>geopandas / rasterio / shapely</li>
            <li>Next.js + Leaflet (this dashboard)</li>
          </ul>
        </section>

        <div className="disclaimer">
          <strong>Important caveat:</strong> This is a heuristic flagging system
          based on public data completeness, not a legal determination. Concession
          registries are often outdated or incomplete. &quot;Outside a
          concession&quot; means not accounted for in available public records,
          not proven illegality. 10 m Sentinel-2 resolution misses small-scale
          clearings; cloud cover creates temporal gaps; garimpo sites frequently
          lack formal polygons. No field verification in v1.
        </div>

        <footer>
          <Link href="/">Back to dashboard</Link>
        </footer>
      </main>
    </>
  );
}
