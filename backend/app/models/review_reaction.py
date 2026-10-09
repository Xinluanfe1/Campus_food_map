"""评价互动实体：点赞与点踩。"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class ReviewReaction(Base):
    """评价点赞与点踩表。"""

    __tablename__ = "review_reactions"
    __table_args__ = (
        CheckConstraint("reaction_type IN ('like', 'dislike')", name="reaction_type_allowed"),
        UniqueConstraint("review_id", "user_id", name="uq_review_reactions_review_id_user_id"),
        Index("ix_review_reactions_user_id", "user_id"),
        {"comment": "评价点赞与点踩表"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="互动主键")
    review_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("reviews.id", ondelete="CASCADE"),
        nullable=False,
        comment="目标评价 ID（外键：reviews.id）",
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="执行互动的用户 ID（外键：users.id）",
    )
    reaction_type: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="互动类型：like（点赞）或 dislike（点踩）"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, comment="创建时间（UTC）"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now, comment="更新时间（UTC）"
    )
