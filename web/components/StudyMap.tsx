"use client";

import { useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  GeoJSON,
  LayersControl,
  useMap,
} from "react-leaflet";
import type { FeatureCollection } from "geojson";
import L from "leaflet";
import { STATUS_COLORS, type FlaggedSiteProperties } from "@/lib/types";
import { buildSitePopup } from "@/lib/copy";

import "leaflet/dist/leaflet.css";

interface MapProps {
  studyArea: FeatureCollection;
  flaggedSites: FeatureCollection;
  center: [number, number];
  bbox: [number, number, number, number];
}

function styleFeature(status: FlaggedSiteProperties["permit_status"]) {
  return {
    color: STATUS_COLORS[status],
    weight: 2.5,
    fillColor: STATUS_COLORS[status],
    fillOpacity: 0.45,
  };
}

function FitStudyBounds({
  bbox,
}: {
  bbox: [number, number, number, number];
}) {
  const map = useMap();
  const [west, south, east, north] = bbox;

  useEffect(() => {
    map.fitBounds(
      L.latLngBounds([south, west], [north, east]),
      { padding: [20, 20], maxZoom: 11 }
    );
  }, [map, west, south, east, north]);

  return null;
}

export default function StudyMap({
  studyArea,
  flaggedSites,
  center,
  bbox,
}: MapProps) {
  useEffect(() => {
    delete (L.Icon.Default.prototype as unknown as { _getIconUrl?: unknown })
      ._getIconUrl;
    L.Icon.Default.mergeOptions({
      iconRetinaUrl:
        "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
      iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
      shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
    });
  }, []);

  return (
    <MapContainer
      center={center}
      zoom={9}
      scrollWheelZoom
      className="map-wrap"
      style={{ height: "100%", width: "100%" }}
    >
      <FitStudyBounds bbox={bbox} />
      <LayersControl position="topright">
        <LayersControl.BaseLayer checked name="Satellite imagery">
          <TileLayer
            attribution="Tiles &copy; Esri"
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          />
        </LayersControl.BaseLayer>
        <LayersControl.BaseLayer name="Street map">
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
        </LayersControl.BaseLayer>
      </LayersControl>

      <GeoJSON
        data={studyArea}
        style={{
          color: "#38bdf8",
          weight: 2,
          fillOpacity: 0.04,
          fillColor: "#38bdf8",
          dashArray: "6 4",
        }}
      />

      <GeoJSON
        data={flaggedSites}
        style={(feature) =>
          styleFeature(
            (feature?.properties as FlaggedSiteProperties).permit_status
          )
        }
        onEachFeature={(feature, layer) => {
          const props = feature.properties as FlaggedSiteProperties;
          layer.bindPopup(buildSitePopup(props), { maxWidth: 320 });
        }}
      />
    </MapContainer>
  );
}
