import { useCallback, useEffect, useState } from "react";

import { fetchContributorRankings, fetchCampuses, fetchMyContribution } from "../api/client";
import type { CampusSummary, ContributionSummary, ContributorItem } from "../types/api";

const PAGE_SIZE = 20;

export default function ContributorsPage() {
  const [campusList, setCampusList] = useState<CampusSummary[]>([]);
  const [campusId, setCampusId] = useState("");
  const [items, setItems] = useState<ContributorItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [summary, setSummary] = useState<ContributionSummary | null>(null);
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
      const [ranking, mine] = await Promise.all([
        fetchContributorRankings(campusId, page, PAGE_SIZE),
        fetchMyContribution(campusId),
      ]);
      setItems(ranking.data.items);
      setTotal(ranking.data.total);
      setSummary(mine.data);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "贡献榜加载失败。");
    } finally {
      setLoading(false);
    }
  }, [campusId, page]);

  useEffect(() => {
    void load();
  }, [load]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <main className="page contributors-page">
      <h1>美食贡献榜</h1>
      <p className="subtitle">只统计审核通过的有效店铺；待审核、被拒绝或已删除的店铺不计入贡献数量。</p>

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
      </div>

      {error && <p className="alert alert-error">{error}</p>}

      <section className="card">
        <h2>我的贡献统计</h2>
        {summary ? (
          <p>
            已审核通过的店铺：<strong>{summary.approved_shop_count}</strong> 家
            {summary.rank !== null ? `（当前校园贡献榜第 ${summary.rank} 名）` : "（暂无排名）"}
          </p>
        ) : (
          <p className="hint">正在加载个人贡献统计……</p>
        )}
      </section>

      <section className="card">
        {loading ? (
          <p className="hint">正在加载贡献榜……</p>
        ) : items.length === 0 ? (
          <p className="hint">当前校园还没有审核通过的店铺贡献记录。</p>
        ) : (
          <table className="ranking-table">
            <thead>
              <tr>
                <th>排名</th>
                <th>用户名</th>
                <th>审核通过店铺数</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.user_id}>
                  <td>{item.rank}</td>
                  <td>{item.username}</td>
                  <td>{item.approved_shop_count}</td>
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
            第 {page} / {totalPages} 页（共 {total} 位贡献者）
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
    </main>
  );
}
