/**
 * 图片底图坐标换算。
 *
 * 数据库保存归一化坐标 map_x、map_y（0 至 1）：
 * - map_x 表示从图片左侧向右的比例；
 * - map_y 表示从图片顶部向下的比例。
 *
 * Leaflet 使用 CRS.Simple 时纵轴向上，因此图片坐标需要把 map_y 取负。
 * 使用归一化坐标后，更换高清底图或调整图片尺寸不会导致点位整体偏移。
 */

export interface ImageGeometry {
  width: number;
  height: number;
}

export interface LeafletPoint {
  x: number;
  y: number;
}

export function normalizedToLeaflet(
  mapX: number,
  mapY: number,
  geometry: ImageGeometry,
): LeafletPoint {
  return {
    x: geometry.width * mapX,
    y: -geometry.height * mapY,
  };
}

export function imageBounds(
  geometry: ImageGeometry,
): [[number, number], [number, number]] {
  return [
    [-geometry.height, 0],
    [0, geometry.width],
  ];
}

/** 返回点位在底图中的相对位置，用于验证图片尺寸变化后比例保持不变。 */
export function relativePosition(
  mapX: number,
  mapY: number,
  geometry: ImageGeometry,
): LeafletPoint {
  const point = normalizedToLeaflet(mapX, mapY, geometry);
  return {
    x: point.x / geometry.width,
    y: -point.y / geometry.height,
  };
}
