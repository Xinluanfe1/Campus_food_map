"""举报实体：评价举报与管理员处理记录。"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class Report(Base):
    """评价举报及处理记录表。"""

    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'resolved', 'dismissed')", name="status_allowed"),
        CheckConstraint("length(reason) >= 1", name="reason_not_empty"),
        Index("ix_reports_status", "status"),
        Index(
            "uq_reports_pending_review_id_reported_by",
            "review_id",
            "reported_by",
            unique=True,
            sqlite_where=text("status = 'pending'"),
            postgresql_where=text("status = 'pending'"),
        ),
        {"comment": "评价举报及处理记录表"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="举报主键")
    review_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        comment="被举报评价 ID（外键：reviews.id）",
    )
    reported_by: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="举报用户 ID（外键：users.id）",
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False, comment="举报理由（必填）")
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="pending", comment="处理状态：pending、resolved 或 dismissed"
    )
    handled_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="处理管理员 ID（外键：users.id，可为空）",
    )
    handled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="处理时间（UTC，可为空）"
    )
    handling_note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="处理备注，可为空")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, comment="举报时间（UTC）"
    )
