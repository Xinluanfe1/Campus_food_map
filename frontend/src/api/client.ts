import type {
  ApiResponse,
  CampusMapConfig,
  CampusMapUploadResult,
  CampusSummary,
  HealthData,
  PagedData,
  PendingShopItem,
  ShopDetailData,
  ShopPhotoUploadResult,
  ShopPointsData,
  ShopSubmitPayload,
  MyShopItem,
  UserPublic,
} from "../types/api";

const API_BASE = "/api/v1";
const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** 读取前端可访问的 Cookie（仅用于 CSRF 令牌，认证 Cookie 为 HttpOnly 不可读取）。 */
function readCookie(name: string): string | null {
  const prefix = `${name}=`;
  for (const part of document.cookie.split(";")) {
    const item = part.trim();
    if (item.startsWith(prefix)) {
      return decodeURIComponent(item.slice(prefix.length));
    }
  }
  return null;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  formData?: FormData;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<ApiResponse<T>> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };

  if (options.body !== undefined && options.formData === undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (UNSAFE_METHODS.has(method)) {
    const csrfToken = readCookie("csrf_token");
    if (csrfToken) {
      headers["X-CSRF-Token"] = csrfToken;
    }
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    credentials: "include",
    body:
      options.formData ??
      (options.body === undefined ? undefined : JSON.stringify(options.body)),
  });

  let payload: ApiResponse<T> | null = null;
  try {
    payload = (await response.json()) as ApiResponse<T>;
  } catch {
    payload = null;
  }

  if (!response.ok || payload === null || payload.success === false) {
    throw new ApiError(response.status, payload?.message ?? `请求失败（HTTP ${response.status}）`);
  }

  return payload;
}

export function fetchHealth(): Promise<ApiResponse<HealthData>> {
  return request<HealthData>("/health");
}

export function fetchCurrentUser(): Promise<ApiResponse<UserPublic>> {
  return request<UserPublic>("/auth/me");
}

export function registerAccount(username: string, password: string): Promise<ApiResponse<UserPublic>> {
  return request<UserPublic>("/auth/register", {
    method: "POST",
    body: { username, password },
  });
}

export function loginAccount(username: string, password: string): Promise<ApiResponse<UserPublic>> {
  return request<UserPublic>("/auth/login", {
    method: "POST",
    body: { username, password },
  });
}

export function logoutAccount(): Promise<ApiResponse<null>> {
  return request<null>("/auth/logout", { method: "POST" });
}

export function fetchCampuses(): Promise<ApiResponse<PagedData<CampusSummary>>> {
  return request<PagedData<CampusSummary>>("/campuses");
}

export function fetchCampusMap(campusId: string): Promise<ApiResponse<CampusMapConfig>> {
  return request<CampusMapConfig>(`/campuses/${encodeURIComponent(campusId)}/map`);
}

export function fetchShopPoints(campusId: string): Promise<ApiResponse<ShopPointsData>> {
  return request<ShopPointsData>(`/campuses/${encodeURIComponent(campusId)}/shops/points`);
}

export interface CampusMapUpdatePayload {
  map_type: string;
  map_asset_url: string | null;
  tile_url_template: string | null;
  map_attribution: string | null;
  allow_off_campus: boolean;
  image_width: number | null;
  image_height: number | null;
  default_map_x: number | null;
  default_map_y: number | null;
  default_latitude: number | null;
  default_longitude: number | null;
  default_zoom: number;
  boundary_radius_meters: number | null;
}

export function updateCampusMap(
  campusId: string,
  payload: CampusMapUpdatePayload,
): Promise<ApiResponse<CampusMapConfig>> {
  return request<CampusMapConfig>(`/admin/campuses/${encodeURIComponent(campusId)}/map`, {
    method: "PUT",
    body: payload,
  });
}

export function uploadCampusMap(file: File): Promise<ApiResponse<CampusMapUploadResult>> {
  const formData = new FormData();
  formData.append("file", file);
  return request<CampusMapUploadResult>("/admin/uploads/campus-map", {
    method: "POST",
    formData,
  });
}

export function fetchShopDetail(campusId: string, shopId: number): Promise<ApiResponse<ShopDetailData>> {
  return request<ShopDetailData>(
    `/campuses/${encodeURIComponent(campusId)}/shops/${shopId}`,
  );
}

export function createShop(
  campusId: string,
  payload: ShopSubmitPayload,
): Promise<ApiResponse<ShopDetailData>> {
  return request<ShopDetailData>(`/campuses/${encodeURIComponent(campusId)}/shops`, {
    method: "POST",
    body: payload,
  });
}

export function fetchMyShops(): Promise<ApiResponse<PagedData<MyShopItem>>> {
  return request<PagedData<MyShopItem>>("/users/me/shops");
}

export function uploadShopPhoto(file: File): Promise<ApiResponse<ShopPhotoUploadResult>> {
  const formData = new FormData();
  formData.append("file", file);
  return request<ShopPhotoUploadResult>("/uploads/shop-photo", { method: "POST", formData });
}

export function fetchPendingShops(): Promise<ApiResponse<PagedData<PendingShopItem>>> {
  return request<PagedData<PendingShopItem>>("/admin/shops/pending");
}

export function approveShop(shopId: number): Promise<ApiResponse<Record<string, unknown>>> {
  return request<Record<string, unknown>>(`/admin/shops/${shopId}/approve`, { method: "POST" });
}

export function rejectShop(
  shopId: number,
  reason: string,
): Promise<ApiResponse<Record<string, unknown>>> {
  return request<Record<string, unknown>>(`/admin/shops/${shopId}/reject`, {
    method: "POST",
    body: { reason },
  });
}
