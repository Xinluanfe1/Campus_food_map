import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

import type { CampusMapConfig, ShopPoint, ShopTypeFilter } from "../types/api";
import { loadBaiduMapSdk } from "../utils/baiduMap";

interface BaiduFoodMapProps {
  campus: CampusMapConfig;
  points: ShopPoint[];
  shopTypeFilter: ShopTypeFilter;
  selectedPointId: number | null;
  resetSignal: number;
  focusTarget?: { id: number; token: number } | null;
  onSelectPoint: (point: ShopPoint) => void;
  onMapError: (message: string) => void;
  renderOverlay?: (
    point: { x: number; y: number; width: number; height: number } | null,
  ) => ReactNode;
}

const MARKER_COLORS: Record<string, string> = {
  shop: "#1f8a4c",
  vendor: "#f2994a",
};

export default function BaiduFoodMap({
  campus,
  points,
  shopTypeFilter,
  selectedPointId,
  resetSignal,
  focusTarget,
  onSelectPoint,
  onMapError,
  renderOverlay,
}: BaiduFoodMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<any>(null);
  const pointRef = useRef<Map<number, any>>(new Map());
  const updateOverlayRef = useRef<(() => void) | null>(null);
  const selectRef = useRef(onSelectPoint);
  const errorRef = useRef(onMapError);
  const [ready, setReady] = useState(false);
  const [overlayPoint, setOverlayPoint] = useState<{
    x: number;
    y: number;
    width: number;
    height: number;
  } | null>(null);

  useEffect(() => {
    selectRef.current = onSelectPoint;
    errorRef.current = onMapError;
  }, [onMapError, onSelectPoint]);

  const updateOverlayPoint = useCallback(() => {
    const map = mapRef.current;
    if (!map || selectedPointId === null) {
      setOverlayPoint(null);
      return;
    }
    const position = pointRef.current.get(selectedPointId);
    if (!position) {
      setOverlayPoint(null);
      return;
    }
    const pixel =
      typeof map.pointToOverlayPixel === "function"
        ? map.pointToOverlayPixel(position)
        : map.pointToPixel(position);
    const size =
      typeof map.getSize === "function"
        ? map.getSize()
        : { width: containerRef.current?.clientWidth ?? 0, height: containerRef.current?.clientHeight ?? 0 };
    setOverlayPoint({ x: pixel.x, y: pixel.y, width: size.width, height: size.height });
  }, [selectedPointId]);

  updateOverlayRef.current = updateOverlayPoint;

  // 初始化百度地图（校园或提供方变化时重建）
  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    let disposed = false;

    const ak = campus.baidu_map_ak;
    if (!ak) {
      errorRef.current("当前校园使用百度地图，但部署环境未配置 BAIDU_MAP_AK。");
      return;
    }

    loadBaiduMapSdk(campus.tile_url_template, ak)
      .then(() => {
        if (disposed || !window.BMapGL) {
          return;
        }
        const BMapGL = window.BMapGL;
        const map = new BMapGL.Map(container);
        const center = new BMapGL.Point(
          campus.default_longitude ?? 0,
          campus.default_latitude ?? 0,
        );
        map.centerAndZoom(center, Math.round(campus.default_zoom) || 15);
        map.enableScrollWheelZoom(true);
        mapRef.current = map;

        const handler = () => updateOverlayRef.current?.();
        map.addEventListener("moving", handler);
        map.addEventListener("moveend", handler);
        map.addEventListener("zoomend", handler);
        map.addEventListener("resize", handler);
        // 点击地图空白区域不关闭详情卡片（与开发文档 5.2 一致）
        map.addEventListener("click", () => undefined);

        setReady(true);
      })
      .catch((error: unknown) => {
        if (!disposed) {
          errorRef.current(error instanceof Error ? error.message : "百度地图加载失败。");
        }
      });

    return () => {
      disposed = true;
      const map = mapRef.current;
      if (map) {
        try {
          map.clearOverlays();
        } catch {
          // 忽略清理异常
        }
      }
      mapRef.current = null;
      pointRef.current.clear();
      setReady(false);
      setOverlayPoint(null);
    };
  }, [campus]);

  // 渲染店铺点位
  useEffect(() => {
    const map = mapRef.current;
    const BMapGL = window.BMapGL;
    if (!map || !ready || !BMapGL) {
      return;
    }

    map.clearOverlays();
    pointRef.current.clear();

    for (const point of points) {
      if (shopTypeFilter !== "all" && point.shop_type !== shopTypeFilter) {
        continue;
      }
      if (point.latitude === undefined || point.longitude === undefined) {
        continue;
      }

      const selected = selectedPointId === point.id;
      const size = selected ? 26 : 22;
      const color = MARKER_COLORS[point.shop_type] ?? "#1f8a4c";
      const svg =
        `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}">` +
        `<circle cx="${size / 2}" cy="${size / 2}" r="${size / 2 - 2}" fill="${color}" ` +
        `stroke="#ffffff" stroke-width="2"/></svg>`;
      const icon = new BMapGL.Icon(
        `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`,
        new BMapGL.Size(size, size),
        { anchor: new BMapGL.Size(size / 2, size / 2) },
      );

      const position = new BMapGL.Point(point.longitude, point.latitude);
      pointRef.current.set(point.id, position);
      const marker = new BMapGL.Marker(position, { icon });
      marker.setTitle(`${point.name}（${point.shop_type === "vendor" ? "摊贩" : "商铺"}）`);
      marker.addEventListener("click", () => selectRef.current(point));
      map.addOverlay(marker);
    }

    updateOverlayPoint();
  }, [points, ready, selectedPointId, shopTypeFilter, updateOverlayPoint]);

  // 重置视图
  useEffect(() => {
    const map = mapRef.current;
    const BMapGL = window.BMapGL;
    if (!map || !ready || !BMapGL) {
      return;
    }
    map.centerAndZoom(
      new BMapGL.Point(campus.default_longitude ?? 0, campus.default_latitude ?? 0),
      Math.round(campus.default_zoom) || 15,
    );
  }, [campus, ready, resetSignal]);

  // 从排行榜或搜索结果定位到指定点位
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !focusTarget) {
      return;
    }
    const position = pointRef.current.get(focusTarget.id);
    if (position) {
      map.panTo(position);
    }
  }, [focusTarget, points]);

  return (
    <div className="map-stage">
      <div className="food-map" ref={containerRef} />
      {renderOverlay ? renderOverlay(overlayPoint) : null}
    </div>
  );
}
