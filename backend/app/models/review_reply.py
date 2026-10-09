"""回复实体：对评价的一级回复。"""

from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime, utc_now


class ReviewReply(Base):
    """评价回复表。"""

    __tablename__ = "review_replies"
    __table_args__ = (
        CheckConstraint("length(content) BETWEEN 1 AND 1000", name="content_length"),
        CheckConstraint("status IN ('visible', 'hidden')", name="status_allowed"),
        Index("ix_review_replies_review_id_status", "review_id", "status"),
        {"comment": "评价回复表"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="回复主键")
    review_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属主评价 ID（外键：reviews.id）",
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="回复者用户 ID（外键：users.id）",
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="回复文本（1 至 1000 个字符）")
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="visible", comment="回复状态：visible（可见）或 hidden（已隐藏）"
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, comment="创建时间（UTC）"
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now, comment="更新时间（UTC）"
    )
