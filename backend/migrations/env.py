"""Alembic 迁移环境：读取项目配置、模型元数据与数据库地址。"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401  导入全部模型，保证元数据完整
from app.core.config import settings
from app.db.base import Base
from app.db.session import resolve_sqlite_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    """数据库地址优先取命令行传入值，其次取项目配置。"""

    configured_url = config.get_main_option("sqlalchemy.url")
    if configured_url:
        return configured_url
    return settings.database_url


def run_migrations_offline() -> None:
    """离线模式：只生成 SQL，不建立数据库连接。"""

    context.configure(
        url=resolve_sqlite_url(get_database_url()),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：连接数据库并执行迁移。"""

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = resolve_sqlite_url(get_database_url())

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
