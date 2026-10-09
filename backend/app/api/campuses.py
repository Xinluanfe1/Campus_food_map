"""校园与地图公开接口（游客可访问）。"""

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.core.config import settings
from app.schemas.campus import CampusDetail, CampusMapConfig, CampusSummary, ShopPoint
from app.services import campus_service

router = APIRouter(prefix="/campuses", tags=["校园与地图"])


@router.get("", summary="获取允许公开访问的校园列表")
def list_campuses(
    session: DbSession,
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量，最大 100"),
) -> dict:
    campuses = campus_service.list_active_campuses(session)
    start = (page - 1) * page_size
    items = [
        CampusSummary.model_validate(campus).model_dump(mode="json")
        for campus in campuses[start : start + page_size]
    ]
    return {
        "success": True,
        "message": "获取成功",
        "data": {"items": items, "page": page, "page_size": page_size, "total": len(campuses)},
    }


@router.get("/{campus_id}", summary="获取校园基本信息及公开地图配置")
def read_campus(campus_id: str, session: DbSession) -> dict:
    campus = campus_service.get_campus(session, campus_id)
    return {
        "success": True,
        "message": "获取成功",
        "data": CampusDetail.model_validate(campus).model_dump(mode="json"),
    }


@router.get("/{campus_id}/map", summary="获取底图类型、中心、缩放和署名等信息")
def read_campus_map(campus_id: str, session: DbSession) -> dict:
    campus = campus_service.get_campus(session, campus_id)
    data = CampusMapConfig.model_validate(campus).model_dump(mode="json")
    # 百度地图模式下需要把 AK 下发给前端；AK 由部署环境变量提供，不写入代码仓库。
    # 其他提供方返回 None，避免无关密钥出现在响应中。
    data["baidu_map_ak"] = settings.baidu_map_ak if campus.map_provider == "baidu" else None
    return {
        "success": True,
        "message": "获取成功",
        "data": data,
    }


@router.get("/{campus_id}/shops/points", summary="获取地图所需的最少店铺点位信息")
def list_shop_points(campus_id: str, session: DbSession) -> dict:
    campus = campus_service.get_campus(session, campus_id)
    shops = campus_service.list_public_shop_points(session, campus)

    # 只返回当前底图类型对应的坐标字段，避免图片坐标与经纬度混用。
    if campus.map_type == "image":
        items = [
            ShopPoint(
                id=shop.id,
                name=shop.name,
                shop_type=shop.shop_type,
                map_x=shop.map_x,
                map_y=shop.map_y,
            ).model_dump(mode="json", exclude_none=True)
            for shop in shops
        ]
    else:
        items = [
            ShopPoint(
                id=shop.id,
                name=shop.name,
                shop_type=shop.shop_type,
                latitude=shop.latitude,
                longitude=shop.longitude,
            ).model_dump(mode="json", exclude_none=True)
            for shop in shops
        ]

    return {
        "success": True,
        "message": "获取成功",
        "data": {"campus_id": campus.campus_id, "map_type": campus.map_type, "items": items},
    }
