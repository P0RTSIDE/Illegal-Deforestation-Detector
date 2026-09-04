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
  gfw_logging: "https://data.globalforestwatch.org/datasets/gfw::logging-concessions/about",
  sinaflor:
    "https://www.gov.br/ibama/pt-br/assuntos/biodiversidade/flora-e-madeira/sistema-nacional-de-controle-da-origem-dos-produtos-florestais-sinaflor",
};

export default function MethodologyPage() {
  return (
    <>
      <SiteNav active="methodology" />
      <main className="methodology-page">
        <section className="hero">
          <h1>Methodology</h1>
          <p>
            This page documents the full technical pipeline behind the flagged
            sites, from satellite imagery to permit cross-referencing. For a
            quick overview of the results, see the{" "}
            <Link href="/">dashboard</Link>.
          </p>
        </section>

        <section className="card methodology-block">
          <h2>Study area</h2>
          <p>
            <strong>Southern Pará (Novo Progresso corridor)</strong>: a ~265 by
            245 km study area along the BR-163 highway. The region has high INPE
            DETER alert density and documented pressure from illegal mining and
            forest clearing.
          </p>
          <ul className="method-list">
            <li>Before composite: 2019 annual Sentinel-2 median</li>
            <li>After composite: 2023 annual Sentinel-2 median</li>
            <li>BBox (W,S,E,N): -57.00, -8.60, -54.60, -6.40</li>
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
            <li>
              Clouds and their shadows are removed from each image before the
              yearly composite is built, so passing weather is not mistaken for
              change on the ground.
            </li>
            <li>
              Pixel brightness values are rescaled to a common range so the two
              years can be compared on equal footing.
            </li>
            <li>
              Each large image is cut into fixed-size tiles (for example, 256 by
              256 pixels). Every tile keeps its map coordinates, so any change
              found in a tile can be traced back to a real location on the map.
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
            Two live paths can produce the change polygons. The preferred path
            compares NDVI and NBR on Sentinel-2 before and after composites
            through Earth Engine. A pixel is flagged if it was vegetated (NDVI
            above 0.40) and then lost enough canopy that NDVI dropped by more
            than 0.12 or NBR dropped by more than 0.10. Small holes inside those
            patches are filled so a visible clearing stays one shape.
            When Earth Engine is not available, the map uses{" "}
            <a href={SOURCE_LINKS.hansen} target="_blank" rel="noopener noreferrer">
              Hansen Global Forest Change
            </a>{" "}
            tree-cover loss for 2019 to 2023 at 30 m. That product maps complete
            stand-replacement clearings, so large blocks that a capped NDVI
            sample can miss still appear. In Brazil, patches smaller than 2
            hectares are dropped. Inside US parks the floor is 0.5 hectares.
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
            polygons (raster-to-vector), then spatially joined against public
            permit layers using geopandas:
          </p>
          <ul className="method-list">
            <li>
              <strong>Mining:</strong>{" "}
              <a href={SOURCE_LINKS.anm} target="_blank" rel="noopener noreferrer">
                ANM SIGMINE
              </a>{" "}
              mineral process polygons for Pará (daily-updated open data)
            </li>
            <li>
              <strong>Logging:</strong>{" "}
              <a
                href={SOURCE_LINKS.gfw_logging}
                target="_blank"
                rel="noopener noreferrer"
              >
                GFW managed forest concessions
              </a>{" "}
              clipped to the study bbox via ArcGIS REST, plus optional local
              SINAFLOR shapefiles dropped in{" "}
              <code>data/raw/concessions/logging/sinaflor/</code>
            </li>
          </ul>
          <p>
            Each clearing centroid is checked against mining first, then logging.
            The output includes <code>matched_permit_type</code> (mining, logging,
            both, or none).
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
                    Centroid outside all mining and logging permit boundaries in
                    public records for this study area
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
          <h2>5. US protected parks</h2>
          <p>
            The same Sentinel-2 change method is also run over a small set of US
            national parks and preserves with documented illegal mining or
            logging pressure. Detections are clipped to National Park Service
            boundary polygons. These parks are not in Brazilian permit
            registries, so the map treats vegetation loss inside a protected
            boundary as the signal, not a permit match.
          </p>
        </section>

        <section className="card methodology-block">
          <h2>6. Validation</h2>
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
                  <td>
                    <a
                      href={SOURCE_LINKS.gfw_logging}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      GFW managed forest concessions
                    </a>{" "}
                    (primary for this pipeline), optional{" "}
                    <a
                      href={SOURCE_LINKS.sinaflor}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      IBAMA SINAFLOR
                    </a>{" "}
                    shapefiles
                  </td>
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
