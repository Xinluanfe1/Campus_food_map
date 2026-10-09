"""百度地图提供方测试：验证可选的 baidu 提供方与 AK 下发行为。"""

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models import Campus, Shop, User

ADMIN_USERNAME = "百度地图管理员"
ADMIN_PASSWORD = "百度地图管理员密码-2026"

BAIDU_SDK_URL = "https://api.map.baidu.com/api?type=webgl&v=1.0"


def create_admin(engine: Engine) -> None:
    with Session(engine) as session:
        session.add(
            User(
                username=ADMIN_USERNAME,
                password_hash=hash_password(ADMIN_PASSWORD),
                role="admin",
                is_active=True,
            )
        )
        session.commit()


def create_image_campus(engine: Engine) -> None:
    with Session(engine) as session:
        session.add(
            Campus(
                campus_id="provider_campus",
                campus_name="提供方测试校园",
                map_type="image",
                map_provider="tiles",
                map_asset_url="/assets/maps/provider.png",
                map_attribution="测试署名",
                allow_off_campus=False,
                image_width=1000,
                image_height=800,
                default_map_x=0.5,
                default_map_y=0.5,
                default_zoom=1,
                is_active=True,
            )
        )
        session.commit()


def login_admin(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text


def csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get("csrf_token")
    if token is None:
        client.get("/api/v1/health")
        token = client.cookies.get("csrf_token")
    return {"X-CSRF-Token": token or ""}


def baidu_payload(**overrides) -> dict:
    payload = {
        "map_type": "real",
        "map_provider": "baidu",
        "map_asset_url": None,
        "tile_url_template": BAIDU_SDK_URL,
        "map_attribution": "百度地图",
        "allow_off_campus": True,
        "image_width": None,
        "image_height": None,
        "default_map_x": None,
        "default_map_y": None,
        "default_latitude": 30.7503,
        "default_longitude": 103.9857,
        "default_zoom": 16,
        "boundary_radius_meters": 2000,
    }
    payload.update(overrides)
    return payload


def test_default_provider_is_tiles(client: TestClient, engine: Engine) -> None:
    """未显式配置时，真实地图默认使用瓦片提供方，且不返回百度 AK。"""

    create_image_campus(engine)
    data = client.get("/api/v1/campuses/provider_campus/map").json()["data"]

    assert data["map_provider"] == "tiles"
    assert data["baidu_map_ak"] is None


def test_admin_can_switch_campus_to_baidu_provider(
    client: TestClient, engine: Engine, monkeypatch
) -> None:
    """管理员可以把校园切换为百度地图提供方，接口返回 SDK 地址与部署环境中的 AK。"""

    create_admin(engine)
    create_image_campus(engine)
    login_admin(client)
    monkeypatch.setattr(settings, "baidu_map_ak", "测试用百度AK")

    updated = client.put(
        "/api/v1/admin/campuses/provider_campus/map",
        json=baidu_payload(),
        headers=csrf_headers(client),
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["map_provider"] == "baidu"

    data = client.get("/api/v1/campuses/provider_campus/map").json()["data"]
    assert data["map_type"] == "real"
    assert data["map_provider"] == "baidu"
    assert data["tile_url_template"] == BAIDU_SDK_URL
    assert data["baidu_map_ak"] == "测试用百度AK"
    assert data["default_latitude"] == 30.7503


def test_baidu_ak_is_null_when_not_configured(client: TestClient, engine: Engine) -> None:
    """部署环境未提供 AK 时，接口返回 None，由前端给出中文提示。"""

    create_admin(engine)
    create_image_campus(engine)
    login_admin(client)
    monkeypatch_target = settings.baidu_map_ak
    settings.baidu_map_ak = None
    try:
        client.put(
            "/api/v1/admin/campuses/provider_campus/map",
            json=baidu_payload(),
            headers=csrf_headers(client),
        )
    finally:
        settings.baidu_map_ak = monkeypatch_target

    data = client.get("/api/v1/campuses/provider_campus/map").json()["data"]
    assert data["map_provider"] == "baidu"
    assert data["baidu_map_ak"] is None


def test_invalid_provider_is_rejected(client: TestClient, engine: Engine) -> None:
    """提供方只允许 tiles 或 baidu，图片模式不能使用百度提供方。"""

    create_admin(engine)
    create_image_campus(engine)
    login_admin(client)

    invalid = client.put(
        "/api/v1/admin/campuses/provider_campus/map",
        json=baidu_payload(map_provider="amap"),
        headers=csrf_headers(client),
    )
    assert invalid.status_code == 422
    assert invalid.json()["data"]["errors"][0]["message"] == (
        "真实地图提供方只允许 tiles（瓦片地图）或 baidu（百度 JSAPI）。"
    )

    image_with_baidu = client.put(
        "/api/v1/admin/campuses/provider_campus/map",
        json={
            **baidu_payload(map_provider="baidu"),
            "map_type": "image",
            "map_asset_url": "/assets/maps/provider.png",
            "image_width": 1000,
            "image_height": 800,
            "default_map_x": 0.5,
            "default_map_y": 0.5,
        },
        headers=csrf_headers(client),
    )
    assert image_with_baidu.status_code == 422
    assert image_with_baidu.json()["data"]["errors"][0]["message"] == (
        "图片底图模式只能使用 tiles 提供方。"
    )


def test_baidu_campus_points_use_geo_coordinates(client: TestClient, engine: Engine) -> None:
    """百度提供方属于真实地图模式，点位返回经纬度而不是图片坐标。"""

    create_admin(engine)
    create_image_campus(engine)
    login_admin(client)
    client.put(
        "/api/v1/admin/campuses/provider_campus/map",
        json=baidu_payload(),
        headers=csrf_headers(client),
    )

    with Session(engine) as session:
        session.add(
            Shop(
                id=1401,
                campus_id="provider_campus",
                name="百度地图测试店铺",
                description="用于验证百度提供方的点位。",
                shop_type="shop",
                submitted_by=1,
                status="approved",
                latitude=30.7505,
                longitude=103.9858,
            )
        )
        session.commit()

    points = client.get("/api/v1/campuses/provider_campus/shops/points").json()["data"]
    assert points["map_type"] == "real"
    assert set(points["items"][0].keys()) == {"id", "name", "shop_type", "latitude", "longitude"}
