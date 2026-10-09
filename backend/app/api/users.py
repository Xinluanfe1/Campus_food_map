"""当前用户相关接口。"""

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models import Shop
from app.schemas.shop import ShopSummary
from app.services import ranking_service

router = APIRouter(prefix="/users", tags=["用户"])


@router.get("/me/shops", summary="查看自己提交的店铺及审核状态")
def list_my_shops(
    current_user: CurrentUser,
    session: DbSession,
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量，最大 100"),
) -> dict:
    condition = Shop.submitted_by == current_user.id
    total = session.scalar(select(func.count()).select_from(Shop).where(condition)) or 0
    shops = session.scalars(
        select(Shop)
        .where(condition)
        .order_by(Shop.created_at.desc(), Shop.id.desc())
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


@router.get("/me/contributions", summary="获取当前用户的贡献统计")
def read_my_contributions(
    current_user: CurrentUser,
    session: DbSession,
    campus_id: str | None = Query(None, description="指定校园时返回该校园的贡献排名"),
) -> dict:
    data = ranking_service.user_contribution(session, current_user, campus_id)
    return {"success": True, "message": "获取成功", "data": data}
