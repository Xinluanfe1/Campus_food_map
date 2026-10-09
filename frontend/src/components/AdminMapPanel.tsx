import { useState, type ChangeEvent, type FormEvent } from "react";

import { uploadCampusMap, updateCampusMap, type CampusMapUpdatePayload } from "../api/client";
import type { CampusMapConfig } from "../types/api";

interface AdminMapPanelProps {
  campus: CampusMapConfig;
  onClose: () => void;
  onSaved: () => void;
}

interface FormState {
  map_type: string;
  map_asset_url: string;
  tile_url_template: string;
  map_attribution: string;
  image_width: string;
  image_height: string;
  default_map_x: string;
  default_map_y: string;
  default_latitude: string;
  default_longitude: string;
  default_zoom: string;
  boundary_radius_meters: string;
  allow_off_campus: boolean;
}

function toText(value: number | null | undefined): string {
  return value === null || value === undefined ? "" : String(value);
}

function toNumberOrNull(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function buildFormState(campus: CampusMapConfig): FormState {
  return {
    map_type: campus.map_type,
    map_asset_url: campus.map_asset_url ?? "",
    tile_url_template: campus.tile_url_template ?? "",
    map_attribution: campus.map_attribution ?? "",
    image_width: toText(campus.image_width),
    image_height: toText(campus.image_height),
    default_map_x: toText(campus.default_map_x),
    default_map_y: toText(campus.default_map_y),
    default_latitude: toText(campus.default_latitude),
    default_longitude: toText(campus.default_longitude),
    default_zoom: toText(campus.default_zoom),
    boundary_radius_meters: toText(campus.boundary_radius_meters ?? null),
    allow_off_campus: campus.allow_off_campus,
  };
}

export default function AdminMapPanel({ campus, onClose, onSaved }: AdminMapPanelProps) {
  const [form, setForm] = useState<FormState>(() => buildFormState(campus));
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);

  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((previous) => ({ ...previous, [key]: value }));
  }

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    setError("");
    setMessage("");
    setUploading(true);
    try {
      const result = await uploadCampusMap(file);
      setForm((previous) => ({
        ...previous,
        map_asset_url: result.data.map_asset_url,
        image_width: String(result.data.image_width),
        image_height: String(result.data.image_height),
      }));
      setMessage("底图上传成功，请保存配置后生效。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "底图上传失败，请稍后重试。");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    setSaving(true);

    const payload: CampusMapUpdatePayload = {
      map_type: form.map_type,
      map_asset_url: form.map_asset_url.trim() || null,
      tile_url_template: form.tile_url_template.trim() || null,
      map_attribution: form.map_attribution.trim() || null,
      allow_off_campus: form.allow_off_campus,
      image_width: toNumberOrNull(form.image_width),
      image_height: toNumberOrNull(form.image_height),
      default_map_x: toNumberOrNull(form.default_map_x),
      default_map_y: toNumberOrNull(form.default_map_y),
      default_latitude: toNumberOrNull(form.default_latitude),
      default_longitude: toNumberOrNull(form.default_longitude),
      default_zoom: toNumberOrNull(form.default_zoom) ?? 1,
      boundary_radius_meters: toNumberOrNull(form.boundary_radius_meters),
    };

    try {
      await updateCampusMap(campus.campus_id, payload);
      setMessage("地图配置已保存。");
      onSaved();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "保存失败，请稍后重试。");
    } finally {
      setSaving(false);
    }
  }

  return (
    <aside className="admin-panel">
      <div className="admin-panel-header">
        <h2>地图配置</h2>
        <button type="button" className="ghost-button" onClick={onClose}>
          关闭
        </button>
      </div>
      <p className="hint">管理员可以修改底图类型、底图文件、默认视图与校园范围配置。</p>

      <form className="admin-form" onSubmit={handleSubmit}>
        <label>
          底图类型
          <select
            value={form.map_type}
            onChange={(event) => updateField("map_type", event.target.value)}
          >
            <option value="image">图片底图</option>
            <option value="real">真实地图</option>
          </select>
        </label>

        <label>
          上传图片底图（PNG / JPEG / WebP，最大 5 MB）
          <input type="file" accept=".png,.jpg,.jpeg,.webp" onChange={handleUpload} disabled={uploading} />
        </label>
        <label>
          底图访问路径
          <input
            value={form.map_asset_url}
            onChange={(event) => updateField("map_asset_url", event.target.value)}
            placeholder="/assets/maps/xxx.png"
          />
        </label>
        <div className="admin-form-row">
          <label>
            图片宽度（像素）
            <input
              type="number"
              value={form.image_width}
              onChange={(event) => updateField("image_width", event.target.value)}
            />
          </label>
          <label>
            图片高度（像素）
            <input
              type="number"
              value={form.image_height}
              onChange={(event) => updateField("image_height", event.target.value)}
            />
          </label>
        </div>
        <div className="admin-form-row">
          <label>
            图片中心横向比例
            <input
              type="number"
              step="0.01"
              value={form.default_map_x}
              onChange={(event) => updateField("default_map_x", event.target.value)}
            />
          </label>
          <label>
            图片中心纵向比例
            <input
              type="number"
              step="0.01"
              value={form.default_map_y}
              onChange={(event) => updateField("default_map_y", event.target.value)}
            />
          </label>
        </div>

        <label>
          瓦片地址模板（真实地图）
          <input
            value={form.tile_url_template}
            onChange={(event) => updateField("tile_url_template", event.target.value)}
            placeholder="https://example.com/{z}/{x}/{y}.png"
          />
        </label>
        <label>
          地图署名
          <input
            value={form.map_attribution}
            onChange={(event) => updateField("map_attribution", event.target.value)}
          />
        </label>
        <div className="admin-form-row">
          <label>
            默认纬度
            <input
              type="number"
              step="0.0001"
              value={form.default_latitude}
              onChange={(event) => updateField("default_latitude", event.target.value)}
            />
          </label>
          <label>
            默认经度
            <input
              type="number"
              step="0.0001"
              value={form.default_longitude}
              onChange={(event) => updateField("default_longitude", event.target.value)}
            />
          </label>
        </div>
        <div className="admin-form-row">
          <label>
            默认缩放级别
            <input
              type="number"
              step="0.5"
              value={form.default_zoom}
              onChange={(event) => updateField("default_zoom", event.target.value)}
            />
          </label>
          <label>
            校园范围半径（米）
            <input
              type="number"
              step="50"
              value={form.boundary_radius_meters}
              onChange={(event) => updateField("boundary_radius_meters", event.target.value)}
            />
          </label>
        </div>
        <label className="admin-checkbox">
          <input
            type="checkbox"
            checked={form.allow_off_campus}
            onChange={(event) => updateField("allow_off_campus", event.target.checked)}
          />
          允许展示校园范围以外的店铺
        </label>

        <button type="submit" disabled={saving}>
          {saving ? "保存中……" : "保存地图配置"}
        </button>
      </form>

      {message && <p className="alert alert-success">{message}</p>}
      {error && <p className="alert alert-error">{error}</p>}
    </aside>
  );
}
