"""评价实体：用户对店铺的评分与文字评价。"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class Review(Base):
    """用户店铺评价表。"""

    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),
        CheckConstraint("length(content) BETWEEN 1 AND 2000", name="content_length"),
        CheckConstraint("status IN ('visible', 'hidden')", name="status_allowed"),
        UniqueConstraint("shop_id", "user_id", name="uq_reviews_shop_id_user_id"),
        Index("ix_reviews_shop_id_status", "shop_id", "status"),
        {"comment": "用户店铺评价表"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="评价主键")
    shop_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        comment="被评价店铺 ID（外键：shops.id）",
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="评价用户 ID（外键：users.id）",
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False, comment="评分（1 至 5 的整数）")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="文字评价内容（1 至 2000 个字符）")
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="visible", comment="评价状态：visible（可见）或 hidden（已隐藏）"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, comment="创建时间（UTC）"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, comment="更新时间（UTC）"
    )
