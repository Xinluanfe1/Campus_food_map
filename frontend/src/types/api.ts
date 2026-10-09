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

export interface RatingSummary {
  average_rating: number | null;
  weighted_rating: number | null;
  review_count: number;
  like_count: number;
  dislike_count: number;
}

export interface ShopDetailData {
  id: number;
  campus_id: string;
  name: string;
  description: string;
  shop_type: "shop" | "vendor";
  photo_url: string | null;
  status: "pending" | "approved" | "rejected";
  map_x?: number | null;
  map_y?: number | null;
  latitude?: number | null;
  longitude?: number | null;
  created_at: string;
  updated_at: string;
  rating: RatingSummary;
}

export interface ShopSubmitPayload {
  name: string;
  description: string;
  shop_type: "shop" | "vendor";
  photo_url: string | null;
  map_x: number | null;
  map_y: number | null;
  latitude: number | null;
  longitude: number | null;
}

export interface MyShopItem {
  id: number;
  campus_id: string;
  name: string;
  description: string;
  shop_type: "shop" | "vendor";
  photo_url: string | null;
  submitted_by: number;
  status: "pending" | "approved" | "rejected";
  map_x: number | null;
  map_y: number | null;
  latitude: number | null;
  longitude: number | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface PendingShopItem {
  id: number;
  campus_id: string;
  name: string;
  description: string;
  shop_type: "shop" | "vendor";
  photo_url: string | null;
  submitted_by: number;
  submitter_username: string;
  status: string;
  map_x?: number | null;
  map_y?: number | null;
  latitude?: number | null;
  longitude?: number | null;
  created_at: string;
  updated_at: string;
}

export interface ShopPhotoUploadResult {
  photo_url: string;
}
