export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
}

export interface HealthData {
  status: string;
}

export interface HealthState {
  phase: "loading" | "ok" | "error";
  message: string;
}

export interface UserPublic {
  id: number;
  username: string;
  role: "user" | "admin";
  is_active: boolean;
  created_at: string;
}
