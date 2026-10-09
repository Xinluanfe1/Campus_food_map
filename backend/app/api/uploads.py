"""店铺照片上传接口（上传使用 /api/v1 前缀，访问入口见 assets 模块）。"""

from fastapi import APIRouter, File, UploadFile

from app.api.deps import CurrentUser
from app.services import upload_service

router = APIRouter(tags=["图片上传"])


@router.post("/uploads/shop-photo", summary="上传店铺照片")
def upload_shop_photo(
    _current_user: CurrentUser,
    file: UploadFile = File(..., description="店铺照片，支持 PNG、JPEG、WebP"),
) -> dict:
    data = upload_service.save_shop_photo(file)
    return {"success": True, "message": "照片上传成功。", "data": data}
