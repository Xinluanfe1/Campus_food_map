"""校园实体：管理校园基本信息与地图配置。"""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class Campus(Base):
    """校园及其地图配置表。"""

    __tablename__ = "campuses"
    __table_args__ = (
        CheckConstraint("map_type IN ('image', 'real')", name="map_type_allowed"),
        CheckConstraint(
            "map_type <> 'image' OR (map_asset_url IS NOT NULL AND image_width IS NOT NULL "
            "AND image_height IS NOT NULL AND default_map_x IS NOT NULL AND default_map_y IS NOT NULL)",
            name="image_config_required",
        ),
        CheckConstraint(
            "map_type <> 'real' OR (tile_url_template IS NOT NULL AND map_attribution IS NOT NULL "
            "AND default_latitude IS NOT NULL AND default_longitude IS NOT NULL)",
            name="real_config_required",
        ),
        CheckConstraint(
            "default_map_x IS NULL OR (default_map_x >= 0 AND default_map_x <= 1)",
            name="default_map_x_range",
        ),
        CheckConstraint(
            "default_map_y IS NULL OR (default_map_y >= 0 AND default_map_y <= 1)",
            name="default_map_y_range",
        ),
        CheckConstraint(
            "default_latitude IS NULL OR (default_latitude >= -90 AND default_latitude <= 90)",
            name="default_latitude_range",
        ),
        CheckConstraint(
            "default_longitude IS NULL OR (default_longitude >= -180 AND default_longitude <= 180)",
            name="default_longitude_range",
        ),
        CheckConstraint("default_zoom > 0", name="default_zoom_positive"),
        {"comment": "校园及其地图配置表"},
    )

    campus_id: Mapped[str] = mapped_column(
        String(50), primary_key=True, comment="校园唯一标识（稳定字符串，主键）"
    )
    campus_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="校园名称")
    map_type: Mapped[str] = mapped_column(
        String(10), nullable=False, default="image", comment="地图类型：image（图片底图）或 real（真实地图）"
    )
    map_asset_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="图片底图资源路径，真实地图模式可为空"
    )
    tile_url_template: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="真实地图瓦片地址模板，图片模式可为空"
    )
    map_attribution: Mapped[str | None] = mapped_column(
        String(300), nullable=True, comment="地图署名文本，真实地图模式必填"
    )
    allow_off_campus: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否允许展示校园范围以外的店铺"
    )
    image_width: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="图片底图宽度（像素）")
    image_height: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="图片底图高度（像素）")
    default_map_x: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="图片底图默认中心横向比例（0 至 1）"
    )
    default_map_y: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="图片底图默认中心纵向比例（0 至 1）"
    )
    default_latitude: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="真实地图默认中心纬度（-90 至 90）"
    )
    default_longitude: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="真实地图默认中心经度（-180 至 180）"
    )
    default_zoom: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, comment="默认缩放级别")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否允许正常访问")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, comment="创建时间（UTC）"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, comment="更新时间（UTC）"
    )
