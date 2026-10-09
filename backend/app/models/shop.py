"""店铺实体：校园美食店铺与摊贩。"""

from datetime import datetime

from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime, utc_now


class Shop(Base):
    """校园美食店铺表。"""

    __tablename__ = "shops"
    __table_args__ = (
        CheckConstraint("shop_type IN ('shop', 'vendor')", name="shop_type_allowed"),
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="status_allowed"),
        CheckConstraint("length(name) >= 1", name="name_not_empty"),
        CheckConstraint("length(description) >= 1", name="description_not_empty"),
        CheckConstraint("map_x IS NULL OR (map_x >= 0 AND map_x <= 1)", name="map_x_range"),
        CheckConstraint("map_y IS NULL OR (map_y >= 0 AND map_y <= 1)", name="map_y_range"),
        CheckConstraint("latitude IS NULL OR (latitude >= -90 AND latitude <= 90)", name="latitude_range"),
        CheckConstraint("longitude IS NULL OR (longitude >= -180 AND longitude <= 180)", name="longitude_range"),
        CheckConstraint(
            "(map_x IS NULL AND map_y IS NULL) OR (map_x IS NOT NULL AND map_y IS NOT NULL)",
            name="map_coordinates_paired",
        ),
        CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL) OR (latitude IS NOT NULL AND longitude IS NOT NULL)",
            name="geo_coordinates_paired",
        ),
        CheckConstraint("map_x IS NOT NULL OR latitude IS NOT NULL", name="location_required"),
        CheckConstraint(
            "status <> 'rejected' OR (rejection_reason IS NOT NULL AND length(rejection_reason) >= 1)",
            name="rejection_reason_required",
        ),
        Index("ix_shops_campus_id_status", "campus_id", "status"),
        Index("ix_shops_submitted_by", "submitted_by"),
        {"comment": "校园美食店铺表"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="店铺主键")
    campus_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("campuses.campus_id", ondelete="RESTRICT"),
        nullable=False,
        comment="所属校园标识（外键：campuses.campus_id）",
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="店铺名称（必填）")
    description: Mapped[str] = mapped_column(Text, nullable=False, comment="店铺简介（必填）")
    shop_type: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="店铺类型：shop（商铺）或 vendor（摊贩）"
    )
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="封面照片路径，可为空")
    submitted_by: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="提交用户 ID（外键：users.id）",
    )
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="pending", comment="审核状态：pending、approved 或 rejected"
    )
    map_x: Mapped[float | None] = mapped_column(Float, nullable=True, comment="图片模式横向比例坐标（0 至 1）")
    map_y: Mapped[float | None] = mapped_column(Float, nullable=True, comment="图片模式纵向比例坐标（0 至 1）")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True, comment="真实地图纬度（-90 至 90）")
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True, comment="真实地图经度（-180 至 180）")
    reviewed_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="审核管理员 ID（外键：users.id，可为空）",
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime, nullable=True, comment="审核时间（UTC，可为空）"
    )
    rejection_reason: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="拒绝原因（被拒绝时必填）"
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, comment="创建时间（UTC）"
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now, comment="更新时间（UTC）"
    )
