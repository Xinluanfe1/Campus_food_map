/**
 * 店铺详情信息卡片的定位计算。
 *
 * 规则（对应开发文档 5.2）：
 * 1. 卡片优先显示在点位右侧；
 * 2. 右侧空间不足时依次尝试左侧、上方或下方；
 * 3. 卡片必须收敛在地图容器内，不能完全超出可视区域。
 */

export type CardSide = "right" | "left" | "top" | "bottom";

export interface CardPlacementInput {
  pointX: number;
  pointY: number;
  containerWidth: number;
  containerHeight: number;
  cardWidth: number;
  cardHeight: number;
  offset?: number;
  margin?: number;
}

export interface CardPlacement {
  left: number;
  top: number;
  side: CardSide;
  arrowOffset: number;
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.min(Math.max(value, minimum), maximum);
}

export function computeCardPlacement(input: CardPlacementInput): CardPlacement {
  const offset = input.offset ?? 16;
  const margin = input.margin ?? 12;
  const { pointX, pointY, containerWidth, containerHeight, cardWidth, cardHeight } = input;

  const fitsRight = pointX + offset + cardWidth + margin <= containerWidth;
  const fitsLeft = pointX - offset - cardWidth - margin >= 0;
  const fitsTop = pointY - offset - cardHeight - margin >= 0;
  const fitsBottom = pointY + offset + cardHeight + margin <= containerHeight;

  let side: CardSide;
  if (fitsRight) {
    side = "right";
  } else if (fitsLeft) {
    side = "left";
  } else if (fitsTop) {
    side = "top";
  } else if (fitsBottom) {
    side = "bottom";
  } else {
    side = "bottom";
  }

  let left: number;
  let top: number;
  switch (side) {
    case "right":
      left = pointX + offset;
      top = pointY - cardHeight / 2;
      break;
    case "left":
      left = pointX - offset - cardWidth;
      top = pointY - cardHeight / 2;
      break;
    case "top":
      left = pointX - cardWidth / 2;
      top = pointY - offset - cardHeight;
      break;
    default:
      left = pointX - cardWidth / 2;
      top = pointY + offset;
      break;
  }

  // 收敛到容器内部，避免卡片因点位靠近地图边缘而完全超出可视区域。
  const maximumLeft = Math.max(margin, containerWidth - cardWidth - margin);
  const maximumTop = Math.max(margin, containerHeight - cardHeight - margin);
  left = clamp(left, margin, maximumLeft);
  top = clamp(top, margin, maximumTop);

  const arrowOffset =
    side === "left" || side === "right"
      ? clamp(pointY - top, 16, Math.max(16, cardHeight - 16))
      : clamp(pointX - left, 16, Math.max(16, cardWidth - 16));

  return { left, top, side, arrowOffset };
}
