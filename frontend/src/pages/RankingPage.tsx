import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { fetchCampuses, fetchShopRankings } from "../api/client";
import type { CampusSummary, RankingShopItem } from "../types/api";

const PAGE_SIZE = 20;

export default function RankingPage() {
  const navigate = useNavigate();
  const [campusList, setCampusList] = useState<CampusSummary[]>([]);
  const [campusId, setCampusId] = useState("");
  const [shopType, setShopType] = useState<"all" | "shop" | "vendor">("all");
  const [sort, setSort] = useState<"desc" | "asc">("desc");
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<RankingShopItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchCampuses()
      .then((response) => {
        setCampusList(response.data.items);
        setCampusId((current) => current || response.data.items[0]?.campus_id || "");
      })
      .catch((caught) => setError(caught instanceof Error ? caught.message : "校园列表加载失败。"));
  }, []);

  const load = useCallback(async () => {
    if (!campusId) {
      return;
    }
    setLoading(true);
    setError("");
    try {
      const response = await fetchShopRankings(campusId, shopType, sort, page, PAGE_SIZE);
      setItems(response.data.items);
      setTotal(response.data.total);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "排行榜加载失败。");
    } finally {
      setLoading(false);
    }
  }, [campusId, page, shopType, sort]);

  useEffect(() => {
    void load();
  }, [load]);

  function openOnMap(shopId: number) {
    navigate(`/?campus=${encodeURIComponent(campusId)}&shop=${shopId}`);
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <main className="page ranking-page">
      <h1>校园美食排行榜</h1>
      <p className="subtitle">按加权评分排序，只统计有效评价；无有效评价的店铺不参与排名。</p>

      <div className="ranking-filters">
        <span className="toolbar-item">
          当前校园：
          {campusList.length > 1 ? (
            <select
              value={campusId}
              onChange={(event) => {
                setCampusId(event.target.value);
                setPage(1);
              }}
            >
              {campusList.map((campus) => (
                <option key={campus.campus_id} value={campus.campus_id}>
                  {campus.campus_name}
                </option>
              ))}
            </select>
          ) : (
            <strong>{campusList[0]?.campus_name ?? "加载中……"}</strong>
          )}
        </span>

        <div className="admin-tabs">
          {(
            [
              ["all", "全部类型"],
              ["shop", "商铺"],
              ["vendor", "摊贩"],
            ] as const
          ).map(([value, label]) => (
            <button
              type="button"
              key={value}
              className={shopType === value ? "tab active" : "tab"}
              onClick={() => {
                setShopType(value);
                setPage(1);
              }}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="admin-tabs">
          {(
            [
              ["desc", "评分从高到低"],
              ["asc", "评分从低到高"],
            ] as const
          ).map(([value, label]) => (
            <button
              type="button"
              key={value}
              className={sort === value ? "tab active" : "tab"}
              onClick={() => {
                setSort(value);
                setPage(1);
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="alert alert-error">{error}</p>}

      <section className="card">
        {loading ? (
          <p className="hint">正在加载排行榜……</p>
        ) : items.length === 0 ? (
          <p className="hint">暂无有效评价的店铺，暂时没有排名数据。</p>
        ) : (
          <table className="ranking-table">
            <thead>
              <tr>
                <th>排名</th>
                <th>店铺名称</th>
                <th>类型</th>
                <th>加权评分</th>
                <th>有效评价</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.shop_id} onClick={() => openOnMap(item.shop_id)}>
                  <td>{item.rank}</td>
                  <td>{item.name}</td>
                  <td>{item.shop_type === "vendor" ? "摊贩" : "商铺"}</td>
                  <td>{item.weighted_rating.toFixed(2)}</td>
                  <td>{item.review_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <div className="pagination">
          <button
            type="button"
            className="ghost-button"
            onClick={() => setPage((value) => Math.max(1, value - 1))}
            disabled={page <= 1}
          >
            上一页
          </button>
          <span className="hint">
            第 {page} / {totalPages} 页（共 {total} 家店铺）
          </span>
          <button
            type="button"
            className="ghost-button"
            onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
            disabled={page >= totalPages}
          >
            下一页
          </button>
        </div>
      </section>

      <p className="hint">点击任意一行可以返回地图，并在对应点位打开店铺详情信息卡片。</p>
    </main>
  );
}
