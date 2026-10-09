"""数据库连接、会话管理与存储目录解析。"""

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# backend 目录：把配置中的相对路径解析为稳定路径时使用。
BACKEND_DIR = Path(__file__).resolve().parents[2]


def resolve_sqlite_url(url: str) -> str:
    """把 SQLite 相对路径解析为基于 backend 目录的绝对路径 URL。"""

    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return url

    raw_path = url[len(prefix):]
    if raw_path.startswith("/") or raw_path[1:3] == ":/":
        return url

    absolute_path = (BACKEND_DIR / raw_path).resolve()
    return prefix + absolute_path.as_posix()


def resolve_storage_dir(configured_path: str) -> Path:
    """把配置中的存储目录解析为绝对路径。"""

    path = Path(configured_path)
    if path.is_absolute():
        return path
    return (BACKEND_DIR / path).resolve()


def ensure_storage_directories() -> list[Path]:
    """确保店铺照片与地图目录存在，返回处理过的目录列表。"""

    directories = [
        resolve_storage_dir(settings.upload_dir),
        resolve_storage_dir(settings.map_dir),
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    return directories


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    """SQLite 默认不启用外键，这里在每次建立连接时显式开启。"""

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_db_engine(database_url: str | None = None) -> Engine:
    """创建数据库引擎，并统一启用 SQLite 外键约束。"""

    url = resolve_sqlite_url(database_url or settings.database_url)
    engine = create_engine(url, connect_args={"check_same_thread": False})
    event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI 依赖：提供一个请求级别的数据库会话。"""

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
