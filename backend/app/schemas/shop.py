"""店铺相关的请求与响应结构。"""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SHOP_TYPES = {"shop", "vendor"}
SHOP_TYPE_MESSAGE = "店铺类型只允许 shop（商铺）或 vendor（摊贩）。"
PHOTO_URL_PATTERN = re.compile(r"^/media/shop_photos/[A-Za-z0-9][A-Za-z0-9._-]*$")


class ShopBaseFields(BaseModel):
    """店铺字段与公共校验规则（提交与修改共用）。"""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, max_length=100, description="店铺名称")
    description: str | None = Field(None, max_length=2000, description="店铺简介")
    shop_type: str | None = Field(None, description="店铺类型：shop 或 vendor")
    photo_url: str | None = Field(None, max_length=500, description="封面照片路径")
    map_x: float | None = Field(None, description="图片模式横向比例坐标")
    map_y: float | None = Field(None, description="图片模式纵向比例坐标")
    latitude: float | None = Field(None, description="真实地图纬度")
    longitude: float | None = Field(None, description="真实地图经度")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not text:
            raise ValueError("店铺名称不能为空。")
        return text

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not text:
            raise ValueError("店铺简介不能为空。")
        return text

    @field_validator("shop_type")
    @classmethod
    def validate_shop_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in SHOP_TYPES:
            raise ValueError(SHOP_TYPE_MESSAGE)
        return value

    @field_validator("photo_url")
    @classmethod
    def validate_photo_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not PHOTO_URL_PATTERN.match(value):
            raise ValueError("照片路径不合法，请通过照片上传接口获取。")
        return value

    @field_validator("map_x", "map_y")
    @classmethod
    def validate_map_range(cls, value: float | None) -> float | None:
        if value is not None and not 0 <= value <= 1:
            raise ValueError("图片坐标必须在 0 至 1 之间。")
        return value

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: float | None) -> float | None:
        if value is not None and not -90 <= value <= 90:
            raise ValueError("纬度必须在 -90 至 90 之间。")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: float | None) -> float | None:
        if value is not None and not -180 <= value <= 180:
            raise ValueError("经度必须在 -180 至 180 之间。")
        return value

    @model_validator(mode="after")
    def validate_coordinate_pairs(self) -> "ShopBaseFields":
        if (self.map_x is None) != (self.map_y is None):
            raise ValueError("图片坐标必须同时提供 map_x 和 map_y。")
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("经纬度必须同时提供 latitude 和 longitude。")
        return self


class ShopSubmitRequest(ShopBaseFields):
    """提交店铺请求：名称、简介、类型与位置均为必填。"""

    name: str = Field(..., max_length=100, description="店铺名称，必填")
    description: str = Field(..., max_length=2000, description="店铺简介，必填")
    shop_type: str = Field(..., description="店铺类型，必填")

    @model_validator(mode="after")
    def validate_location_required(self) -> "ShopSubmitRequest":
        if self.map_x is None and self.latitude is None:
            raise ValueError("必须提供店铺位置（图片坐标或经纬度）。")
        return self


class ShopUpdateRequest(ShopBaseFields):
    """修改店铺请求：至少提供一个字段，核心信息变化后重新进入待审核。"""

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "ShopUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("请至少提供一个需要修改的字段。")
        return self


class ShopRejectRequest(BaseModel):
    """拒绝店铺请求：必须填写拒绝原因。"""

    model_config = ConfigDict(extra="forbid")

    reason: str = Field(..., max_length=500, description="拒绝原因，必填")

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("请填写拒绝原因。")
        return text


class RatingSummary(BaseModel):
    """店铺评分统计（对应开发文档 6.9）。"""

    average_rating: float | None
    weighted_rating: float | None
    review_count: int
    like_count: int
    dislike_count: int


class ShopDetailData(BaseModel):
    """店铺详情：只包含当前校园坐标体系对应的坐标字段。"""

    id: int
    campus_id: str
    name: str
    description: str
    shop_type: str
    photo_url: str | None
    status: str
    map_x: float | None = None
    map_y: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    created_at: datetime
    updated_at: datetime
    rating: RatingSummary


class PendingShopItem(BaseModel):
    """待审核店铺列表项（管理员）。"""

    id: int
    campus_id: str
    name: str
    description: str
    shop_type: str
    photo_url: str | None
    submitted_by: int
    submitter_username: str
    status: str
    map_x: float | None = None
    map_y: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    created_at: datetime
    updated_at: datetime


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
