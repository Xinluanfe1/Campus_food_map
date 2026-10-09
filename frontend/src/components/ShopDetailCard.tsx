import { useEffect, useRef, useState, type CSSProperties } from "react";

import { computeCardPlacement } from "../utils/cardPlacement";
import type { ShopDetailData } from "../types/api";

interface ShopDetailCardProps {
  pointX: number;
  pointY: number;
  containerWidth: number;
  containerHeight: number;
  shopName: string;
  shopType: string;
  detail: ShopDetailData | null;
  loading: boolean;
  error: string;
  onClose: () => void;
}

const CARD_WIDTH = 320;
export const CARD_MAX_HEIGHT = 340;

function formatRating(value: number | null | undefined): string {
  return value === null || value === undefined ? "暂无评分" : value.toFixed(2);
}

export default function ShopDetailCard({
  pointX,
  pointY,
  containerWidth,
  containerHeight,
  shopName,
  shopType,
  detail,
  loading,
  error,
  onClose,
}: ShopDetailCardProps) {
  const [photoFailed, setPhotoFailed] = useState(false);
  const [cardHeight, setCardHeight] = useState(CARD_MAX_HEIGHT);
  const cardRef = useRef<HTMLDivElement | null>(null);
  const typeText = (detail?.shop_type ?? shopType) === "vendor" ? "摊贩" : "商铺";
  // 卡片高度不能超过地图容器，小屏幕下允许内部滚动。
  const maxHeight = Math.max(180, Math.min(CARD_MAX_HEIGHT, containerHeight - 24));

  // 测量卡片实际高度，保证卡片位置与指示箭头始终对准点位。
  useEffect(() => {
    const element = cardRef.current;
    if (!element) {
      return;
    }
    const applyHeight = () => {
      const height = Math.min(element.offsetHeight || maxHeight, maxHeight);
      setCardHeight((previous) => (Math.abs(previous - height) > 2 ? height : previous));
    };
    applyHeight();
    if (typeof ResizeObserver === "undefined") {
      return;
    }
    const observer = new ResizeObserver(applyHeight);
    observer.observe(element);
    return () => observer.disconnect();
  }, [maxHeight, detail, loading, error]);

  const placement = computeCardPlacement({
    pointX,
    pointY,
    containerWidth,
    containerHeight,
    cardWidth: CARD_WIDTH,
    cardHeight: Math.min(cardHeight, maxHeight),
  });

  return (
    <div
      ref={cardRef}
      className={`shop-card shop-card-${placement.side}`}
      style={{
        left: placement.left,
        top: placement.top,
        width: CARD_WIDTH,
        maxHeight,
      }}
    >
      <span
        className="shop-card-arrow"
        style={{ "--arrow-offset": `${placement.arrowOffset}px` } as CSSProperties}
      />
      <div className="shop-card-header">
        <h3>{shopName}</h3>
        <button type="button" className="ghost-button shop-card-close" onClick={onClose} aria-label="关闭店铺详情">
          关闭
        </button>
      </div>

      <div className="shop-card-body">
        {loading && <p className="card-note">正在加载店铺详情……</p>}
        {error && <p className="alert alert-error">{error}</p>}

        {detail && (
          <>
            {detail.photo_url && !photoFailed && (
              <img
                className="shop-card-photo"
                src={detail.photo_url}
                alt={`${detail.name} 的门店照片`}
                onError={() => setPhotoFailed(true)}
              />
            )}
            <p className="shop-card-meta">
              类型：{typeText}
              <span className="shop-card-separator">|</span>
              加权评分：{formatRating(detail.rating.weighted_rating)}
              <span className="shop-card-separator">|</span>
              有效评价：{detail.rating.review_count} 条
            </p>
            <p className="shop-card-description">{detail.description}</p>
            {detail.status !== "approved" && (
              <p className="card-note">
                当前状态：
                {detail.status === "pending" ? "待审核（仅自己和管理员可见）" : "已拒绝"}
              </p>
            )}
            <p className="card-note">评价列表与评价互动入口将在第六步提供。</p>
          </>
        )}
      </div>
    </div>
  );
}
