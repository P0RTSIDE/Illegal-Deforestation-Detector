export type PermitStatus =
  | "likely_unpermitted"
  | "likely_permitted"
  | "likely_exceeding_permit"
  | "unknown";

export interface FlaggedSiteProperties {
  id: string;
  name: string;
  permit_status: PermitStatus;
  area_ha: number;
  detected_year: number;
  method: string;
  notes: string;
  matched_permit_type?: string;
}

export interface SummaryData {
  study_area: string;
  bbox: [number, number, number, number];
  before_year: number;
  after_year: number;
  before_image_count: number;
  after_image_count: number;
  total_flagged_sites: number;
  total_flagged_area_ha: number;
  by_status: Record<PermitStatus, number>;
  data_mode: "demo" | "live";
  method?: string;
  last_updated: string;
}

export const STATUS_COLORS: Record<PermitStatus, string> = {
  likely_unpermitted: "#ef4444",
  likely_exceeding_permit: "#f59e0b",
  likely_permitted: "#22c55e",
  unknown: "#64748b",
};

export const STATUS_LABELS: Record<PermitStatus, string> = {
  likely_unpermitted: "Likely unpermitted (outside concessions)",
  likely_exceeding_permit: "Likely exceeding permit",
  likely_permitted: "Likely permitted",
  unknown: "Unknown / incomplete registry",
};

export type ParkThreat = "mining" | "logging";

export interface ParkProperties {
  name: string;
  state: string;
  threat: ParkThreat;
  threat_label: string;
  description: string;
  source_url: string;
}

export const PARK_THREAT_COLORS: Record<ParkThreat, string> = {
  mining: "#f59e0b",
  logging: "#a855f7",
};

export interface ParkClearingProperties {
  id?: string;
  name?: string;
  park_name: string;
  park_unit: string;
  threat: ParkThreat;
  area_ha?: number;
  detected_year?: number;
  boundary_clipped?: boolean;
}
