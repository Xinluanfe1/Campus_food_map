"""多校园隔离与地图模式测试：对应第八步验收标准 3、4、5。

说明：第一阶段默认只启用一个校园，多校园能力通过配置与数据模型预留；
本测试在独立数据库中创建两个启用校园，用于验证隔离与扩展能力。
"""

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Campus, Review, Shop, User

VIEWER_USERNAME = "多校园查看者"
VIEWER_PASSWORD = "多校园查看密码-2026"


def create_user(session: Session, user_id: int, username: str, password: str, role: str = "user") -> None:
    session.add(
        User(
            id=user_id,
            username=username,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )
    )


def create_campus(session: Session, campus_id: str, map_type: str, name: str) -> None:
    if map_type == "image":
        session.add(
            Campus(
                campus_id=campus_id,
                campus_name=name,
                map_type="image",
                map_asset_url=f"/assets/maps/{campus_id}.png",
                map_attribution="图片模式署名",
                allow_off_campus=False,
                image_width=1000,
                image_height=800,
                default_map_x=0.5,
                default_map_y=0.5,
                default_zoom=1,
                is_active=True,
            )
        )
    else:
        session.add(
            Campus(
                campus_id=campus_id,
                campus_name=name,
                map_type="real",
                tile_url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                map_attribution="地图数据 © OpenStreetMap 贡献者",
                allow_off_campus=True,
                default_latitude=30.75,
                default_longitude=103.98,
                default_zoom=16,
                boundary_radius_meters=None,
                is_active=True,
            )
        )


def setup_two_campuses(engine: Engine) -> None:
    """校园一使用图片底图，校园二使用真实地图，各自拥有店铺与评价。"""

    with Session(engine) as session:
        create_campus(session, "campus_image", "image", "图片底图校园")
        create_campus(session, "campus_real", "real", "真实地图校园")
        create_user(session, 1, "校园一提交者", "校园一提交者密码-2026")
        create_user(session, 2, "校园二提交者", "校园二提交者密码-2026")
        create_user(session, 3, "校园一评价者", "校园一评价者密码-2026")
        create_user(session, 4, "校园二评价者", "校园二评价者密码-2026")
        create_user(session, 9, VIEWER_USERNAME, VIEWER_PASSWORD)
        session.commit()

        session.add(
            Shop(
                id=1001,
                campus_id="campus_image",
                name="共享名称食堂",
                description="图片校园的店铺。",
                shop_type="shop",
                submitted_by=1,
                status="approved",
                map_x=0.3,
                map_y=0.4,
            )
        )
        session.add(
            Shop(
                id=1002,
                campus_id="campus_real",
                name="共享名称食堂",
                description="真实地图校园的店铺。",
                shop_type="vendor",
                submitted_by=2,
                status="approved",
                latitude=30.7505,
                longitude=103.9801,
            )
        )
        session.commit()

        session.add(Review(id=1, shop_id=1001, user_id=3, rating=5, content="图片校园评价。", status="visible"))
        session.add(Review(id=2, shop_id=1002, user_id=4, rating=4, content="真实校园评价。", status="visible"))
        session.commit()


def login_viewer(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": VIEWER_USERNAME, "password": VIEWER_PASSWORD},
    )
    assert response.status_code == 200, response.text


def test_campus_list_contains_both_enabled_campuses(client: TestClient, engine: Engine) -> None:
    """多校园能力预留：启用多个校园时，公开列表会返回全部启用校园。"""

    setup_two_campuses(engine)

    data = client.get("/api/v1/campuses").json()["data"]
    campus_ids = [item["campus_id"] for item in data["items"]]
    assert campus_ids == ["campus_image", "campus_real"]
    types = {item["campus_id"]: item["map_type"] for item in data["items"]}
    assert types == {"campus_image": "image", "campus_real": "real"}


def test_points_are_isolated_between_campuses(client: TestClient, engine: Engine) -> None:
    """验收标准 3、4：两个校园的店铺相互隔离，且分别使用不同地图模式。"""

    setup_two_campuses(engine)

    image_points = client.get("/api/v1/campuses/campus_image/shops/points").json()["data"]
    real_points = client.get("/api/v1/campuses/campus_real/shops/points").json()["data"]

    assert image_points["map_type"] == "image"
    assert [item["id"] for item in image_points["items"]] == [1001]
    assert set(image_points["items"][0].keys()) == {"id", "name", "shop_type", "map_x", "map_y"}

    assert real_points["map_type"] == "real"
    assert [item["id"] for item in real_points["items"]] == [1002]
    assert set(real_points["items"][0].keys()) == {"id", "name", "shop_type", "latitude", "longitude"}


def test_detail_and_reviews_are_bound_to_campus(client: TestClient, engine: Engine) -> None:
    """验收标准 5：店铺详情与评价必须与当前校园匹配，不能跨校园读取。"""

    setup_two_campuses(engine)
    login_viewer(client)

    own_detail = client.get("/api/v1/campuses/campus_image/shops/1001")
    assert own_detail.status_code == 200
    assert own_detail.json()["data"]["name"] == "共享名称食堂"

    cross_campus = client.get("/api/v1/campuses/campus_image/shops/1002")
    assert cross_campus.status_code == 404
    assert cross_campus.json()["message"] == "店铺不存在或未公开。"

    reviews = client.get("/api/v1/shops/1001/reviews").json()["data"]
    assert reviews["total"] == 1
    assert reviews["items"][0]["content"] == "图片校园评价。"


def test_rankings_and_contributors_are_per_campus(client: TestClient, engine: Engine) -> None:
    """验收标准 5：排行榜与贡献榜只统计当前校园的数据。"""

    setup_two_campuses(engine)
    login_viewer(client)

    image_ranking = client.get("/api/v1/campuses/campus_image/rankings/shops").json()["data"]
    real_ranking = client.get("/api/v1/campuses/campus_real/rankings/shops").json()["data"]
    assert [item["shop_id"] for item in image_ranking["items"]] == [1001]
    assert [item["shop_id"] for item in real_ranking["items"]] == [1002]

    image_contributors = client.get("/api/v1/campuses/campus_image/rankings/contributors").json()["data"]
    real_contributors = client.get("/api/v1/campuses/campus_real/rankings/contributors").json()["data"]
    assert [item["username"] for item in image_contributors["items"]] == ["校园一提交者"]
    assert [item["username"] for item in real_contributors["items"]] == ["校园二提交者"]


def test_search_only_returns_current_campus(client: TestClient, engine: Engine) -> None:
    """验收标准 3：同名店铺不会跨校园返回。"""

    setup_two_campuses(engine)
    login_viewer(client)

    image_search = client.get("/api/v1/campuses/campus_image/search?q=共享名称").json()["data"]
    real_search = client.get("/api/v1/campuses/campus_real/search?q=共享名称").json()["data"]

    assert [item["id"] for item in image_search["items"]] == [1001]
    assert [item["id"] for item in real_search["items"]] == [1002]
