"""后端测试公共夹具：为每个测试创建独立数据库并执行 Alembic 迁移。"""

from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.session import BACKEND_DIR, create_db_engine


def migrate_database(database_url: str) -> None:
    """使用与生产一致的 Alembic 迁移创建数据库结构。"""

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


@pytest.fixture()
def database_url(tmp_path) -> str:
    """返回当前测试专属的数据库地址。"""

    return f"sqlite:///{(tmp_path / 'test.db').as_posix()}"


@pytest.fixture()
def migrated_database_url(database_url: str) -> str:
    """返回已完成迁移的数据库地址。"""

    migrate_database(database_url)
    return database_url


@pytest.fixture()
def engine(migrated_database_url: str) -> Iterator[Engine]:
    """连接已迁移数据库的引擎。"""

    test_engine = create_db_engine(migrated_database_url)
    try:
        yield test_engine
    finally:
        test_engine.dispose()


@pytest.fixture()
def session(engine: Engine) -> Iterator[Session]:
    """数据库会话，测试结束后自动关闭。"""

    with Session(engine) as test_session:
        yield test_session
