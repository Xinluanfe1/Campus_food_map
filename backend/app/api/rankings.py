"""排行榜与店铺搜索接口。"""

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.services import campus_service, ranking_service

router = APIRouter(prefix="/campuses", tags=["排行榜与搜索"])


@router.get("/{campus_id}/rankings/shops", summary="获取店铺评分排行榜")
def shop_rankings(
    campus_id: str,
    _current_user: CurrentUser,
    session: DbSession,
    shop_type: str = Query("all", pattern="^(all|shop|vendor)$", description="店铺类型筛选"),
    sort: str = Query("desc", pattern="^(desc|asc)$", description="排序方式：desc 或 asc"),
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量，最大 100"),
) -> dict:
    campus = campus_service.get_campus(session, campus_id)
    items, total = ranking_service.list_shop_rankings(
        session, campus, shop_type, sort, page, page_size
    )
    return {
        "success": True,
        "message": "获取成功",
        "data": {"items": items, "page": page, "page_size": page_size, "total": total},
    }


@router.get("/{campus_id}/rankings/contributors", summary="获取校园贡献榜")
def contributor_rankings(
    campus_id: str,
    _current_user: CurrentUser,
    session: DbSession,
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量，最大 100"),
) -> dict:
    campus = campus_service.get_campus(session, campus_id)
    items, total = ranking_service.list_contributor_rankings(session, campus, page, page_size)
    return {
        "success": True,
        "message": "获取成功",
        "data": {"items": items, "page": page, "page_size": page_size, "total": total},
    }


@router.get("/{campus_id}/search", summary="按关键词搜索公开店铺")
def search_shops(
    campus_id: str,
    _current_user: CurrentUser,
    session: DbSession,
    q: str = Query("", max_length=50, description="搜索关键词，匹配店铺名称或简介"),
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量，最大 100"),
) -> dict:
    campus = campus_service.get_campus(session, campus_id)
    items, total = ranking_service.search_public_shops(session, campus, q, page, page_size)
    return {
        "success": True,
        "message": "获取成功",
        "data": {
            "items": items,
            "keyword": q.strip(),
            "page": page,
            "page_size": page_size,
            "total": total,
        },
    }
