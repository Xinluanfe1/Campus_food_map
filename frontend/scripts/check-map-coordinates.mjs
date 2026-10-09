/**
 * 校验图片底图坐标换算：底图尺寸变化后，点位的相对位置必须保持不变。
 *
 * 运行方式（在 frontend 目录执行）：
 *   node scripts/check-map-coordinates.mjs
 *
 * 说明：Node.js 22 及以上可以直接运行 TypeScript 文件（类型擦除）。
 */

import {
  imageBounds,
  normalizedToLeaflet,
  relativePosition,
} from "../src/utils/mapCoordinates.ts";

const cases = [
  { mapX: 0.2, mapY: 0.3 },
  { mapX: 0.5, mapY: 0.5 },
  { mapX: 0.75, mapY: 0.65 },
];

const geometries = [
  { width: 2400, height: 1600 },
  { width: 4800, height: 3200 },
  { width: 1200, height: 800 },
];

let failures = 0;

for (const point of cases) {
  const reference = relativePosition(point.mapX, point.mapY, geometries[0]);

  for (const geometry of geometries.slice(1)) {
    const current = relativePosition(point.mapX, point.mapY, geometry);
    const ok =
      Math.abs(current.x - reference.x) < 1e-9 && Math.abs(current.y - reference.y) < 1e-9;
    if (!ok) {
      failures += 1;
      console.error(
        `失败：点位 (${point.mapX}, ${point.mapY}) 在 ${geometry.width}×${geometry.height} 下的相对位置发生偏移`,
      );
    }
  }
}

// 边界检查：图片四角必须落在 Leaflet 边界内
const bounds = imageBounds(geometries[0]);
const topLeft = normalizedToLeaflet(0, 0, geometries[0]);
const bottomRight = normalizedToLeaflet(1, 1, geometries[0]);
const boundsOk =
  topLeft.x === bounds[0][1] &&
  topLeft.y === bounds[1][0] &&
  bottomRight.x === bounds[1][1] &&
  bottomRight.y === bounds[0][0];

if (!boundsOk) {
  failures += 1;
  console.error("失败：图片边界与归一化坐标换算结果不一致");
}

// 左上角对应 (0, 0)，右下角对应 (width, -height)
if (topLeft.x !== 0 || topLeft.y !== 0 || bottomRight.x !== 2400 || bottomRight.y !== -1600) {
  failures += 1;
  console.error("失败：图片坐标原点和方向的换算结果不正确", { topLeft, bottomRight });
}

if (failures === 0) {
  console.log("坐标换算校验通过：3 组点位 × 3 种图片尺寸的相对位置完全一致，边界换算正确。");
  process.exit(0);
}

process.exit(1);
