"""评分排行榜、店铺搜索与贡献榜（对应开发文档 6.10、6.11 与 7.9）。"""

from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import BusinessError
from app.models import Campus, Review, Shop, User
from app.schemas.ranking import (
    ContributionSummary,
    ContributorItem,
    RankingShopItem,
    SearchShopItem,
)
from app.services.rating_service import RATING_WEIGHT_MIN_REVIEWS

FAR_FUTURE = datetime.max.replace(tzinfo=timezone.utc)


def _campus_average_rating(session: Session, campus_id: str) -> float | None:
    """当前校园全部有效主评价的平均星级（公式中的 C）。"""

    ratings = list(
        session.scalars(
            select(Review.rating)
            .join(Shop, Review.shop_id == Shop.id)
            .where(
                Shop.campus_id == campus_id,
                Shop.status == "approved",
                Review.status == "visible",
            )
        ).all()
    )
    if not ratings:
        return None
    return sum(ratings) / len(ratings)


def _weighted_rating(average_rating: float, review_count: int, campus_average: float | None) -> float:
    """贝叶斯加权评分：S = v/(v+m)·R + m/(v+m)·C。"""

    if campus_average is None:
        return average_rating
    weight = review_count / (review_count + RATING_WEIGHT_MIN_REVIEWS)
    return weight * average_rating + (1 - weight) * campus_average


