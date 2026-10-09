import { useEffect, useRef } from "react";

import type { CampusMapConfig } from "../types/api";
import { loadBaiduMapSdk } from "../utils/baiduMap";
import type { PickedPoint } from "./PointPicker";

interface BaiduPointPickerProps {
  campus: CampusMapConfig;
  value: PickedPoint;
  onChange?: (value: PickedPoint) => void;
  readOnly?: boolean;
  height?: number;
}

/** 百度地图点位选择器：点击地图返回经纬度。 */
export default function BaiduPointPicker({
  campus,
  value,
  onChange,
  readOnly = false,
  height = 320,
}: BaiduPointPickerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<any>(null);
  const markerRef = useRef<any>(null);
  const onChangeRef = useRef(onChange);
  const readyRef = useRef(false);

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    let disposed = false;

    const ak = campus.baidu_map_ak;
    if (!ak) {
      return;
    }

    loadBaiduMapSdk(campus.tile_url_template, ak)
      .then(() => {
        if (disposed || !window.BMapGL) {
          return;
        }
        const BMapGL = window.BMapGL;
        const map = new BMapGL.Map(container);
        map.centerAndZoom(
          new BMapGL.Point(campus.default_longitude ?? 0, campus.default_latitude ?? 0),
          Math.round(campus.default_zoom) || 15,
        );
        map.enableScrollWheelZoom(true);
        mapRef.current = map;
        readyRef.current = true;

        if (!readOnly) {
          map.addEventListener("click", (event: any) => {
            const handler = onChangeRef.current;
            const latlng = event?.latlng;
            if (!handler || !latlng) {
              return;
            }
            handler({
              map_x: null,
              map_y: null,
              latitude: latlng.lat,
              longitude: latlng.lng,
            });
          });
        }
      })
      .catch(() => {
        // 加载失败时由上层页面给出提示（地图页会显示错误信息）
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
      markerRef.current = null;
      readyRef.current = false;
    };
  }, [campus, readOnly]);

  // 更新选中的点位标记
  useEffect(() => {
    const map = mapRef.current;
    const BMapGL = window.BMapGL;
    if (!map || !readyRef.current || !BMapGL) {
      return;
    }

    if (markerRef.current) {
      map.removeOverlay(markerRef.current);
      markerRef.current = null;
    }
    if (value.latitude === null || value.longitude === null) {
      return;
    }

    const svg =
      '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24">' +
      '<circle cx="12" cy="12" r="10" fill="#1f8a4c" stroke="#ffffff" stroke-width="2"/></svg>';
    const icon = new BMapGL.Icon(
      `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`,
      new BMapGL.Size(24, 24),
      { anchor: new BMapGL.Size(12, 12) },
    );
    const marker = new BMapGL.Marker(new BMapGL.Point(value.longitude, value.latitude), { icon });
    markerRef.current = marker;
    map.addOverlay(marker);
  }, [value]);

  return <div className="point-picker" ref={containerRef} style={{ height }} />;
}
