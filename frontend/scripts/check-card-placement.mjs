/**
 * 校验详情卡片定位逻辑：优先右侧、依次尝试左侧/上方/下方，并始终收敛在容器内。
 *
 * 运行方式（在 frontend 目录执行）：
 *   node scripts/check-card-placement.mjs
 */

import { computeCardPlacement } from "../src/utils/cardPlacement.ts";

const cardWidth = 320;
const cardHeight = 340;
const container = { containerWidth: 1000, containerHeight: 600 };

const cases = [
  {
    name: "中间点位使用右侧",
    input: { pointX: 400, pointY: 300, ...container, cardWidth, cardHeight },
    expectedSide: "right",
  },
  {
    name: "靠近右边缘改用左侧",
    input: { pointX: 900, pointY: 300, ...container, cardWidth, cardHeight },
    expectedSide: "left",
  },
  {
    name: "靠近右边缘改用左侧（左侧优先于上方）",
    input: { pointX: 940, pointY: 560, ...container, cardWidth, cardHeight },
    expectedSide: "left",
  },
  {
    name: "容器较小时卡片收敛在边界内",
    input: { pointX: 150, pointY: 100, containerWidth: 360, containerHeight: 220, cardWidth, cardHeight },
    expectedSide: "bottom",
  },
];

let failures = 0;

for (const item of cases) {
  const placement = computeCardPlacement(item.input);
  const { containerWidth, containerHeight } = item.input;
  // 卡片高度随容器自适应（与 MapPage 中的计算保持一致）
  const effectiveHeight = Math.max(180, Math.min(cardHeight, containerHeight - 24));

  if (placement.side !== item.expectedSide) {
    failures += 1;
    console.error(`失败：${item.name} 期望 ${item.expectedSide}，实际 ${placement.side}`);
  }

  // 卡片左上角不能为负，也不会整体越出容器
  if (placement.left < 0 || placement.top < 0) {
    failures += 1;
    console.error(`失败：${item.name} 卡片位置越界`, placement);
  }
  if (placement.left + Math.min(cardWidth, containerWidth) > containerWidth + 1) {
    failures += 1;
    console.error(`失败：${item.name} 卡片横向超出容器`, placement);
  }
  if (placement.top + Math.min(effectiveHeight, containerHeight) > containerHeight + 1) {
    failures += 1;
    console.error(`失败：${item.name} 卡片纵向超出容器`, placement);
  }
  if (placement.arrowOffset < 16) {
    failures += 1;
    console.error(`失败：${item.name} 指示箭头位置不合法`, placement);
  }
}

if (failures === 0) {
  console.log("详情卡片定位校验通过：优先右侧、边缘自动换向，且始终收敛在地图容器内。");
  process.exit(0);
}

process.exit(1);
