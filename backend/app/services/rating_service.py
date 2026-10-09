"""评分统计计算（对应开发文档 6.9 与 6.10）。"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Review, ReviewReaction, Shop

# 开发文档 6.10：最少评价数的平滑参数 m，初始固定为 5。
RATING_WEIGHT_MIN_REVIEWS = 5


def _average(values: list[int]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def shop_rating_summary(session: Session, shop: Shop) -> dict[str, float | int | None]:
    """计算单家店铺的评分统计。

    返回未舍入的原始数值：接口展示时可以保留两位小数，
    但排行榜排序必须使用原始数值，避免舍入误差影响排名。
    """

    shop_ratings = list(
        session.scalars(
            select(Review.rating).where(
                Review.shop_id == shop.id,
                Review.status == "visible",
            )
        ).all()
    )
    review_count = len(shop_ratings)
    average_rating = _average(shop_ratings)

    # 当前校园全部有效主评价的平均星级（C）
    campus_ratings = list(
        session.scalars(
            select(Review.rating)
            .join(Shop, Review.shop_id == Shop.id)
            .where(
                Shop.campus_id == shop.campus_id,
                Shop.status == "approved",
                Review.status == "visible",
            )
        ).all()
    )
    campus_average = _average(campus_ratings)

    weighted_rating: float | None = None
    if average_rating is not None and campus_average is not None:
        weight = review_count / (review_count + RATING_WEIGHT_MIN_REVIEWS)
        weighted_rating = weight * average_rating + (1 - weight) * campus_average

    like_count = session.scalar(
        select(func.count())
        .select_from(ReviewReaction)
        .join(Review, ReviewReaction.review_id == Review.id)
        .where(
            Review.shop_id == shop.id,
            Review.status == "visible",
            ReviewReaction.reaction_type == "like",
        )
    ) or 0
    dislike_count = session.scalar(
        select(func.count())
        .select_from(ReviewReaction)
        .join(Review, ReviewReaction.review_id == Review.id)
        .where(
            Review.shop_id == shop.id,
            Review.status == "visible",
            ReviewReaction.reaction_type == "dislike",
        )
    ) or 0

    return {
        "average_rating": average_rating,
        "weighted_rating": weighted_rating,
        "review_count": review_count,
        "like_count": int(like_count),
        "dislike_count": int(dislike_count),
    }
