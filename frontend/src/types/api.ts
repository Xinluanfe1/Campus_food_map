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

export interface PagedData<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface CampusSummary {
  campus_id: string;
  campus_name: string;
  map_type: "image" | "real";
  is_active: boolean;
}

export interface CampusMapConfig {
  campus_id: string;
  campus_name: string;
  map_type: "image" | "real";
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

export interface ShopPoint {
  id: number;
  name: string;
  shop_type: "shop" | "vendor";
  map_x?: number;
  map_y?: number;
  latitude?: number;
  longitude?: number;
}

export interface ShopPointsData {
  campus_id: string;
  map_type: "image" | "real";
  items: ShopPoint[];
}

export interface CampusMapUploadResult {
  map_asset_url: string;
  image_width: number;
  image_height: number;
}

export type ShopTypeFilter = "all" | "shop" | "vendor";
