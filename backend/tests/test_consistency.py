"""数据一致性检查测试：对应第八步验收标准 10。"""

import sqlite3

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.check_consistency import run_checks
from app.models import Campus, Report, Review, ReviewReaction, ReviewReply, Shop, User


def setup_consistent_data(engine: Engine) -> None:
    with Session(engine) as session:
        session.add(
            Campus(
                campus_id="consistency_campus",
                campus_name="一致性测试校园",
                map_type="image",
                map_asset_url="/assets/maps/consistency.png",
                map_attribution="一致性测试署名",
                allow_off_campus=False,
                image_width=1000,
                image_height=800,
                default_map_x=0.5,
                default_map_y=0.5,
                default_zoom=1,
                is_active=True,
            )
        )
        session.add(
            User(
                id=1,
                username="一致性用户",
                password_hash=hash_password("一致性用户密码-2026"),
                role="admin",
                is_active=True,
            )
        )
        session.commit()
        session.add(
            Shop(
                id=1301,
                campus_id="consistency_campus",
                name="一致性测试店铺",
                description="用于一致性检查的店铺。",
                shop_type="shop",
                submitted_by=1,
                status="approved",
                map_x=0.3,
                map_y=0.3,
                reviewed_by=1,
            )
        )
        session.commit()
        session.add(
            Review(id=1301, shop_id=1301, user_id=1, rating=4, content="一致性评价。", status="visible")
        )
        session.commit()


def test_consistent_database_has_no_issues(engine: Engine) -> None:
    """一致的数据不应报告任何问题。"""

    setup_consistent_data(engine)
    database_file = engine.url.database
    issues = run_checks(database_file)

    assert all(len(items) == 0 for items in issues.values()), issues


def test_detects_coordinate_mismatch(engine: Engine) -> None:
    """店铺坐标与校园地图类型不一致时应当被检查出来。"""

    setup_consistent_data(engine)
    with Session(engine) as session:
        session.add(
            Shop(
                id=1302,
                campus_id="consistency_campus",
                name="坐标异常店铺",
                description="图片校园却只有经纬度。",
                shop_type="shop",
                submitted_by=1,
                status="approved",
                latitude=30.75,
                longitude=103.98,
            )
        )
        session.commit()

    issues = run_checks(engine.url.database)
    assert any("坐标不符合图片模式要求" in item for item in issues["coordinate_mismatch"])


def test_detects_orphan_records(engine: Engine) -> None:
    """绕过外键生成的孤立评价应当被检查出来。"""

    setup_consistent_data(engine)
    # 使用独立连接关闭外键约束，模拟外部工具写入的孤立数据
    raw = sqlite3.connect(engine.url.database)
    try:
        raw.execute("PRAGMA foreign_keys=OFF")
        raw.execute(
            "INSERT INTO reviews (id, shop_id, user_id, rating, content, status, created_at, updated_at) "
            "VALUES (1399, 9999, 1, 5, '孤立评价', 'visible', datetime('now'), datetime('now'))"
        )
        raw.commit()
    finally:
        raw.close()

    issues = run_checks(engine.url.database)
    assert any("记录 id=1399" in item for item in issues["orphan_reviews"])
    assert len(issues["foreign_keys"]) >= 1


def test_deleting_review_removes_related_records(engine: Engine, client) -> None:
    """验收标准 10：删除评价后不会留下孤立的互动、回复与举报数据。"""

    setup_consistent_data(engine)
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "一致性用户", "password": "一致性用户密码-2026"},
    )
    assert login.status_code == 200

    with Session(engine) as session:
        session.add(ReviewReaction(id=1301, review_id=1301, user_id=1, reaction_type="like"))
        session.add(ReviewReply(id=1301, review_id=1301, user_id=1, content="一致性回复。", status="visible"))
        session.add(Report(id=1301, review_id=1301, reported_by=1, reason="一致性举报。", status="pending"))
        session.commit()

    response = client.delete("/api/v1/reviews/1301", headers={"X-CSRF-Token": client.cookies.get("csrf_token") or ""})
    assert response.status_code == 200

    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Review)) == 0
        assert session.scalar(select(func.count()).select_from(ReviewReaction)) == 0
        assert session.scalar(select(func.count()).select_from(ReviewReply)) == 0
        assert session.scalar(select(func.count()).select_from(Report)) == 0

    issues = run_checks(engine.url.database)
    assert all(len(items) == 0 for items in issues.values()), issues
