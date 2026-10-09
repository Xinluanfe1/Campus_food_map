"""店铺相关的响应结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ShopSummary(BaseModel):
    """店铺概要信息，用于个人提交记录与管理员的待审核列表。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    campus_id: str
    name: str
    description: str
    shop_type: str
    photo_url: str | None
    submitted_by: int
    status: str
    map_x: float | None
    map_y: float | None
    latitude: float | None
    longitude: float | None
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime
