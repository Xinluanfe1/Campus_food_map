import type { ApiResponse, HealthData } from "../types/api";

const API_BASE = "/api/v1";

async function request<T>(path: string): Promise<ApiResponse<T>> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error(`请求失败（HTTP ${response.status}）`);
  }

  return (await response.json()) as ApiResponse<T>;
}

export function fetchHealth(): Promise<ApiResponse<HealthData>> {
  return request<HealthData>("/health");
}
