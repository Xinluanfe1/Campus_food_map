"""用户实体：系统账号与角色。"""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UTCDateTime, utc_now


class User(Base):
    """系统用户表。"""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin')", name="role_allowed"),
        CheckConstraint("length(username) BETWEEN 2 AND 20", name="username_length"),
        {"comment": "系统用户表"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="用户主键")
    username: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True, comment="用户名（唯一，2 至 20 个字符）"
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="密码哈希（Argon2id，不保存明文密码）"
    )
    role: Mapped[str] = mapped_column(
        String(10), nullable=False, default="user", comment="用户角色：user（普通用户）或 admin（管理员）"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="账号是否启用")
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, comment="创建时间（UTC）"
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utc_now, onupdate=utc_now, comment="更新时间（UTC）"
    )
