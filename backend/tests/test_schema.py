"""数据库结构与约束测试：对应第二步验收标准。"""

from pathlib import Path

import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Campus, Report, Review, ReviewReaction, ReviewReply, Shop, User

EXPECTED_TABLES = {
    "campuses",
    "users",
    "shops",
    "reviews",
    "review_reactions",
    "review_replies",
    "reports",
}

DICTIONARY_PATH = Path(__file__).resolve().parents[2] / "docs" / "数据库字典.md"


def add_campus(session: Session, campus_id: str = "swjtu_xipu") -> Campus:
    """写入一个符合校验规则的校园记录。"""

    campus = Campus(
        campus_id=campus_id,
        campus_name="测试校园",
        map_type="image",
        map_asset_url="/assets/maps/test.png",
        image_width=1000,
        image_height=800,
        default_map_x=0.5,
        default_map_y=0.5,
        default_zoom=1,
        is_active=True,
    )
    session.add(campus)
    session.flush()
    return campus


def add_user(session: Session, user_id: int = 1, username: str = "测试用户", role: str = "user") -> User:
    """写入一个用户记录。"""

    user = User(id=user_id, username=username, password_hash="测试密码哈希", role=role, is_active=True)
    session.add(user)
    session.flush()
    return user


def add_shop(session: Session, shop_id: int = 101, **overrides) -> Shop:
    """写入一个通过校验的店铺记录。"""

    values = {
        "id": shop_id,
        "campus_id": "swjtu_xipu",
        "name": "测试店铺",
        "description": "用于测试的店铺简介。",
        "shop_type": "shop",
        "submitted_by": 1,
        "status": "approved",
        "map_x": 0.5,
        "map_y": 0.5,
        "reviewed_by": 2,
    }
    values.update(overrides)
    shop = Shop(**values)
    session.add(shop)
    session.flush()
    return shop


def add_review(session: Session, review_id: int = 1001, shop_id: int = 101, user_id: int = 1) -> Review:
    """写入一条评价记录。"""

    review = Review(id=review_id, shop_id=shop_id, user_id=user_id, rating=5, content="测试评价内容。", status="visible")
    session.add(review)
    session.flush()
    return review


def test_all_required_tables_created(engine: Engine) -> None:
    """验收标准 1、2：数据库可以创建，并包含全部规定的表。"""

    table_names = set(inspect(engine).get_table_names())
    assert EXPECTED_TABLES <= table_names
    assert "alembic_version" in table_names


def test_alembic_revision_is_applied(engine: Engine) -> None:
    """数据库结构必须由 Alembic 迁移创建，而不是启动时自动建表。"""

    with engine.connect() as connection:
        version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert version == "20261009_0003"


def test_sqlite_foreign_keys_enabled(engine: Engine) -> None:
    """数据库连接必须启用 SQLite 外键约束。"""

    with engine.connect() as connection:
        pragma_value = connection.execute(text("PRAGMA foreign_keys")).scalar_one()
    assert pragma_value == 1


def test_table_and_column_comments_are_chinese() -> None:
    """验收标准 3：所有表与字段都有中文说明（保存在模型 comment 属性中）。"""

    for table_name in EXPECTED_TABLES:
        table = Base.metadata.tables[table_name]
        assert table.comment, f"表 {table_name} 缺少中文说明"
        for column in table.columns:
            assert column.comment, f"字段 {table_name}.{column.name} 缺少中文说明"


def test_data_dictionary_covers_all_tables_and_fields() -> None:
    """中文数据字典必须覆盖全部表与字段。"""

    content = DICTIONARY_PATH.read_text(encoding="utf-8")
    for table_name in EXPECTED_TABLES:
        table = Base.metadata.tables[table_name]
        assert f"`{table_name}`：" in content, f"数据字典缺少表 {table_name}"
        for column in table.columns:
            assert f"| `{column.name}` |" in content, f"数据字典缺少字段 {table_name}.{column.name}"


