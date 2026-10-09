import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import type { CampusMapConfig, ShopPoint, ShopTypeFilter } from "../types/api";
import { imageBounds, normalizedToLeaflet } from "../utils/mapCoordinates";

interface FoodMapProps {
  campus: CampusMapConfig;
  points: ShopPoint[];
  shopTypeFilter: ShopTypeFilter;
  selectedPointId: number | null;
  resetSignal: number;
  onSelectPoint: (point: ShopPoint) => void;
  onMapError: (message: string) => void;
  renderOverlay?: (
    point: { x: number; y: number; width: number; height: number } | null,
  ) => ReactNode;
}

const SHOP_COLORS: Record<string, string> = {
  shop: "#1f8a4c",
  vendor: "#f2994a",
};

export default function FoodMap({
  campus,
  points,
  shopTypeFilter,
  selectedPointId,
  resetSignal,
  onSelectPoint,
  onMapError,
  renderOverlay,
}: FoodMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerLayerRef = useRef<L.LayerGroup | null>(null);
  const pointLatLngsRef = useRef<Map<number, [number, number]>>(new Map());
  const [overlayPoint, setOverlayPoint] = useState<{
    x: number;
    y: number;
    width: number;
    height: number;
  } | null>(null);

  const selectRef = useRef(onSelectPoint);
  const errorRef = useRef(onMapError);

  useEffect(() => {
    selectRef.current = onSelectPoint;
    errorRef.current = onMapError;
  }, [onSelectPoint, onMapError]);

  /** 计算选中点位在容器内的像素坐标；卡片据此锚定在点位附近。 */
  const updateOverlayPoint = useCallback(() => {
    const map = mapRef.current;
    if (!map || selectedPointId === null) {
      setOverlayPoint(null);
      return;
    }
    const latlng = pointLatLngsRef.current.get(selectedPointId);
    if (!latlng) {
      setOverlayPoint(null);
      return;
    }
    const size = map.getSize();
    const containerPoint = map.latLngToContainerPoint(L.latLng(latlng[0], latlng[1]));
    setOverlayPoint({
      x: containerPoint.x,
      y: containerPoint.y,
      width: size.x,
      height: size.y,
    });
  }, [selectedPointId]);

  // 初始化地图：校园或底图类型变化时重建。
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
            attributionControl: true,
          })
        : L.map(container, {
            center: [campus.default_latitude ?? 0, campus.default_longitude ?? 0],
            zoom: campus.default_zoom,
            minZoom: 3,
            maxZoom: 19,
            attributionControl: true,
          });

    mapRef.current = map;

    if (campus.map_type === "image") {
      const bounds = imageBounds(geometry);
      if (campus.map_asset_url) {
        const overlay = L.imageOverlay(campus.map_asset_url, bounds).addTo(map);
        overlay.on("error", () => errorRef.current("底图加载失败，请检查底图文件是否存在。"));
      } else {
        errorRef.current("当前校园还没有配置图片底图。");
      }
      map.setMaxBounds(bounds);
      map.fitBounds(bounds);
    } else if (campus.tile_url_template) {
      L.tileLayer(campus.tile_url_template, {
        attribution: campus.map_attribution ?? "",
        maxZoom: 19,
      }).addTo(map);
    } else {
      errorRef.current("当前校园还没有配置真实地图瓦片源。");
    }

    if (campus.map_attribution && campus.map_type === "image") {
      map.attributionControl.addAttribution(campus.map_attribution);
    }

    markerLayerRef.current = L.layerGroup().addTo(map);
    // 说明：点击地图空白区域不关闭详情卡片，关闭只能通过卡片右上角的 ×
    // 或再次点击同一个美食点触发（对应开发文档 5.2）。

    return () => {
      map.remove();
      mapRef.current = null;
      markerLayerRef.current = null;
      pointLatLngsRef.current.clear();
    };
  }, [campus]);

  // 地图拖动、缩放或容器变化时重新计算卡片锚点，保证卡片始终指向点位。
  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }
    const handler = () => updateOverlayPoint();
    map.on("move", handler);
    map.on("zoom", handler);
    map.on("zoomend", handler);
    map.on("moveend", handler);
    map.on("resize", handler);
    return () => {
      map.off("move", handler);
      map.off("zoom", handler);
      map.off("zoomend", handler);
      map.off("moveend", handler);
      map.off("resize", handler);
    };
  }, [campus, updateOverlayPoint]);

  // 点位渲染：按店铺类型筛选，图片模式使用归一化坐标换算。
  useEffect(() => {
    const layer = markerLayerRef.current;
    if (!layer) {
      return;
    }

    layer.clearLayers();
    pointLatLngsRef.current.clear();
    const geometry = {
      width: campus.image_width ?? 1,
      height: campus.image_height ?? 1,
    };

    for (const point of points) {
      if (shopTypeFilter !== "all" && point.shop_type !== shopTypeFilter) {
        continue;
      }

      let latlng: [number, number];
      if (campus.map_type === "image") {
        if (point.map_x === undefined || point.map_y === undefined) {
          continue;
        }
        const { x, y } = normalizedToLeaflet(point.map_x, point.map_y, geometry);
        latlng = [y, x];
      } else {
        if (point.latitude === undefined || point.longitude === undefined) {
          continue;
        }
        latlng = [point.latitude, point.longitude];
      }

      pointLatLngsRef.current.set(point.id, latlng);
      const selected = selectedPointId === point.id;
      const marker = L.circleMarker(latlng, {
        radius: selected ? 12 : 9,
        color: selected ? "#1f2329" : "#ffffff",
        weight: selected ? 3 : 2,
        fillColor: SHOP_COLORS[point.shop_type] ?? "#1f8a4c",
        fillOpacity: 1,
      });
      marker.bindTooltip(`${point.name}（${point.shop_type === "vendor" ? "摊贩" : "商铺"}）`);
      marker.on("click", (event) => {
        if (event.originalEvent) {
          L.DomEvent.stopPropagation(event.originalEvent);
        }
        selectRef.current(point);
      });
      marker.addTo(layer);
    }

    updateOverlayPoint();
  }, [campus, points, shopTypeFilter, selectedPointId, updateOverlayPoint]);

  // 重置视图。
  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }
    if (campus.map_type === "image") {
      map.fitBounds(
        imageBounds({
          width: campus.image_width ?? 1,
          height: campus.image_height ?? 1,
        }),
      );
    } else {
      map.setView(
        [campus.default_latitude ?? 0, campus.default_longitude ?? 0],
        campus.default_zoom,
      );
    }
  }, [resetSignal, campus]);

  return (
    <div className="map-stage">
      <div className="food-map" ref={containerRef} />
      {renderOverlay ? renderOverlay(overlayPoint) : null}
    </div>
  );
}
