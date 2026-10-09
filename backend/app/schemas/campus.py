"""校园配置与地图点位的请求、响应结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAP_TYPES = {"image", "real"}
MAP_TYPE_MESSAGE = "地图类型只允许 image（图片底图）或 real（真实地图）。"
MAP_PROVIDERS = {"tiles", "baidu"}
MAP_PROVIDER_MESSAGE = "真实地图提供方只允许 tiles（瓦片地图）或 baidu（百度 JSAPI）。"


def _validate_map_fields(model: BaseModel) -> None:
    """校验地图配置的必填项与取值范围。"""

    if model.map_type not in MAP_TYPES:
        raise ValueError(MAP_TYPE_MESSAGE)
    if model.map_provider not in MAP_PROVIDERS:
        raise ValueError(MAP_PROVIDER_MESSAGE)
    if model.map_type == "image" and model.map_provider != "tiles":
        raise ValueError("图片底图模式只能使用 tiles 提供方。")
    if model.default_zoom <= 0:
        raise ValueError("默认缩放级别必须大于 0。")
    if model.boundary_radius_meters is not None and model.boundary_radius_meters <= 0:
        raise ValueError("校园范围半径必须大于 0。")

    if model.default_map_x is not None and not 0 <= model.default_map_x <= 1:
        raise ValueError("图片中心横向比例必须在 0 至 1 之间。")
    if model.default_map_y is not None and not 0 <= model.default_map_y <= 1:
        raise ValueError("图片中心纵向比例必须在 0 至 1 之间。")
    if model.default_latitude is not None and not -90 <= model.default_latitude <= 90:
        raise ValueError("默认纬度必须在 -90 至 90 之间。")
    if model.default_longitude is not None and not -180 <= model.default_longitude <= 180:
        raise ValueError("默认经度必须在 -180 至 180 之间。")

    if model.map_type == "image":
        if (
            not model.map_asset_url
            or model.image_width is None
            or model.image_height is None
            or model.default_map_x is None
            or model.default_map_y is None
        ):
            raise ValueError("图片底图模式必须提供底图地址、图片宽高和默认中心点。")
        if model.image_width <= 0 or model.image_height <= 0:
            raise ValueError("图片宽高必须大于 0。")
    else:
        if (
            not model.tile_url_template
            or not model.map_attribution
            or model.default_latitude is None
            or model.default_longitude is None
        ):
            raise ValueError("真实地图模式必须提供瓦片地址模板、署名和默认经纬度中心。")


class CampusMapFields(BaseModel):
    """校园地图配置的公共字段。"""

    map_type: str = Field(..., description="地图类型：image 或 real")
    map_provider: str = Field("tiles", description="真实地图提供方：tiles 或 baidu")
    map_asset_url: str | None = Field(None, max_length=500, description="图片底图资源路径")
    tile_url_template: str | None = Field(None, max_length=500, description="真实地图瓦片地址模板")
    map_attribution: str | None = Field(None, max_length=300, description="地图署名文本")
    allow_off_campus: bool = Field(False, description="是否允许展示校园范围以外的店铺")
    image_width: int | None = Field(None, description="图片底图宽度（像素）")
    image_height: int | None = Field(None, description="图片底图高度（像素）")
    default_map_x: float | None = Field(None, description="图片底图默认中心横向比例")
    default_map_y: float | None = Field(None, description="图片底图默认中心纵向比例")
    default_latitude: float | None = Field(None, description="真实地图默认中心纬度")
    default_longitude: float | None = Field(None, description="真实地图默认中心经度")
    default_zoom: float = Field(1, description="默认缩放级别")
    boundary_radius_meters: float | None = Field(
        None, description="真实地图校园范围半径（米），为空时后端不做范围过滤"
    )


class CampusCreateRequest(CampusMapFields):
    """新增校园配置请求（管理员）。"""

    model_config = ConfigDict(extra="forbid")

    campus_id: str = Field(..., min_length=1, max_length=50, description="校园唯一标识")
    campus_name: str = Field(..., min_length=1, max_length=100, description="校园名称")
    is_active: bool = Field(True, description="是否允许正常访问")

    @field_validator("campus_id")
    @classmethod
    def validate_campus_id(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized.replace("_", "").replace("-", "").isalnum():
            raise ValueError("校园标识只能包含英文字母、数字、下划线和连字符。")
        return normalized

    @field_validator("campus_name")
    @classmethod
    def validate_campus_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("校园名称不能为空。")
        return normalized

    @model_validator(mode="after")
    def validate_map_config(self) -> "CampusCreateRequest":
        _validate_map_fields(self)
        return self


class CampusMapUpdateRequest(CampusMapFields):
    """更新校园地图配置请求（管理员，完整替换地图配置）。"""

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_map_config(self) -> "CampusMapUpdateRequest":
        _validate_map_fields(self)
        return self


class CampusPatchRequest(BaseModel):
    """修改校园基本信息与展示状态请求（管理员）。"""

    model_config = ConfigDict(extra="forbid")

    campus_name: str | None = Field(None, min_length=1, max_length=100)
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "CampusPatchRequest":
        if self.campus_name is None and self.is_active is None:
            raise ValueError("请至少提供校园名称或展示状态中的一项。")
        return self


class CampusSummary(BaseModel):
    """校园列表项（公开）。"""

    model_config = ConfigDict(from_attributes=True)

    campus_id: str
    campus_name: str
    map_type: str
    is_active: bool


class CampusDetail(BaseModel):
    """校园详情与公开地图配置。"""

    model_config = ConfigDict(from_attributes=True)

    campus_id: str
    campus_name: str
    map_type: str
    map_provider: str
    map_asset_url: str | None
    tile_url_template: str | None
    map_attribution: str | None
    allow_off_campus: bool
    image_width: int | None
    image_height: int | None
    default_map_x: float | None
    default_map_y: float | None
    default_latitude: float | None
    default_longitude: float | None
    default_zoom: float
    boundary_radius_meters: float | None
    boundary_radius_meters: float | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CampusMapConfig(BaseModel):
    """地图渲染所需的公开配置。"""

    model_config = ConfigDict(from_attributes=True)

    campus_id: str
    campus_name: str
    map_type: str
    map_provider: str
    map_asset_url: str | None
    tile_url_template: str | None
    map_attribution: str | None
    allow_off_campus: bool
    image_width: int | None
    image_height: int | None
    default_map_x: float | None
    default_map_y: float | None
    default_latitude: float | None
    default_longitude: float | None
    default_zoom: float
    baidu_map_ak: str | None = None


class ShopPoint(BaseModel):
    """地图点位的最小字段，不包含店铺简介、照片与评价等详情。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    shop_type: str
    map_x: float | None = None
    map_y: float | None = None
    latitude: float | None = None
    longitude: float | None = None
