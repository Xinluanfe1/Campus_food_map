import { useCallback, useEffect, useState } from "react";

import { approveShop, fetchCampusMap, fetchPendingShops, rejectShop } from "../api/client";
import type { CampusMapConfig, PendingShopItem } from "../types/api";
import PointPicker, { type PickedPoint } from "./PointPicker";

function formatTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN");
}

function toPickedPoint(item: PendingShopItem): PickedPoint {
  return {
    map_x: item.map_x ?? null,
    map_y: item.map_y ?? null,
    latitude: item.latitude ?? null,
    longitude: item.longitude ?? null,
  };
}

export default function AdminShopReview() {
  const [items, setItems] = useState<PendingShopItem[]>([]);
  const [campusMap, setCampusMap] = useState<Record<string, CampusMapConfig>>({});
  const [reasons, setReasons] = useState<Record<number, string>>({});
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      const response = await fetchPendingShops();
      setItems(response.data.items);

      const campusIds = Array.from(new Set(response.data.items.map((item) => item.campus_id)));
      const configs = await Promise.all(
        campusIds.map(async (id) => {
          const config = await fetchCampusMap(id);
          return [id, config.data] as const;
        }),
      );
      setCampusMap(Object.fromEntries(configs));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "待审核列表加载失败。");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleApprove(item: PendingShopItem) {
    setError("");
    setMessage("");
    setBusyId(item.id);
    try {
      await approveShop(item.id);
      setMessage(`已通过“${item.name}”（审核时间：${new Date().toLocaleString("zh-CN")}）。`);
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "审核操作失败，请稍后重试。");
    } finally {
      setBusyId(null);
    }
  }

  async function handleReject(item: PendingShopItem) {
    const reason = (reasons[item.id] ?? "").trim();
    setError("");
    setMessage("");
    if (!reason) {
      setError("拒绝店铺时必须填写拒绝原因。");
      return;
    }
    setBusyId(item.id);
    try {
      await rejectShop(item.id, reason);
      setMessage(`已拒绝“${item.name}”（审核时间：${new Date().toLocaleString("zh-CN")}）。`);
      setReasons((previous) => ({ ...previous, [item.id]: "" }));
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "审核操作失败，请稍后重试。");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section>
      {message && <p className="alert alert-success">{message}</p>}
      {error && <p className="alert alert-error">{error}</p>}

      {items.length === 0 ? (
        <section className="card">
          <p className="hint">当前没有待审核的店铺。</p>
        </section>
      ) : (
        items.map((item) => (
          <section className="card review-card" key={item.id}>
            <div className="review-card-header">
              <h2>{item.name}</h2>
              <span className="status-tag status-pending">待审核</span>
            </div>
            <p className="hint">
              类型：{item.shop_type === "vendor" ? "摊贩" : "商铺"} · 提交者：
              {item.submitter_username} · 提交时间：{formatTime(item.created_at)}
            </p>
            <p className="review-description">{item.description}</p>
            {item.photo_url && (
              <img className="photo-preview" src={item.photo_url} alt={`${item.name} 的门店照片`} />
            )}

            <div className="point-picker-block">
              <p className="field-label">店铺位置预览</p>
              {campusMap[item.campus_id] ? (
                <PointPicker
                  campus={campusMap[item.campus_id]}
                  value={toPickedPoint(item)}
                  readOnly
                  height={200}
                />
              ) : (
                <p className="hint">正在加载位置预览……</p>
              )}
            </div>

            <div className="review-actions">
              <button type="button" onClick={() => handleApprove(item)} disabled={busyId === item.id}>
                {busyId === item.id ? "处理中……" : "通过"}
              </button>
              <textarea
                value={reasons[item.id] ?? ""}
                onChange={(event) =>
                  setReasons((previous) => ({ ...previous, [item.id]: event.target.value }))
                }
                placeholder="拒绝原因（拒绝时必须填写）"
                rows={2}
                maxLength={500}
              />
              <button
                type="button"
                className="danger-button"
                onClick={() => handleReject(item)}
                disabled={busyId === item.id}
              >
                拒绝
              </button>
            </div>
          </section>
        ))
      )}
    </section>
  );
}
