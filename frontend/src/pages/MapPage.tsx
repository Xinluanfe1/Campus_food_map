import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { fetchCampusMap, fetchCampuses, fetchShopDetail, fetchShopPoints } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import AdminMapPanel from "../components/AdminMapPanel";
import FoodMap from "../components/FoodMap";
import ShopDetailCard from "../components/ShopDetailCard";
import { useHealthStatus } from "../hooks/useHealthStatus";
import type {
  CampusMapConfig,
  CampusSummary,
  ShopDetailData,
  ShopPoint,
  ShopTypeFilter,
} from "../types/api";

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
  const [detail, setDetail] = useState<ShopDetailData | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const detailRequestRef = useRef(0);
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
        setDetail(null);
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

  const handleClearSelection = useCallback(() => {
    detailRequestRef.current += 1;
    setSelectedPoint(null);
    setDetail(null);
    setDetailError("");
    setDetailLoading(false);
    setNotice("");
  }, []);

  const handleSelectPoint = useCallback(
    (point: ShopPoint) => {
      setNotice("");

      // 再次点击同一个点位时关闭卡片（点击地图空白区域不会关闭）。
      if (selectedPoint?.id === point.id) {
        handleClearSelection();
        return;
      }

      if (!user) {
        // 游客点击点位时不请求详情接口，只提示登录。
        setSelectedPoint(null);
        setDetail(null);
        setNotice(`游客不能查看店铺详情，请先登录后再查看“${point.name}”。`);
        return;
      }

      setSelectedPoint(point);
      setDetail(null);
      setDetailError("");
      setDetailLoading(true);

      // 记录请求序号，避免快速切换点位时旧请求覆盖新内容。
      detailRequestRef.current += 1;
      const requestId = detailRequestRef.current;
      fetchShopDetail(campusId, point.id)
        .then((response) => {
          if (detailRequestRef.current === requestId) {
            setDetail(response.data);
          }
        })
        .catch((caught) => {
          if (detailRequestRef.current === requestId) {
            setDetailError(caught instanceof Error ? caught.message : "店铺详情加载失败。");
          }
        })
        .finally(() => {
          if (detailRequestRef.current === requestId) {
            setDetailLoading(false);
          }
        });
    },
    [campusId, handleClearSelection, selectedPoint, user],
  );

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
              onMapError={handleMapError}
              renderOverlay={(position) => {
                if (!position || !selectedPoint) {
                  return null;
                }
                return (
                  <ShopDetailCard
                    pointX={position.x}
                    pointY={position.y}
                    containerWidth={position.width}
                    containerHeight={position.height}
                    shopName={selectedPoint.name}
                    shopType={selectedPoint.shop_type}
                    detail={detail}
                    loading={detailLoading}
                    error={detailError}
                    onClose={handleClearSelection}
                  />
                );
              }}
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
        提示：游客可以浏览地图与公开点位；登录用户点击点位会在点位附近打开店铺详情信息卡片，点击卡片右上角的 × 或再次点击同一个点位即可关闭。
      </p>
    </main>
  );
}
