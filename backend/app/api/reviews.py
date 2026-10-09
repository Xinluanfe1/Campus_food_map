"""评价、顶踩、回复与举报接口。"""

from fastapi import APIRouter, Query, Response

from app.api.deps import CurrentUser, DbSession
from app.schemas.review import (
    ReactionRequest,
    ReplyCreateRequest,
    ReportCreateRequest,
    ReviewCreateRequest,
    ReviewUpdateRequest,
)
from app.services import report_service, review_service

router = APIRouter(tags=["评价与互动"])


@router.post("/shops/{shop_id}/reviews", status_code=201, summary="创建评价（已有评价时更新）")
def create_review(
    shop_id: int,
    payload: ReviewCreateRequest,
    current_user: CurrentUser,
    session: DbSession,
    response: Response,
) -> dict:
    shop = review_service.get_approved_shop(session, shop_id)
    review, created = review_service.upsert_review(session, shop, current_user, payload)
    if not created:
        response.status_code = 200

    return {
        "success": True,
        "message": "评价提交成功。" if created else "评价已更新。",
        "data": review_service.build_review_item(
            session, review, current_user.username, current_user
        ),
    }


@router.get("/shops/{shop_id}/reviews", summary="分页获取有效评价")
def list_reviews(
    shop_id: int,
    current_user: CurrentUser,
    session: DbSession,
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量，最大 100"),
) -> dict:
    shop = review_service.get_approved_shop(session, shop_id)
    items, total = review_service.list_visible_reviews(session, shop, current_user, page, page_size)
    return {
        "success": True,
        "message": "获取成功",
        "data": {"items": items, "page": page, "page_size": page_size, "total": total},
    }


@router.patch("/reviews/{review_id}", summary="编辑自己的评价")
def update_review(
    review_id: int,
    payload: ReviewUpdateRequest,
    current_user: CurrentUser,
    session: DbSession,
) -> dict:
    review = review_service.get_own_review(session, review_id, current_user)
    updated = review_service.update_review(session, review, payload)
    return {
        "success": True,
        "message": "评价已更新。",
        "data": review_service.build_review_item(
            session, updated, current_user.username, current_user
        ),
    }


@router.delete("/reviews/{review_id}", summary="删除自己的评价")
def delete_review(review_id: int, current_user: CurrentUser, session: DbSession) -> dict:
    review = review_service.get_own_review(session, review_id, current_user)
    review_service.delete_review(session, review)
    return {"success": True, "message": "评价已删除。", "data": None}


@router.put("/reviews/{review_id}/reaction", summary="设置点赞或点踩（幂等）")
def set_reaction(
    review_id: int,
    payload: ReactionRequest,
    current_user: CurrentUser,
    session: DbSession,
) -> dict:
    review = review_service.get_visible_review(session, review_id)
    reaction_type = review_service.set_reaction(session, review, current_user, payload)
    return {
        "success": True,
        "message": "互动已保存。",
        "data": {"reaction_type": reaction_type},
    }


@router.delete("/reviews/{review_id}/reaction", summary="取消当前互动")
def clear_reaction(review_id: int, current_user: CurrentUser, session: DbSession) -> dict:
    review = review_service.get_visible_review(session, review_id)
    review_service.clear_reaction(session, review, current_user)
    return {"success": True, "message": "已取消互动。", "data": None}


@router.post("/reviews/{review_id}/replies", status_code=201, summary="回复一条评价（仅一级回复）")
def create_reply(
    review_id: int,
    payload: ReplyCreateRequest,
    current_user: CurrentUser,
    session: DbSession,
) -> dict:
    review = review_service.get_visible_review(session, review_id)
    reply = review_service.create_reply(session, review, current_user, payload)
    return {
        "success": True,
        "message": "回复成功。",
        "data": {
            "id": reply.id,
            "content": reply.content,
            "created_at": reply.created_at.isoformat(),
        },
    }


@router.get("/reviews/{review_id}/replies", summary="获取评价的一级回复")
def list_replies(review_id: int, current_user: CurrentUser, session: DbSession) -> dict:
    review = review_service.get_visible_review(session, review_id)
    return {
        "success": True,
        "message": "获取成功",
        "data": {"items": review_service.list_replies(session, review)},
    }


@router.delete("/replies/{reply_id}", summary="删除自己的回复或由管理员隐藏回复")
def delete_reply(reply_id: int, current_user: CurrentUser, session: DbSession) -> dict:
    action = review_service.delete_or_hide_reply(session, reply_id, current_user)
    return {
        "success": True,
        "message": "回复已删除。" if action == "deleted" else "回复已隐藏。",
        "data": {"action": action},
    }


@router.post("/reviews/{review_id}/reports", status_code=201, summary="举报评价")
def create_report(
    review_id: int,
    payload: ReportCreateRequest,
    current_user: CurrentUser,
    session: DbSession,
) -> dict:
    review = review_service.get_visible_review(session, review_id)
    report = report_service.create_report(session, review, current_user, payload)
    return {
        "success": True,
        "message": "举报已提交，管理员会尽快处理。",
        "data": {"id": report.id, "status": report.status},
    }
