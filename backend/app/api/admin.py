"""管理员接口：店铺审核与待审核列表。"""

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import AdminUser, DbSession
from app.models import Campus, Shop, User
from app.schemas.shop import PendingShopItem, ShopRejectRequest
from app.services import shop_service

router = APIRouter(prefix="/admin", tags=["管理员"])


@router.get("/shops/pending", summary="获取待审核店铺列表")
def list_pending_shops(
    _admin: AdminUser,
    session: DbSession,
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量，最大 100"),
) -> dict:
    condition = Shop.status == "pending"
    total = session.scalar(select(func.count()).select_from(Shop).where(condition)) or 0
    rows = session.execute(
        select(Shop, User.username)
        .join(User, Shop.submitted_by == User.id)
        .where(condition)
        .order_by(Shop.created_at.asc(), Shop.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    items = []
    for shop, submitter_username in rows:
        campus = session.get(Campus, shop.campus_id)
        coordinates = (
            {"map_x": shop.map_x, "map_y": shop.map_y}
            if campus is not None and campus.map_type == "image"
            else {"latitude": shop.latitude, "longitude": shop.longitude}
        )
        items.append(
            PendingShopItem(
                id=shop.id,
                campus_id=shop.campus_id,
                name=shop.name,
                description=shop.description,
                shop_type=shop.shop_type,
                photo_url=shop.photo_url,
                submitted_by=shop.submitted_by,
                submitter_username=submitter_username,
                status=shop.status,
                created_at=shop.created_at,
                updated_at=shop.updated_at,
                **coordinates,
            ).model_dump(mode="json")
        )

    return {
        "success": True,
        "message": "获取成功",
        "data": {"items": items, "page": page, "page_size": page_size, "total": total},
    }


@router.post("/shops/{shop_id}/approve", summary="审核通过店铺")
def approve_shop(shop_id: int, admin: AdminUser, session: DbSession) -> dict:
    shop = shop_service.approve_shop(session, shop_id, admin)
    return {
        "success": True,
        "message": "店铺已审核通过。",
        "data": {"id": shop.id, "status": shop.status, "reviewed_by": shop.reviewed_by},
    }


@router.post("/shops/{shop_id}/reject", summary="拒绝店铺并填写原因")
def reject_shop(
    shop_id: int,
    payload: ShopRejectRequest,
    admin: AdminUser,
    session: DbSession,
) -> dict:
    shop = shop_service.reject_shop(session, shop_id, admin, payload.reason)
    return {
        "success": True,
        "message": "店铺已被拒绝。",
        "data": {
            "id": shop.id,
            "status": shop.status,
            "rejection_reason": shop.rejection_reason,
            "reviewed_by": shop.reviewed_by,
        },
    }
