import type {
  ParkClearingProperties,
  ParkProperties,
  PermitStatus,
} from "./types";

/** Plain-language labels for the dashboard legend */
export const STATUS_LABELS_PLAIN: Record<PermitStatus, string> = {
  likely_unpermitted: "No mining or logging permit found",
  likely_exceeding_permit: "May exceed permit limits",
  likely_permitted: "Matches a registered permit",
  unknown: "Needs review (unclear permit match)",
};

/** Short explanations shown on the dashboard */
export const STATUS_DESCRIPTIONS: Record<PermitStatus, string> = {
  likely_unpermitted:
    "Satellite data shows vegetation loss here, and the spot does not fall inside any mining (ANM SIGMINE) or logging (GFW) permit polygon we have for this area.",
  likely_exceeding_permit:
    "The clearing overlaps a registered mining or logging permit, but the cleared area or timing may go beyond what the permit allows.",
  likely_permitted:
    "The clearing overlaps an active mining or logging permit in public records. This is still not proof of full legal compliance.",
  unknown:
    "Vegetation loss was detected, but permit records are incomplete, outdated, or ambiguous for this location.",
};

export const DATA_SOURCES = {
  sentinel2: {
    name: "Sentinel-2 satellite imagery (ESA/Copernicus)",
    url: "https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED",
    role: "Used to compare forest cover between 2019 and 2023.",
  },
  anm_sigmine: {
    name: "ANM SIGMINE mining permits (Pará)",
    url: "https://dadosabertos.anm.gov.br/SIGMINE/PROCESSOS_MINERARIOS/",
    role: "Public mining permit boundaries used for cross-reference.",
  },
  gfw_logging: {
    name: "GFW managed forest (logging) concessions",
    url: "https://data.globalforestwatch.org/datasets/gfw::logging-concessions/about",
    role: "Logging permit boundaries compiled by Global Forest Watch.",
  },
  sinaflor: {
    name: "IBAMA SINAFLOR forest authorizations (optional local layer)",
    url: "https://www.gov.br/ibama/pt-br/assuntos/biodiversidade/flora-e-madeira/sistema-nacional-de-controle-da-origem-dos-produtos-florestais-sinaflor",
    role: "Official forest exploitation authorizations when manually added to the pipeline.",
  },
  inpe_deter: {
    name: "INPE DETER deforestation alerts",
    url: "https://terrabrasilis.dpi.inpe.br/downloads/",
    role: "Independent government alerts for validation.",
  },
  hansen: {
    name: "Hansen Global Forest Change",
    url: "https://storage.googleapis.com/earthengine-stac/catalog/UMD_hansen_global_forest_change_2023_v1.json",
    role: "Tree-cover loss from 2019 to 2023 used for the live clearing overlays.",
  },
  gfw: {
    name: "Global Forest Watch",
    url: "https://data.globalforestwatch.org/",
    role: "Aggregated concession and forest data.",
  },
  methodology: {
    name: "Full methodology",
    url: "/methodology",
    role: "Technical details on how detections are produced.",
  },
} as const;

export interface PopupFields {
  id?: string;
  name?: string;
  permit_status: PermitStatus;
  area_ha?: number;
  detected_year?: number;
  method?: string;
  notes?: string;
  matched_permit_type?: string;
}

