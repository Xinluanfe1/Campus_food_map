import { useCallback, useEffect, useState, type FormEvent } from "react";

import {
  clearReaction,
  createReply,
  createReport,
  createReview,
  deleteReply,
  deleteReview,
  fetchReviews,
  setReaction,
  updateReview,
} from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type { ReviewItem } from "../types/api";

interface ShopReviewsProps {
  shopId: number;
  onRatingChanged?: () => void;
}

function formatTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN");
}

function stars(rating: number): string {
  return "★".repeat(rating) + "☆".repeat(Math.max(0, 5 - rating));
}

export default function ShopReviews({ shopId, onRatingChanged }: ShopReviewsProps) {
  const { user } = useAuth();
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [rating, setRating] = useState(5);
  const [content, setContent] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [replyDrafts, setReplyDrafts] = useState<Record<number, string>>({});
  const [reportDrafts, setReportDrafts] = useState<Record<number, string>>({});
  const [openReportId, setOpenReportId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetchReviews(shopId);
      setReviews(response.data.items);
      setTotal(response.data.total);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "评价列表加载失败。");
    } finally {
      setLoading(false);
    }
  }, [shopId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setNotice("");
    if (!content.trim()) {
      setError("评价内容不能为空。");
      return;
    }

    setSubmitting(true);
    try {
      if (editingId !== null) {
        await updateReview(editingId, { rating, content: content.trim() });
        setNotice("评价已更新。");
        setEditingId(null);
      } else {
        const response = await createReview(shopId, { rating, content: content.trim() });
        setNotice(response.message || "评价提交成功。");
      }
      setRating(5);
      setContent("");
      await load();
      onRatingChanged?.();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "评价提交失败，请稍后重试。");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleReaction(review: ReviewItem, reactionType: "like" | "dislike") {
    setError("");
    try {
      if (review.my_reaction === reactionType) {
        await clearReaction(review.id);
      } else {
        await setReaction(review.id, reactionType);
      }
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "互动操作失败，请稍后重试。");
    }
  }

  function startEdit(review: ReviewItem) {
    setEditingId(review.id);
    setRating(review.rating);
    setContent(review.content);
    setNotice("正在编辑自己的评价，修改后点击“保存修改”。");
  }

  function cancelEdit() {
    setEditingId(null);
    setRating(5);
    setContent("");
    setNotice("");
  }

  async function handleDeleteReview(review: ReviewItem) {
    if (!window.confirm("确定删除这条评价吗？删除后评分统计会同步更新。")) {
      return;
    }
    setError("");
    try {
      await deleteReview(review.id);
      setNotice("评价已删除。");
      await load();
      onRatingChanged?.();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "删除失败，请稍后重试。");
    }
  }

  async function handleReply(review: ReviewItem) {
    const draft = (replyDrafts[review.id] ?? "").trim();
    setError("");
    if (!draft) {
      setError("回复内容不能为空。");
      return;
    }
    try {
      await createReply(review.id, draft);
      setReplyDrafts((previous) => ({ ...previous, [review.id]: "" }));
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "回复失败，请稍后重试。");
    }
  }

  async function handleDeleteReply(replyId: number) {
    setError("");
    try {
      const response = await deleteReply(replyId);
      setNotice(response.data.action === "hidden" ? "回复已隐藏。" : "回复已删除。");
      await load();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "删除回复失败，请稍后重试。");
    }
  }

  async function handleReport(review: ReviewItem) {
    const reason = (reportDrafts[review.id] ?? "").trim();
    setError("");
    if (!reason) {
      setError("请填写举报理由。");
      return;
    }
    try {
      const response = await createReport(review.id, reason);
      setNotice(response.message || "举报已提交，管理员会尽快处理。");
      setReportDrafts((previous) => ({ ...previous, [review.id]: "" }));
      setOpenReportId(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "举报失败，请稍后重试。");
    }
  }

  return (
    <section className="shop-reviews">
      <h4>评价（{total}）</h4>

      {loading && <p className="card-note">正在加载评价……</p>}
      {error && <p className="alert alert-error">{error}</p>}
      {notice && <p className="alert alert-success">{notice}</p>}

      {reviews.map((review) => (
        <article className="review-item" key={review.id}>
          <div className="review-item-header">
            <strong>{review.username}</strong>
            <span className="review-stars" title={`${review.rating} 星`}>
              {stars(review.rating)}
            </span>
          </div>
          <p className="review-content">{review.content}</p>
          <p className="review-meta">
            {formatTime(review.created_at)}
            {review.updated_at !== review.created_at ? "（已编辑）" : ""}
          </p>

          <div className="review-button-row">
            <button
              type="button"
              className={review.my_reaction === "like" ? "reaction-button active" : "reaction-button"}
              onClick={() => handleReaction(review, "like")}
            >
              赞 {review.like_count}
            </button>
            <button
              type="button"
              className={
                review.my_reaction === "dislike" ? "reaction-button active" : "reaction-button"
              }
              onClick={() => handleReaction(review, "dislike")}
            >
              踩 {review.dislike_count}
            </button>
            {review.is_mine ? (
              <>
                <button type="button" className="reaction-button" onClick={() => startEdit(review)}>
                  编辑
                </button>
                <button
                  type="button"
                  className="reaction-button"
                  onClick={() => handleDeleteReview(review)}
                >
                  删除
                </button>
              </>
            ) : (
              <button
                type="button"
                className="reaction-button"
                onClick={() => setOpenReportId(openReportId === review.id ? null : review.id)}
              >
                举报
              </button>
            )}
          </div>

          {openReportId === review.id && (
            <div className="inline-form">
              <textarea
                rows={2}
                maxLength={500}
                placeholder="请填写举报理由"
                value={reportDrafts[review.id] ?? ""}
                onChange={(event) =>
                  setReportDrafts((previous) => ({ ...previous, [review.id]: event.target.value }))
                }
              />
              <button type="button" onClick={() => handleReport(review)}>
                提交举报
              </button>
            </div>
          )}

          {review.replies.length > 0 && (
            <ul className="reply-list">
              {review.replies.map((reply) => (
                <li key={reply.id}>
                  <span>
                    <strong>{reply.username}</strong>：{reply.content}
                  </span>
                  {user && (user.id === reply.user_id || user.role === "admin") && (
                    <button
                      type="button"
                      className="link-button"
                      onClick={() => handleDeleteReply(reply.id)}
                    >
                      {user.id === reply.user_id ? "删除" : "隐藏"}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}

          <div className="inline-form">
            <input
              placeholder="回复这条评价"
              maxLength={1000}
              value={replyDrafts[review.id] ?? ""}
              onChange={(event) =>
                setReplyDrafts((previous) => ({ ...previous, [review.id]: event.target.value }))
              }
            />
            <button type="button" onClick={() => handleReply(review)}>
              回复
            </button>
          </div>
        </article>
      ))}

      {!loading && reviews.length === 0 && <p className="card-note">还没有评价，欢迎提交第一条。</p>}

      <form className="review-form" onSubmit={handleSubmit}>
        <div className="rating-picker">
          {[1, 2, 3, 4, 5].map((value) => (
            <button
              type="button"
              key={value}
              className={value <= rating ? "star-button active" : "star-button"}
              onClick={() => setRating(value)}
              aria-label={`${value} 星`}
            >
              ★
            </button>
          ))}
          <span className="hint">{rating} 星</span>
        </div>
        <textarea
          rows={3}
          maxLength={2000}
          placeholder={editingId ? "修改评价内容" : "分享你的用餐体验"}
          value={content}
          onChange={(event) => setContent(event.target.value)}
        />
        <div className="review-form-actions">
          <button type="submit" disabled={submitting}>
            {submitting ? "提交中……" : editingId ? "保存修改" : "提交评价"}
          </button>
          {editingId !== null && (
            <button type="button" className="ghost-button" onClick={cancelEdit}>
              取消编辑
            </button>
          )}
        </div>
      </form>
    </section>
  );
}
