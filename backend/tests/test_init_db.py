"""初始化脚本测试：示例数据完整性与重复执行保护。"""

from pwdlib import PasswordHash
from sqlalchemy import func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db import seed_data
from app.db.init_db import init_database
from app.db.session import create_db_engine
from app.models import Campus, Report, Review, ReviewReaction, ReviewReply, Shop, User

TEST_ADMIN_PASSWORD = "测试管理员密码-A1"


def count_records(engine: Engine, model) -> int:  # noqa: ANN001
    """统计指定表的记录数量。"""

    with Session(engine) as session:
        return session.scalar(select(func.count()).select_from(model)) or 0


def test_init_database_writes_expected_demo_data(tmp_path) -> None:
    """验收标准 1、9、10：初始化脚本创建数据库并写入完整示例数据。"""

    database_url = f"sqlite:///{(tmp_path / 'init.db').as_posix()}"
    result = init_database(database_url=database_url, admin_password=TEST_ADMIN_PASSWORD)

    assert result["inserted"] == 43
    assert result["admin_password_generated"] is False

    engine = create_db_engine(database_url)
    try:
        assert count_records(engine, Campus) == 1
        assert count_records(engine, User) == 7
        assert count_records(engine, Shop) == 10
        assert count_records(engine, Review) == 16
        assert count_records(engine, ReviewReaction) == 5
        assert count_records(engine, ReviewReply) == 2
        assert count_records(engine, Report) == 2

        with Session(engine) as session:
            version = session.scalar(text("SELECT version_num FROM alembic_version"))
            assert version == "20261009_0002"

            admin = session.scalar(select(User).where(User.role == "admin"))
            assert admin is not None
            assert admin.username == "admin"
            assert PasswordHash.recommended().verify(TEST_ADMIN_PASSWORD, admin.password_hash)

            demo_user = session.get(User, 1)
            assert PasswordHash.recommended().verify(seed_data.DEMO_USER_PASSWORD, demo_user.password_hash)

            pending_shop = session.get(Shop, 110)
            assert pending_shop.status == "pending"

            # 示例奶茶店（105）故意没有评价，用于测试“无评价店铺不参与评分排行榜”。
            review_count_105 = session.scalar(
                select(func.count()).select_from(Review).where(Review.shop_id == 105)
            )
            assert review_count_105 == 0
    finally:
        engine.dispose()


def test_init_database_is_idempotent(tmp_path) -> None:
    """验收标准 4：重复执行初始化不会重复插入数据。"""

    database_url = f"sqlite:///{(tmp_path / 'init.db').as_posix()}"
    first = init_database(database_url=database_url, admin_password=TEST_ADMIN_PASSWORD)
    second = init_database(database_url=database_url, admin_password=TEST_ADMIN_PASSWORD)

    assert first["inserted"] == 43
    assert second["inserted"] == 0
    assert second["skipped"] == 43

    engine = create_db_engine(database_url)
    try:
        assert count_records(engine, Campus) == 1
        assert count_records(engine, User) == 7
        assert count_records(engine, Shop) == 10
        assert count_records(engine, Review) == 16
        assert count_records(engine, ReviewReaction) == 5
        assert count_records(engine, ReviewReply) == 2
        assert count_records(engine, Report) == 2
    finally:
        engine.dispose()


def test_init_database_generates_random_admin_password(tmp_path) -> None:
    """未提供管理员密码时必须生成随机密码，而不是使用演示密码。"""

    database_url = f"sqlite:///{(tmp_path / 'init.db').as_posix()}"
    result = init_database(database_url=database_url, admin_password=None)

    assert result["admin_password_generated"] is True
    generated_password = str(result["admin_password"])
    assert generated_password
    assert generated_password != seed_data.DEMO_USER_PASSWORD

    engine = create_db_engine(database_url)
    try:
        with Session(engine) as session:
            admin = session.scalar(select(User).where(User.role == "admin"))
            assert PasswordHash.recommended().verify(generated_password, admin.password_hash)
    finally:
        engine.dispose()