export function buildSitePopup(props: PopupFields): string {
  const status = props.permit_status;
  const label = STATUS_LABELS_PLAIN[status];
  const description = STATUS_DESCRIPTIONS[status];
  const area =
    typeof props.area_ha === "number"
      ? `${props.area_ha.toFixed(1)} hectares`
      : "Area not available";
  const year = props.detected_year ?? "Unknown year";
  const method = props.method ?? "NDVI vegetation loss (Sentinel-2)";
  const notes = props.notes ?? "";
  const name = props.name ?? "Detected clearing";
  const permitMatch = props.matched_permit_type ?? "none";

  const sources = [
    DATA_SOURCES.sentinel2,
    DATA_SOURCES.anm_sigmine,
    DATA_SOURCES.gfw_logging,
    permitMatch.includes("logging") ? DATA_SOURCES.sinaflor : null,
    status === "likely_unpermitted" || status === "unknown"
      ? DATA_SOURCES.inpe_deter
      : null,
    DATA_SOURCES.methodology,
  ].filter(Boolean) as (typeof DATA_SOURCES)[keyof typeof DATA_SOURCES][];

  const sourceLinks = sources
    .map(
      (s) =>
        `<li><a href="${s.url}" target="_blank" rel="noopener noreferrer">${s.name}</a></li>`
    )
    .join("");

  return `
    <div class="site-popup">
      <strong class="site-popup-title">${name}</strong>
      <p class="site-popup-status"><span class="site-popup-tag">${label}</span></p>
      <p class="site-popup-text">${description}</p>
      <ul class="site-popup-facts">
        <li><strong>Cleared area:</strong> ${area}</li>
        <li><strong>Change detected around:</strong> ${year}</li>
        <li><strong>Detection method:</strong> ${method}</li>
        <li><strong>Permit match:</strong> ${permitMatch}</li>
      </ul>
      ${notes ? `<p class="site-popup-notes"><strong>Notes:</strong> ${notes}</p>` : ""}
      <p class="site-popup-sources-title"><strong>Where this comes from</strong></p>
      <ul class="site-popup-sources">${sourceLinks}</ul>
      <p class="site-popup-fine-print">Flags use public satellite imagery plus mining and logging permit databases. They are not proof of a crime or a final legal finding.</p>
    </div>
  `;
}

export function buildParkClearingPopup(props: ParkClearingProperties): string {
  const area =
    typeof props.area_ha === "number"
      ? `${props.area_ha.toFixed(1)} hectares`
      : "Area not available";
  const year = props.detected_year ?? "Unknown year";
  const name = props.name ?? "Detected clearing";
  const location =
    props.boundary_clipped === false
      ? `Near ${props.park_name} (park boundary not applied)`
      : `Inside ${props.park_name}`;

  return `
    <div class="site-popup">
      <strong class="site-popup-title">${name}</strong>
      <p class="site-popup-status"><span class="site-popup-tag">Clearing in a protected park</span></p>
      <p class="site-popup-text">Satellite data shows tree-cover loss here. Mining and logging are generally prohibited inside this protected area. Loss can also come from fire, insects, or other disturbance, so this is a starting point, not a finding.</p>
      <ul class="site-popup-facts">
        <li><strong>Location:</strong> ${location}</li>
        <li><strong>Cleared area:</strong> ${area}</li>
        <li><strong>Change detected around:</strong> ${year}</li>
        <li><strong>Detection method:</strong> Hansen tree-cover loss, 2019 to 2023</li>
      </ul>
      <p class="site-popup-fine-print">Detected clearings are automated hints from satellite imagery. They are not proof of illegal activity and have not been verified on the ground.</p>
    </div>
  `;
}

export function buildParkPopup(props: ParkProperties): string {
  return `
    <div class="site-popup">
      <strong class="site-popup-title">${props.name}</strong>
      <p class="site-popup-status"><span class="site-popup-tag">${props.threat_label}</span></p>
      <p class="site-popup-text">${props.description}</p>
      <ul class="site-popup-facts">
        <li><strong>Location:</strong> ${props.state}</li>
      </ul>
      <p class="site-popup-sources-title"><strong>Where this comes from</strong></p>
      <ul class="site-popup-sources">
        <li><a href="${props.source_url}" target="_blank" rel="noopener noreferrer">National Park Service park page</a></li>
      </ul>
      <p class="site-popup-fine-print">These are protected areas with documented illegal mining or logging pressure, shown here for context. This reference layer is separate from the satellite analysis of the Amazon study area.</p>
    </div>
  `;
}
