import type { ApiResponse, HealthData, UserPublic } from "../types/api";

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
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<ApiResponse<T>> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };

  if (options.body !== undefined) {
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
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
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
