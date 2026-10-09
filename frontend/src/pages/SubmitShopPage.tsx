import { useCallback, useEffect, useState, type ChangeEvent, type FormEvent } from "react";

import {
  createShop,
  fetchCampusMap,
  fetchCampuses,
  fetchMyShops,
  uploadShopPhoto,
} from "../api/client";
import PointPicker, { EMPTY_POINT, type PickedPoint } from "../components/PointPicker";
import type { CampusMapConfig, CampusSummary, MyShopItem } from "../types/api";

const STATUS_TEXT: Record<string, string> = {
  pending: "待审核",
  approved: "已通过",
  rejected: "已拒绝",
};

function formatTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN");
}

export default function SubmitShopPage() {
  const [campusList, setCampusList] = useState<CampusSummary[]>([]);
  const [campusId, setCampusId] = useState("");
  const [campus, setCampus] = useState<CampusMapConfig | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [shopType, setShopType] = useState<"shop" | "vendor">("shop");
  const [point, setPoint] = useState<PickedPoint>(EMPTY_POINT);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [photoName, setPhotoName] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [myShops, setMyShops] = useState<MyShopItem[]>([]);

  const loadMyShops = useCallback(async () => {
    try {
      const response = await fetchMyShops();
      setMyShops(response.data.items);
    } catch {
      // 个人提交记录加载失败不影响提交表单。
    }
  }, []);

  useEffect(() => {
    fetchCampuses()
      .then((response) => {
        setCampusList(response.data.items);
        if (response.data.items.length > 0) {
          setCampusId((current) => current || response.data.items[0].campus_id);
        }
      })
      .catch((caught) => setError(caught instanceof Error ? caught.message : "校园列表加载失败。"));
    void loadMyShops();
  }, [loadMyShops]);

  useEffect(() => {
    if (!campusId) {
      return;
    }
    setPoint(EMPTY_POINT);
    fetchCampusMap(campusId)
      .then((response) => setCampus(response.data))
      .catch((caught) => setError(caught instanceof Error ? caught.message : "校园地图配置加载失败。"));
  }, [campusId]);

  async function handlePhotoChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    setError("");
    setMessage("");
    setUploading(true);
    try {
      const response = await uploadShopPhoto(file);
      setPhotoUrl(response.data.photo_url);
      setPhotoName(file.name);
      setMessage("照片上传成功，提交店铺时会一起保存。");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "照片上传失败，请稍后重试。");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!campusId || !campus) {
      setError("请先选择校园。");
      return;
    }
    const hasLocation =
      campus.map_type === "image"
        ? point.map_x !== null && point.map_y !== null
        : point.latitude !== null && point.longitude !== null;
    if (!hasLocation) {
      setError("请在地图上点击选择店铺位置。");
      return;
    }

    setSubmitting(true);
    try {
      const response = await createShop(campusId, {
        name: name.trim(),
        description: description.trim(),
        shop_type: shopType,
        photo_url: photoUrl,
        ...point,
      });
      setMessage(response.message || "已提交，等待管理员审核。");
      setName("");
      setDescription("");
      setShopType("shop");
      setPoint(EMPTY_POINT);
      setPhotoUrl(null);
      setPhotoName("");
      await loadMyShops();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "提交失败，请稍后重试。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page submit-page">
      <h1>提交美食店铺</h1>
      <p className="subtitle">
        提交的店铺需要经过管理员审核后才会公开展示；审核结果会显示在页面下方的提交记录中。
      </p>

      <section className="card">
        <form className="shop-form" onSubmit={handleSubmit}>
          <label>
            当前校园
            <select value={campusId} onChange={(event) => setCampusId(event.target.value)}>
              {campusList.map((item) => (
                <option key={item.campus_id} value={item.campus_id}>
                  {item.campus_name}
                </option>
              ))}
            </select>
          </label>

          <label>
            店铺名称（必填）
            <input value={name} onChange={(event) => setName(event.target.value)} maxLength={100} required />
          </label>

          <label>
            店铺简介（必填）
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              maxLength={2000}
              rows={4}
              required
            />
          </label>

          <fieldset className="shop-type-field">
            <legend>店铺类型（必填）</legend>
            <label>
              <input
                type="radio"
                name="shop_type"
                value="shop"
                checked={shopType === "shop"}
                onChange={() => setShopType("shop")}
              />
              商铺
            </label>
            <label>
              <input
                type="radio"
                name="shop_type"
                value="vendor"
                checked={shopType === "vendor"}
                onChange={() => setShopType("vendor")}
              />
              摊贩
            </label>
          </fieldset>

          <label>
            店铺照片（选填，PNG / JPEG / WebP，最大 5 MB）
            <input type="file" accept=".png,.jpg,.jpeg,.webp" onChange={handlePhotoChange} disabled={uploading} />
          </label>
          {photoName && <p className="hint">已选择照片：{photoName}</p>}
          {photoUrl && <img className="photo-preview" src={photoUrl} alt="店铺照片预览" />}

          <div className="point-picker-block">
            <p className="field-label">店铺位置（必填）：在地图上点击选择</p>
            {campus ? (
              <PointPicker campus={campus} value={point} onChange={setPoint} height={320} />
            ) : (
              <p className="hint">正在加载地图……</p>
            )}
            <p className="hint">
              {campus?.map_type === "image"
                ? point.map_x !== null
                  ? `已选择图片坐标：map_x = ${point.map_x.toFixed(3)}，map_y = ${(point.map_y ?? 0).toFixed(3)}`
                  : "尚未选择位置。"
                : point.latitude !== null
                  ? `已选择经纬度：${point.latitude.toFixed(6)}，${(point.longitude ?? 0).toFixed(6)}`
                  : "尚未选择位置。"}
            </p>
          </div>

          <button type="submit" disabled={submitting}>
            {submitting ? "提交中……" : "提交店铺"}
          </button>
        </form>

        {message && <p className="alert alert-success">{message}</p>}
        {error && <p className="alert alert-error">{error}</p>}
      </section>

      <section className="card">
        <h2>我的提交记录</h2>
        {myShops.length === 0 ? (
          <p className="hint">还没有提交记录。</p>
        ) : (
          <ul className="my-shop-list">
            {myShops.map((shop) => (
              <li key={shop.id}>
                <div className="my-shop-header">
                  <strong>{shop.name}</strong>
                  <span className={`status-tag status-${shop.status}`}>{STATUS_TEXT[shop.status]}</span>
                </div>
                <p className="hint">
                  {shop.shop_type === "vendor" ? "摊贩" : "商铺"} · 提交时间：{formatTime(shop.created_at)}
                </p>
                {shop.status === "rejected" && shop.rejection_reason && (
                  <p className="status-error">拒绝原因：{shop.rejection_reason}</p>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
