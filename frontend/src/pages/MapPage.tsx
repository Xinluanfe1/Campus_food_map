import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { fetchCampusMap, fetchCampuses, fetchShopPoints } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import AdminMapPanel from "../components/AdminMapPanel";
import FoodMap from "../components/FoodMap";
import { useHealthStatus } from "../hooks/useHealthStatus";
import type { CampusMapConfig, CampusSummary, ShopPoint, ShopTypeFilter } from "../types/api";

export default function MapPage() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const campusId = searchParams.get("campus") ?? "";

  const [campusList, setCampusList] = useState<CampusSummary[]>([]);
  const [campus, setCampus] = useState<CampusMapConfig | null>(null);
  const [points, setPoints] = useState<ShopPoint[]>([]);
  const [shopTypeFilter, setShopTypeFilter] = useState<ShopTypeFilter>("all");
  const [selectedPoint, setSelectedPoint] = useState<ShopPoint | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [resetSignal, setResetSignal] = useState(0);
  const [reloadToken, setReloadToken] = useState(0);
  const [showAdminPanel, setShowAdminPanel] = useState(false);
  const health = useHealthStatus();

  // 1. 读取校园列表，未指定校园时默认使用第一个可公开访问的校园。
  useEffect(() => {
    let cancelled = false;
    fetchCampuses()
      .then((response) => {
        if (cancelled) {
          return;
        }
        setCampusList(response.data.items);
        if (!campusId && response.data.items.length > 0) {
          setSearchParams({ campus: response.data.items[0].campus_id }, { replace: true });
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : "校园列表加载失败。");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [campusId, setSearchParams]);

  // 2. 读取当前校园的地图配置与公开点位。
  useEffect(() => {
    if (!campusId) {
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError("");

    Promise.all([fetchCampusMap(campusId), fetchShopPoints(campusId)])
      .then(([campusResponse, pointsResponse]) => {
        if (cancelled) {
          return;
        }
        setCampus(campusResponse.data);
        setPoints(pointsResponse.data.items);
        setSelectedPoint(null);
        setNotice("");
      })
      .catch((caught) => {
        if (!cancelled) {
          setCampus(null);
          setPoints([]);
          setError(caught instanceof Error ? caught.message : "地图数据加载失败。");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [campusId, reloadToken]);

  const handleSelectPoint = useCallback(
    (point: ShopPoint) => {
      setNotice("");
      if (!user) {
        // 游客点击点位时不请求详情接口，只提示登录。
        setSelectedPoint(null);
        setNotice(`游客不能查看店铺详情，请先登录后再查看“${point.name}”。`);
        return;
      }
      setSelectedPoint(point);
      setNotice(
        `已选中“${point.name}”（${point.shop_type === "vendor" ? "摊贩" : "商铺"}）。店铺详情信息卡片将在第五步实现。`,
      );
    },
    [user],
  );

  const handleClearSelection = useCallback(() => {
    setSelectedPoint(null);
    setNotice("");
  }, []);

  const handleMapError = useCallback((message: string) => {
    setError(message);
  }, []);

  const visibleCount = useMemo(
    () =>
      points.filter((point) => shopTypeFilter === "all" || point.shop_type === shopTypeFilter)
        .length,
    [points, shopTypeFilter],
  );

  return (
    <main className="page map-page">
      <section className="map-toolbar">
        <label className="toolbar-item">
          当前校园
          <select
            value={campusId}
            onChange={(event) => setSearchParams({ campus: event.target.value })}
          >
            {campusList.map((item) => (
              <option key={item.campus_id} value={item.campus_id}>
                {item.campus_name}
              </option>
            ))}
          </select>
        </label>

        <span className="toolbar-item toolbar-muted">
          底图模式：{campus?.map_type === "real" ? "真实地图" : "图片底图"}
        </span>

        <label className="toolbar-item">
          店铺类型
          <select
            value={shopTypeFilter}
            onChange={(event) => setShopTypeFilter(event.target.value as ShopTypeFilter)}
          >
            <option value="all">全部</option>
            <option value="shop">商铺</option>
            <option value="vendor">摊贩</option>
          </select>
        </label>

        <button type="button" onClick={() => setResetSignal((value) => value + 1)}>
          重置视图
        </button>

        {user && (
          <input
            className="toolbar-search"
            placeholder="搜索美食店铺（第七步提供）"
            disabled
          />
        )}

        {user?.role === "admin" && (
          <button type="button" onClick={() => setShowAdminPanel((value) => !value)}>
            {showAdminPanel ? "收起地图配置" : "地图配置"}
          </button>
        )}
      </section>

      <div className={showAdminPanel && campus ? "map-layout with-panel" : "map-layout"}>
        <div className="map-canvas">
          {loading && <p className="map-overlay">正在加载地图……</p>}
          {campus && (
            <FoodMap
              campus={campus}
              points={points}
              shopTypeFilter={shopTypeFilter}
              selectedPointId={selectedPoint?.id ?? null}
              resetSignal={resetSignal}
              onSelectPoint={handleSelectPoint}
              onClearSelection={handleClearSelection}
              onMapError={handleMapError}
            />
          )}
          {!loading && !campus && <p className="map-overlay">{error || "地图暂不可用。"}</p>}
          {notice && <p className="map-notice">{notice}</p>}
        </div>

        {showAdminPanel && campus && user?.role === "admin" && (
          <AdminMapPanel
            campus={campus}
            onClose={() => setShowAdminPanel(false)}
            onSaved={() => setReloadToken((value) => value + 1)}
          />
        )}
      </div>

      <section className="map-status">
        <span>
          当前展示店铺：{visibleCount} 家（已通过审核 {points.length} 家）
        </span>
        <span>底图署名：{campus?.map_attribution ?? "开发演示底图（虚构示意图）"}</span>
        <span>
          后端服务：
          {health.phase === "ok" ? "正常" : health.phase === "loading" ? "检查中" : "连接失败"}
        </span>
        {error && <span className="status-error">{error}</span>}
      </section>

      <p className="hint">
        提示：游客可以浏览地图与公开点位；登录用户点击点位可以查看店铺信息，店铺详情信息卡片将在第五步提供。
      </p>
    </main>
  );
}
