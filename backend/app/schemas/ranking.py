"""排行榜、搜索与贡献榜的响应结构。"""

from datetime import datetime

from pydantic import BaseModel


class RankingShopItem(BaseModel):
    """评分排行榜列表项（对应开发文档 6.10）。"""

    rank: int
    shop_id: int
    name: str
    shop_type: str
    average_rating: float
    weighted_rating: float
    review_count: int


class SearchShopItem(BaseModel):
    """搜索结果列表项：只包含公开店铺的概要信息。"""

    id: int
    name: str
    shop_type: str
    average_rating: float | None
    weighted_rating: float | None
    review_count: int


class ContributorItem(BaseModel):
    """贡献榜列表项（对应开发文档 6.11）。"""

    rank: int
    user_id: int
    username: str
    approved_shop_count: int
    first_reached_at: datetime | None


class ContributionSummary(BaseModel):
    """当前用户的贡献统计。"""

    campus_id: str | None
    approved_shop_count: int
    rank: int | None
