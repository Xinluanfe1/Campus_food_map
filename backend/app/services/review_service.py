"""评价、顶踩与回复业务逻辑（对应开发文档 6.5 至 6.7）。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessError
from app.models import Review, ReviewReaction, ReviewReply, Shop, User
from app.schemas.review import (
    ReactionRequest,
    ReplyCreateRequest,
    ReviewCreateRequest,
    ReviewItem,
    ReviewReplyItem,
    ReviewUpdateRequest,
)


def get_approved_shop(session: Session, shop_id: int) -> Shop:
    """评价只能关联审核通过的店铺。"""

    shop = session.get(Shop, shop_id)
    if shop is None or shop.status != "approved":
        raise BusinessError(404, "店铺不存在或未公开。")
    return shop


def get_visible_review(session: Session, review_id: int) -> Review:
    """读取可见评价；隐藏或不存在的评价按 404 处理。"""

    review = session.get(Review, review_id)
    if review is None or review.status != "visible":
        raise BusinessError(404, "评价不存在或已被隐藏。")
    return review


def upsert_review(
    session: Session,
    shop: Shop,
    user: User,
    payload: ReviewCreateRequest,
) -> tuple[Review, bool]:
    """创建评价；同一用户对同一家店铺已有评价时更新原有记录。"""

    review = session.scalar(
        select(Review).where(Review.shop_id == shop.id, Review.user_id == user.id)
    )
    created = review is None
    if review is None:
        review = Review(shop_id=shop.id, user_id=user.id, status="visible")
        session.add(review)

    review.rating = payload.rating
    review.content = payload.content
    # 重新提交评价后恢复可见状态，保证用户修改后的内容可以重新参与统计。
    review.status = "visible"
    session.commit()
    session.refresh(review)
    return review, created


def get_own_review(session: Session, review_id: int, user: User) -> Review:
    """编辑或删除评价时校验作者身份（管理员也不能修改他人评价）。"""

    review = session.get(Review, review_id)
    if review is None:
        raise BusinessError(404, "评价不存在。")
    if review.user_id != user.id:
        raise BusinessError(403, "只能修改或删除自己的评价。")
    return review


def update_review(session: Session, review: Review, payload: ReviewUpdateRequest) -> Review:
    """更新自己的评价内容或评分。"""

    if payload.rating is not None:
        review.rating = payload.rating
    if payload.content is not None:
        review.content = payload.content
    session.commit()
    session.refresh(review)
    return review


def delete_review(session: Session, review: Review) -> None:
    """删除评价；相关的顶踩、回复与举报记录由数据库级联清理。"""

    session.delete(review)
    session.commit()


def list_visible_reviews(
    session: Session,
    shop: Shop,
    viewer: User,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    """分页获取店铺的有效（可见）评价。"""

    condition = (Review.shop_id == shop.id, Review.status == "visible")
    total = session.scalar(select(func.count()).select_from(Review).where(*condition)) or 0
    rows = session.execute(
        select(Review, User.username)
        .join(User, Review.user_id == User.id)
        .where(*condition)
        .order_by(Review.created_at.desc(), Review.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    items = [build_review_item(session, review, username, viewer) for review, username in rows]
    return items, int(total)


def _reaction_count(session: Session, review_id: int, reaction_type: str) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(ReviewReaction)
            .where(
                ReviewReaction.review_id == review_id,
                ReviewReaction.reaction_type == reaction_type,
            )
        )
        or 0
    )


def build_review_item(
    session: Session,
    review: Review,
    username: str,
    viewer: User,
) -> dict:
    """构造评价列表项：互动统计、当前用户互动状态与一级回复。"""

    my_reaction = session.scalar(
        select(ReviewReaction.reaction_type).where(
            ReviewReaction.review_id == review.id,
            ReviewReaction.user_id == viewer.id,
        )
    )
    reply_rows = session.execute(
        select(ReviewReply, User.username)
        .join(User, ReviewReply.user_id == User.id)
        .where(ReviewReply.review_id == review.id, ReviewReply.status == "visible")
        .order_by(ReviewReply.created_at.asc(), ReviewReply.id.asc())
    ).all()
    replies = [
        ReviewReplyItem(
            id=reply.id,
            user_id=reply.user_id,
            username=reply_username,
            content=reply.content,
            created_at=reply.created_at,
        )
        for reply, reply_username in reply_rows
    ]

    return ReviewItem(
        id=review.id,
        user_id=review.user_id,
        username=username,
        rating=review.rating,
        content=review.content,
        created_at=review.created_at,
        updated_at=review.updated_at,
        like_count=_reaction_count(session, review.id, "like"),
        dislike_count=_reaction_count(session, review.id, "dislike"),
        my_reaction=my_reaction,
        is_mine=review.user_id == viewer.id,
        replies=replies,
    ).model_dump(mode="json")


def set_reaction(
    session: Session,
    review: Review,
    user: User,
    payload: ReactionRequest,
) -> str:
    """幂等设置点赞或点踩：未互动则创建，已是相同类型则维持，已是另一类型则切换。"""

    reaction = session.scalar(
        select(ReviewReaction).where(
            ReviewReaction.review_id == review.id,
            ReviewReaction.user_id == user.id,
        )
    )
    if reaction is None:
        session.add(
            ReviewReaction(
                review_id=review.id,
                user_id=user.id,
                reaction_type=payload.reaction_type,
            )
        )
    else:
        reaction.reaction_type = payload.reaction_type

    session.commit()
    return payload.reaction_type


def clear_reaction(session: Session, review: Review, user: User) -> None:
    """取消当前用户对该评价的互动记录。"""

    reaction = session.scalar(
        select(ReviewReaction).where(
            ReviewReaction.review_id == review.id,
            ReviewReaction.user_id == user.id,
        )
    )
    if reaction is not None:
        session.delete(reaction)
        session.commit()


def create_reply(
    session: Session,
    review: Review,
    user: User,
    payload: ReplyCreateRequest,
) -> ReviewReply:
    """回复评价：只支持一级回复，不创建对回复的回复。"""

    reply = ReviewReply(
        review_id=review.id,
        user_id=user.id,
        content=payload.content,
        status="visible",
    )
    session.add(reply)
    session.commit()
    session.refresh(reply)
    return reply


def list_replies(session: Session, review: Review) -> list[dict]:
    """获取评价的可见一级回复。"""

    rows = session.execute(
        select(ReviewReply, User.username)
        .join(User, ReviewReply.user_id == User.id)
        .where(ReviewReply.review_id == review.id, ReviewReply.status == "visible")
        .order_by(ReviewReply.created_at.asc(), ReviewReply.id.asc())
    ).all()
    return [
        ReviewReplyItem(
            id=reply.id,
            user_id=reply.user_id,
            username=username,
            content=reply.content,
            created_at=reply.created_at,
        ).model_dump(mode="json")
        for reply, username in rows
    ]


def delete_or_hide_reply(session: Session, reply_id: int, user: User) -> str:
    """回复作者可以删除自己的回复；管理员处理违规内容时隐藏回复。"""

    reply = session.get(ReviewReply, reply_id)
    if reply is None:
        raise BusinessError(404, "回复不存在。")

    if reply.user_id == user.id:
        session.delete(reply)
        session.commit()
        return "deleted"

    if user.role == "admin":
        reply.status = "hidden"
        session.commit()
        return "hidden"

    raise BusinessError(403, "只能删除自己的回复。")
