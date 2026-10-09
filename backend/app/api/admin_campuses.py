"""管理员校园配置接口。"""

from fastapi import APIRouter, File, UploadFile

from app.api.deps import AdminUser, DbSession
from app.schemas.campus import CampusCreateRequest, CampusDetail, CampusMapUpdateRequest, CampusPatchRequest
from app.services import campus_service, upload_service

router = APIRouter(prefix="/admin", tags=["管理员"])


@router.post("/campuses", status_code=201, summary="新增校园配置")
def create_campus(payload: CampusCreateRequest, _admin: AdminUser, session: DbSession) -> dict:
    campus = campus_service.create_campus(session, payload)
    return {
        "success": True,
        "message": "校园配置创建成功。",
        "data": CampusDetail.model_validate(campus).model_dump(mode="json"),
    }


@router.patch("/campuses/{campus_id}", summary="修改校园基本信息与展示状态")
def patch_campus(
    campus_id: str,
    payload: CampusPatchRequest,
    _admin: AdminUser,
    session: DbSession,
) -> dict:
    campus = campus_service.patch_campus(session, campus_id, payload)
    return {
        "success": True,
        "message": "校园信息已更新。",
        "data": CampusDetail.model_validate(campus).model_dump(mode="json"),
    }


@router.put("/campuses/{campus_id}/map", summary="更新校园地图配置")
def update_campus_map(
    campus_id: str,
    payload: CampusMapUpdateRequest,
    _admin: AdminUser,
    session: DbSession,
) -> dict:
    campus = campus_service.update_campus_map(session, campus_id, payload)
    return {
        "success": True,
        "message": "校园地图配置已更新。",
        "data": CampusDetail.model_validate(campus).model_dump(mode="json"),
    }


@router.post("/uploads/campus-map", summary="上传校园图片底图")
def upload_campus_map(
    _admin: AdminUser,
    file: UploadFile = File(..., description="校园底图文件，支持 PNG、JPEG、WebP"),
) -> dict:
    data = upload_service.save_campus_map(file)
    return {"success": True, "message": "底图上传成功。", "data": data}
