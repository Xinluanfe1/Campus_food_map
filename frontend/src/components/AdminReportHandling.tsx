import { useCallback, useEffect, useState } from "react";

import { dismissReport, fetchReports, resolveReport } from "../api/client";
import type { ReportItem } from "../types/api";

function formatTime(value: string | null): string {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN");
}

const STATUS_TEXT: Record<string, string> = {
  pending: "待处理",
  resolved: "已处理（评价已隐藏）",
  dismissed: "已驳回（评价保留）",
};

export default function AdminReportHandling() {
  const [items, setItems] = useState<ReportItem[]>([]);
  const [notes, setNotes] = useState<Record<number, string>>({});
  const [statusFilter, setStatusFilter] = useState<"pending" | "all">("pending");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setError("");
    try {
      const response = await fetchReports(statusFilter);
      setItems(response.data.items);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "举报列表加载失败。");
    }
  }, [statusFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleDismiss(item: ReportItem) {
    setError("");
    setMessage("");
    setBusyId(item.id);
    try {
      const response = await dismissReport(item.id, (notes[item.id] ?? "").trim() || null);
      setMessage(`举报 #${item.id}：${response.message}`);
      setNotes((previous) => ({ ...previous, [item.id]: "" }));
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "处理失败，请稍后重试。");
    } finally {
      setBusyId(null);
    }
  }

  async function handleResolve(item: ReportItem) {
    if (!window.confirm("确定隐藏这条评价吗？隐藏后该评价将从公开列表与评分统计中移除。")) {
      return;
    }
    setError("");
    setMessage("");
    setBusyId(item.id);
    try {
      const response = await resolveReport(item.id, (notes[item.id] ?? "").trim() || null);
      setMessage(`举报 #${item.id}：${response.message}`);
      setNotes((previous) => ({ ...previous, [item.id]: "" }));
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "处理失败，请稍后重试。");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section>
      <div className="admin-tabs">
        <button
          type="button"
          className={statusFilter === "pending" ? "tab active" : "tab"}
          onClick={() => setStatusFilter("pending")}
        >
          待处理举报
        </button>
        <button
          type="button"
          className={statusFilter === "all" ? "tab active" : "tab"}
          onClick={() => setStatusFilter("all")}
        >
          全部举报
        </button>
      </div>

      {message && <p className="alert alert-success">{message}</p>}
      {error && <p className="alert alert-error">{error}</p>}

      {items.length === 0 ? (
        <section className="card">
          <p className="hint">当前没有需要处理的举报。</p>
        </section>
      ) : (
        items.map((item) => (
          <section className="card review-card" key={item.id}>
            <div className="review-card-header">
              <h2>举报 #{item.id}</h2>
              <span className={`status-tag status-${item.status === "pending" ? "pending" : "approved"}`}>
                {STATUS_TEXT[item.status] ?? item.status}
              </span>
            </div>
            <p className="hint">
              被举报店铺：{item.shop_name ?? "店铺已删除"} · 举报人：{item.reporter_username} · 举报时间：
              {formatTime(item.created_at)}
            </p>
            <blockquote className="review-quote">
              {item.review_content ?? "评价已删除"}
              {item.review_status === "hidden" && "（该评价已隐藏）"}
            </blockquote>
            <p>
              <strong>举报原因：</strong>
              {item.reason}
            </p>
            {item.status !== "pending" && (
              <p className="hint">
                处理备注：{item.handling_note ?? "无"} · 处理时间：{formatTime(item.handled_at)}
              </p>
            )}

            {item.status === "pending" && (
              <div className="review-actions">
                <textarea
                  rows={2}
                  maxLength={500}
                  placeholder="处理备注（可选）"
                  value={notes[item.id] ?? ""}
                  onChange={(event) =>
                    setNotes((previous) => ({ ...previous, [item.id]: event.target.value }))
                  }
                />
                <button type="button" onClick={() => handleDismiss(item)} disabled={busyId === item.id}>
                  {busyId === item.id ? "处理中……" : "驳回举报（保留评价）"}
                </button>
                <button
                  type="button"
                  className="danger-button"
                  onClick={() => handleResolve(item)}
                  disabled={busyId === item.id}
                >
                  隐藏评价并处理举报
                </button>
              </div>
            )}
          </section>
        ))
      )}
    </section>
  );
}
