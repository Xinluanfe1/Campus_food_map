"""店铺提交、修改与详情接口。"""

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.shop import ShopSubmitRequest, ShopUpdateRequest
from app.services import campus_service, shop_service

router = APIRouter(tags=["店铺"])


@router.post(
    "/campuses/{campus_id}/shops",
    status_code=201,
    summary="提交新店铺（状态固定为待审核）",
)
def create_shop(
    campus_id: str,
    payload: ShopSubmitRequest,
    current_user: CurrentUser,
    session: DbSession,
) -> dict:
    campus = campus_service.get_campus(session, campus_id)
    shop = shop_service.create_shop(session, campus, current_user, payload)
    return {
        "success": True,
        "message": "已提交，等待管理员审核。",
        "data": shop_service.build_detail_payload(session, shop, campus.map_type),
    }


@router.get("/campuses/{campus_id}/shops/{shop_id}", summary="获取店铺详情")
def read_shop(
    campus_id: str,
    shop_id: int,
    current_user: CurrentUser,
    session: DbSession,
) -> dict:
    campus = campus_service.get_campus(session, campus_id)
    shop = shop_service.get_visible_shop(session, campus, shop_id, current_user)
    return {
        "success": True,
        "message": "获取成功",
        "data": shop_service.build_detail_payload(session, shop, campus.map_type),
    }


@router.patch("/shops/{shop_id}", summary="修改店铺信息（提交者或管理员）")
def update_shop(
    shop_id: int,
    payload: ShopUpdateRequest,
    current_user: CurrentUser,
    session: DbSession,
) -> dict:
    shop = shop_service.get_shop_or_404(session, shop_id)
    campus = campus_service.get_campus(session, shop.campus_id, include_inactive=True)
    updated = shop_service.update_shop(session, shop, current_user, payload)
    return {
        "success": True,
        "message": "店铺信息已更新。",
        "data": shop_service.build_detail_payload(session, updated, campus.map_type),
    }
