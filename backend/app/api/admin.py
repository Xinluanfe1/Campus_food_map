"""管理员接口。

第三步只提供管理员权限依赖与待审核列表，用于验证角色校验；
审核通过与拒绝操作在第五步实现。
"""

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import AdminUser, DbSession
from app.models import Shop
from app.schemas.shop import ShopSummary

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
    shops = session.scalars(
        select(Shop)
        .where(condition)
        .order_by(Shop.created_at.asc(), Shop.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return {
        "success": True,
        "message": "获取成功",
        "data": {
            "items": [ShopSummary.model_validate(shop).model_dump(mode="json") for shop in shops],
            "page": page,
            "page_size": page_size,
            "total": total,
        },
    }
