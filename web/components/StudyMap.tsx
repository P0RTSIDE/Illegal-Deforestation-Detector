"use client";

import { useEffect, useMemo } from "react";
import {
  MapContainer,
  TileLayer,
  GeoJSON,
  LayersControl,
  useMap,
} from "react-leaflet";
import type { FeatureCollection, Point } from "geojson";
import L from "leaflet";
import {
  STATUS_COLORS,
  PARK_THREAT_COLORS,
  type FlaggedSiteProperties,
  type ParkProperties,
} from "@/lib/types";
import { buildSitePopup, buildParkPopup } from "@/lib/copy";

import "leaflet/dist/leaflet.css";

export type MapRegion = "brazil" | "usa";

interface MapProps {
  studyArea: FeatureCollection;
  flaggedSites: FeatureCollection;
  usParks: FeatureCollection;
  center: [number, number];
  bbox: [number, number, number, number];
  region: MapRegion;
}

function styleFeature(status: FlaggedSiteProperties["permit_status"]) {
  return {
    color: STATUS_COLORS[status],
    weight: 2.5,
    fillColor: STATUS_COLORS[status],
    fillOpacity: 0.45,
  };
}

function RegionView({
  region,
  bbox,
  usBounds,
}: {
  region: MapRegion;
  bbox: [number, number, number, number];
  usBounds: L.LatLngBounds | null;
}) {
  const map = useMap();
  const [west, south, east, north] = bbox;

  useEffect(() => {
    if (region === "brazil") {
      map.flyToBounds(L.latLngBounds([south, west], [north, east]), {
        padding: [20, 20],
        maxZoom: 10,
      });
    } else if (usBounds) {
      map.flyToBounds(usBounds, { padding: [40, 40], maxZoom: 6 });
    }
  }, [region, map, west, south, east, north, usBounds]);

  return null;
}

export default function StudyMap({
  studyArea,
  flaggedSites,
  usParks,
  center,
  bbox,
  region,
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

  const usBounds = useMemo(() => {
    const latLngs = usParks.features
      .filter((f) => f.geometry?.type === "Point")
      .map((f) => {
        const [lng, lat] = (f.geometry as Point).coordinates;
        return [lat, lng] as [number, number];
      });
    return latLngs.length ? L.latLngBounds(latLngs) : null;
  }, [usParks]);

  return (
    <MapContainer
      center={center}
      zoom={7}
      scrollWheelZoom
      worldCopyJump
      className="map-wrap"
      style={{ height: "100%", width: "100%" }}
    >
      <RegionView region={region} bbox={bbox} usBounds={usBounds} />
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

        <LayersControl.Overlay checked name="Amazon flagged clearings">
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
        </LayersControl.Overlay>

        <LayersControl.Overlay checked name="US protected parks (mining/logging)">
          <GeoJSON
            data={usParks}
            pointToLayer={(feature, latlng) => {
              const props = feature.properties as ParkProperties;
              const color = PARK_THREAT_COLORS[props.threat] ?? "#e2e8f0";
              return L.circleMarker(latlng, {
                radius: 8,
                color: "#0b1220",
                weight: 1.5,
                fillColor: color,
                fillOpacity: 0.9,
              });
            }}
            onEachFeature={(feature, layer) => {
              const props = feature.properties as ParkProperties;
              layer.bindPopup(buildParkPopup(props), { maxWidth: 320 });
            }}
          />
        </LayersControl.Overlay>
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
    </MapContainer>
  );
}
