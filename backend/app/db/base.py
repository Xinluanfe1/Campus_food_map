"""SQLAlchemy 基类、统一命名约定与时间工具。"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator

# 统一约束与索引命名，便于迁移脚本定位问题并支持未来的数据库迁移。
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """所有数据库模型的公共基类。"""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def utc_now() -> datetime:
    """返回当前 UTC 时间（带时区），数据库时间字段统一使用 UTC 保存。"""

    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """UTC 时间类型：写入时转换为 UTC，读取时补上 UTC 时区信息。

    SQLite 不保存时区信息，如果直接使用 DateTime(timezone=True)，
    读出的时间会丢失时区标识，接口返回的 ISO 8601 文本就无法体现 UTC。
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, _dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, _dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