def list_shop_rankings(
    session: Session,
    campus: Campus,
    shop_type: str,
    sort: str,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    """店铺评分排行榜：只统计有效评价，按未舍入的加权评分排序。"""

    conditions = [Shop.campus_id == campus.campus_id, Shop.status == "approved"]
    if shop_type != "all":
        conditions.append(Shop.shop_type == shop_type)

    rows = session.execute(
        select(Shop, func.avg(Review.rating), func.count(Review.id))
        .join(Review, (Review.shop_id == Shop.id) & (Review.status == "visible"))
        .where(*conditions)
        .group_by(Shop.id)
    ).all()

    campus_average = _campus_average_rating(session, campus.campus_id)
    entries: list[dict] = []
    for shop, average_rating, review_count in rows:
        count = int(review_count)
        if count == 0:
            continue  # 无有效评价的店铺不进入评分排行榜
        average = float(average_rating)
        entries.append(
            {
                "shop": shop,
                "average_rating": average,
                "weighted_rating": _weighted_rating(average, count, campus_average),
                "review_count": count,
            }
        )

    # 排序规则（6.10）：加权评分升/降序 → 有效评价数量从高到低 → 店铺 ID 从小到大。
    # 使用未舍入的加权评分排序，避免舍入误差影响排名。
    entries.sort(
        key=lambda item: (
            item["weighted_rating"] if sort == "asc" else -item["weighted_rating"],
            -item["review_count"],
            item["shop"].id,
        )
    )

    total = len(entries)
    start = (page - 1) * page_size
    page_entries = entries[start : start + page_size]
    items = [
        RankingShopItem(
            rank=start + index + 1,
            shop_id=entry["shop"].id,
            name=entry["shop"].name,
            shop_type=entry["shop"].shop_type,
            average_rating=round(entry["average_rating"], 2),
            weighted_rating=round(entry["weighted_rating"], 2),
            review_count=entry["review_count"],
        ).model_dump(mode="json")
        for index, entry in enumerate(page_entries)
    ]
    return items, total


def search_public_shops(
    session: Session,
    campus: Campus,
    keyword: str,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    """按名称或简介搜索当前校园的公开店铺（大小写不敏感、忽略首尾空格）。"""

    text = keyword.strip()
    if not text:
        raise BusinessError(400, "请输入搜索关键词。")
    if len(text) > 50:
        raise BusinessError(400, "搜索关键词不能超过 50 个字符。")

    escaped = text.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    conditions = (
        Shop.campus_id == campus.campus_id,
        Shop.status == "approved",
        or_(
            func.lower(Shop.name).like(pattern, escape="\\"),
            func.lower(Shop.description).like(pattern, escape="\\"),
        ),
    )

    total = session.scalar(select(func.count()).select_from(Shop).where(*conditions)) or 0
    shops = session.scalars(
        select(Shop)
        .where(*conditions)
        .order_by(Shop.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    shop_ids = [shop.id for shop in shops]
    stats: dict[int, tuple[float, int]] = {}
    if shop_ids:
        stat_rows = session.execute(
            select(Review.shop_id, func.avg(Review.rating), func.count(Review.id))
            .where(Review.shop_id.in_(shop_ids), Review.status == "visible")
            .group_by(Review.shop_id)
        ).all()
        stats = {shop_id: (float(average), int(count)) for shop_id, average, count in stat_rows}

    campus_average = _campus_average_rating(session, campus.campus_id)
    items = []
    for shop in shops:
        average, count = stats.get(shop.id, (None, 0))
        weighted = (
            _weighted_rating(average, count, campus_average) if average is not None else None
        )
        items.append(
            SearchShopItem(
                id=shop.id,
                name=shop.name,
                shop_type=shop.shop_type,
                average_rating=round(average, 2) if average is not None else None,
                weighted_rating=round(weighted, 2) if weighted is not None else None,
                review_count=count,
            ).model_dump(mode="json")
        )

    return items, int(total)


def _contributor_entries(session: Session, campus: Campus) -> list[dict]:
    """按用户统计当前校园审核通过的店铺数量，并按 6.11 的规则排序。"""

    rows = session.execute(
        select(User, Shop.reviewed_at, Shop.created_at)
        .join(Shop, Shop.submitted_by == User.id)
        .where(Shop.campus_id == campus.campus_id, Shop.status == "approved")
        .order_by(Shop.id.asc())
    ).all()

    grouped: dict[int, dict] = {}
    for user, reviewed_at, created_at in rows:
        entry = grouped.setdefault(user.id, {"user": user, "times": []})
        entry["times"].append(reviewed_at or created_at)

    entries: list[dict] = []
    for entry in grouped.values():
        times = sorted(item for item in entry["times"] if item is not None)
        count = len(entry["times"])
        # 达到当前贡献数量的时间：第 count 家通过审核的时间
        reached_at = times[count - 1] if len(times) >= count and count > 0 else None
        entries.append({"user": entry["user"], "count": count, "reached_at": reached_at})

    entries.sort(
        key=lambda item: (
            -item["count"],
            item["reached_at"] or FAR_FUTURE,
            item["user"].username,
        )
    )
    return entries


def list_contributor_rankings(
    session: Session,
    campus: Campus,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    """贡献榜：只统计审核通过的店铺，同数量按更早达到的时间优先。"""

    entries = _contributor_entries(session, campus)
    total = len(entries)
    start = (page - 1) * page_size
    items = [
        ContributorItem(
            rank=start + index + 1,
            user_id=entry["user"].id,
            username=entry["user"].username,
            approved_shop_count=entry["count"],
            first_reached_at=entry["reached_at"],
        ).model_dump(mode="json")
        for index, entry in enumerate(entries[start : start + page_size])
    ]
    return items, total


def user_contribution(session: Session, user: User, campus_id: str | None) -> dict:
    """当前用户的贡献统计：指定校园时同时返回该校园贡献榜中的排名。"""

    conditions = [Shop.submitted_by == user.id, Shop.status == "approved"]
    if campus_id is not None:
        conditions.append(Shop.campus_id == campus_id)

    count = int(session.scalar(select(func.count()).select_from(Shop).where(*conditions)) or 0)

    rank: int | None = None
    if campus_id is not None and count > 0:
        campus = session.get(Campus, campus_id)
        if campus is not None:
            entries = _contributor_entries(session, campus)
            for index, entry in enumerate(entries):
                if entry["user"].id == user.id:
                    rank = index + 1
                    break

    return ContributionSummary(
        campus_id=campus_id,
        approved_shop_count=count,
        rank=rank,
    ).model_dump(mode="json")