def test_username_unique_constraint(session: Session) -> None:
    """验收标准 5：用户名唯一约束生效。"""

    add_user(session, user_id=1, username="重复用户名")
    session.commit()

    session.add(User(username="重复用户名", password_hash="另一份哈希", role="user", is_active=True))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_review_unique_constraint(session: Session) -> None:
    """验收标准 6：同一用户对同一家店铺只能有一条主评价。"""

    add_campus(session)
    add_user(session, user_id=1)
    add_user(session, user_id=2, username="审核管理员", role="admin")
    add_shop(session)
    session.commit()

    add_review(session, review_id=1001)
    session.commit()

    session.add(Review(shop_id=101, user_id=1, rating=4, content="重复评价。", status="visible"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_role_check_constraint(session: Session) -> None:
    """验收标准 8：角色只允许 user 与 admin，不能写入其他角色。"""

    session.add(User(username="非法角色", password_hash="测试哈希", role="superadmin", is_active=True))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_shop_foreign_keys_enforced(session: Session) -> None:
    """验收标准 7：店铺外键必须指向真实存在的校园与用户。"""

    add_user(session, user_id=1)
    session.commit()

    session.add(
        Shop(
            id=201,
            campus_id="不存在的校园",
            name="异常店铺",
            description="用于测试外键。",
            shop_type="shop",
            submitted_by=1,
            status="approved",
            map_x=0.5,
            map_y=0.5,
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_review_and_reaction_foreign_keys_enforced(session: Session) -> None:
    """验收标准 7：评价与互动外键有效，不能指向不存在的店铺或评价。"""

    add_user(session, user_id=1)
    session.commit()

    session.add(Review(shop_id=999, user_id=1, rating=5, content="不存在的店铺。", status="visible"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    session.add(ReviewReaction(review_id=999, user_id=1, reaction_type="like"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_shop_check_constraints(session: Session) -> None:
    """店铺类型、坐标范围与拒绝原因等校验规则必须生效。"""

    add_campus(session)
    add_user(session, user_id=1)
    add_user(session, user_id=2, username="审核管理员", role="admin")
    session.commit()

    with pytest.raises(IntegrityError):
        add_shop(session, shop_id=202, shop_type="restaurant")
    session.rollback()

    with pytest.raises(IntegrityError):
        add_shop(session, shop_id=203, map_x=1.5)
    session.rollback()

    with pytest.raises(IntegrityError):
        add_shop(session, shop_id=204, map_x=None, map_y=None)
    session.rollback()

    with pytest.raises(IntegrityError):
        add_shop(session, shop_id=205, status="rejected", rejection_reason=None)
    session.rollback()


def test_pending_report_unique_constraint(session: Session) -> None:
    """同一用户对同一条评价只能存在一条待处理举报，已处理举报不受限制。"""

    add_campus(session)
    add_user(session, user_id=1)
    add_user(session, user_id=2, username="审核管理员", role="admin")
    add_shop(session)
    session.commit()
    add_review(session, review_id=1001)
    session.commit()

    session.add(Report(id=1, review_id=1001, reported_by=1, reason="第一条待处理举报", status="pending"))
    session.commit()

    session.add(Report(id=2, review_id=1001, reported_by=1, reason="重复待处理举报", status="pending"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    session.add(Report(id=3, review_id=1001, reported_by=1, reason="历史已处理举报", status="resolved"))
    session.commit()
    assert session.scalar(select(func.count()).select_from(Report)) == 2


def test_delete_review_cascades_related_records(session: Session) -> None:
    """删除评价时，其点赞点踩、回复与举报记录必须同步清理，不产生孤立数据。"""

    add_campus(session)
    add_user(session, user_id=1)
    add_user(session, user_id=2, username="审核管理员", role="admin")
    add_shop(session)
    session.commit()

    review = add_review(session, review_id=1001)
    session.add(ReviewReaction(review_id=1001, user_id=2, reaction_type="like"))
    session.add(ReviewReply(review_id=1001, user_id=2, content="测试回复。", status="visible"))
    session.add(Report(review_id=1001, reported_by=2, reason="测试举报理由", status="pending"))
    session.commit()

    session.delete(review)
    session.commit()

    assert session.scalar(select(func.count()).select_from(ReviewReaction)) == 0
    assert session.scalar(select(func.count()).select_from(ReviewReply)) == 0
    assert session.scalar(select(func.count()).select_from(Report)) == 0
