import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import type { CampusMapConfig } from "../types/api";
import { imageBounds, normalizedToLeaflet } from "../utils/mapCoordinates";

export interface PickedPoint {
  map_x: number | null;
  map_y: number | null;
  latitude: number | null;
  longitude: number | null;
}

export const EMPTY_POINT: PickedPoint = {
  map_x: null,
  map_y: null,
  latitude: null,
  longitude: null,
};

interface PointPickerProps {
  campus: CampusMapConfig;
  value: PickedPoint;
  onChange?: (value: PickedPoint) => void;
  readOnly?: boolean;
  height?: number;
}

/** 地图点位选择器：图片底图返回归一化坐标，真实地图返回经纬度。 */
export default function PointPicker({
  campus,
  value,
  onChange,
  readOnly = false,
  height = 320,
}: PointPickerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.CircleMarker | null>(null);
  const onChangeRef = useRef(onChange);

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const geometry = {
      width: campus.image_width ?? 1,
      height: campus.image_height ?? 1,
    };

    const map =
      campus.map_type === "image"
        ? L.map(container, {
            crs: L.CRS.Simple,
            minZoom: -3,
            maxZoom: 4,
            zoomSnap: 0.25,
          })
        : L.map(container, {
            center: [campus.default_latitude ?? 0, campus.default_longitude ?? 0],
            zoom: campus.default_zoom,
            minZoom: 3,
            maxZoom: 19,
          });

    if (campus.map_type === "image") {
      const bounds = imageBounds(geometry);
      if (campus.map_asset_url) {
        L.imageOverlay(campus.map_asset_url, bounds).addTo(map);
      }
      map.setMaxBounds(bounds);
      map.fitBounds(bounds);
    } else if (campus.tile_url_template) {
      L.tileLayer(campus.tile_url_template, {
        attribution: campus.map_attribution ?? "",
        maxZoom: 19,
      }).addTo(map);
    }

    mapRef.current = map;
    markerRef.current = null;

    if (!readOnly) {
      map.on("click", (event: L.LeafletMouseEvent) => {
        const handler = onChangeRef.current;
        if (!handler) {
          return;
        }
        if (campus.map_type === "image") {
          handler({
            map_x: event.latlng.lng / geometry.width,
            map_y: -event.latlng.lat / geometry.height,
            latitude: null,
            longitude: null,
          });
        } else {
          handler({
            map_x: null,
            map_y: null,
            latitude: event.latlng.lat,
            longitude: event.latlng.lng,
          });
        }
      });
    }

    return () => {
      map.remove();
      mapRef.current = null;
      markerRef.current = null;
    };
  }, [campus, readOnly]);

  // 更新标记位置：只有已选择点位时才显示标记
  useEffect(() => {
    const map = mapRef.current;
    const marker = markerRef.current;
    if (!map) {
      return;
    }
    const geometry = {
      width: campus.image_width ?? 1,
      height: campus.image_height ?? 1,
    };

    let latlng: [number, number] | null = null;
    if (campus.map_type === "image") {
      if (value.map_x !== null && value.map_y !== null) {
        const point = normalizedToLeaflet(value.map_x, value.map_y, geometry);
        latlng = [point.y, point.x];
      }
    } else if (value.latitude !== null && value.longitude !== null) {
      latlng = [value.latitude, value.longitude];
    }

    if (latlng === null) {
      if (marker) {
        map.removeLayer(marker);
        markerRef.current = null;
      }
      return;
    }

    if (marker) {
      marker.setLatLng(latlng);
    } else {
      markerRef.current = L.circleMarker(latlng, {
        radius: 10,
        color: "#ffffff",
        weight: 2,
        fillColor: "#1f8a4c",
        fillOpacity: 1,
      }).addTo(map);
    }
  }, [campus, value]);

  return <div className="point-picker" ref={containerRef} style={{ height }} />;
}
