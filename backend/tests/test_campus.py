"""校园配置、地图点位、范围过滤与底图上传测试：对应第四步验收标准。"""

import io
import json
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import create_db_engine
from app.models import Campus, Shop, User
from app.services.campus_service import import_campuses_from_directory

CAMPUSES_URL = "/api/v1/campuses"
ADMIN_CREATE_CAMPUS_URL = "/api/v1/admin/campuses"
UPLOAD_URL = "/api/v1/admin/uploads/campus-map"

ADMIN_USERNAME = "地图管理员"
ADMIN_PASSWORD = "地图管理员密码-2026"


def create_admin(engine: Engine) -> int:
    with Session(engine) as session:
        user = User(
            username=ADMIN_USERNAME,
            password_hash=hash_password(ADMIN_PASSWORD),
            role="admin",
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.id


def create_image_campus(
    engine: Engine,
    campus_id: str = "image_campus",
    *,
    is_active: bool = True,
    attribution: str = "开发演示底图",
) -> None:
    with Session(engine) as session:
        session.add(
            Campus(
                campus_id=campus_id,
                campus_name=f"图片校园-{campus_id}",
                map_type="image",
                map_asset_url=f"/assets/maps/{campus_id}.png",
                map_attribution=attribution,
                allow_off_campus=False,
                image_width=2000,
                image_height=1000,
                default_map_x=0.5,
                default_map_y=0.5,
                default_zoom=1,
                is_active=is_active,
            )
        )
        session.commit()


def create_real_campus(
    engine: Engine,
    campus_id: str = "real_campus",
    *,
    allow_off_campus: bool = False,
    radius: float | None = 1000,
    latitude: float = 30.7500,
    longitude: float = 103.9800,
) -> None:
    with Session(engine) as session:
        session.add(
            Campus(
                campus_id=campus_id,
                campus_name=f"真实地图校园-{campus_id}",
                map_type="real",
                tile_url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                map_attribution="地图数据 © OpenStreetMap 贡献者",
                allow_off_campus=allow_off_campus,
                default_latitude=latitude,
                default_longitude=longitude,
                default_zoom=16,
                boundary_radius_meters=radius,
                is_active=True,
            )
        )
        session.commit()


def create_shop(
    engine: Engine,
    shop_id: int,
    campus_id: str,
    *,
    status: str = "approved",
    shop_type: str = "shop",
    rejection_reason: str | None = None,
    map_x: float | None = None,
    map_y: float | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> None:
    with Session(engine) as session:
        session.add(
            Shop(
                id=shop_id,
                campus_id=campus_id,
                name=f"测试店铺{shop_id}",
                description="用于地图点位测试的店铺。",
                shop_type=shop_type,
                submitted_by=1,
                status=status,
                rejection_reason=rejection_reason,
                map_x=map_x,
                map_y=map_y,
                latitude=latitude,
                longitude=longitude,
            )
        )
        session.commit()


def create_submitter(engine: Engine) -> None:
    with Session(engine) as session:
        session.add(
            User(
                id=1,
                username="演示提交者",
                password_hash=hash_password("演示提交者密码-2026"),
                role="user",
                is_active=True,
            )
        )
        session.commit()


def login_admin(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200


def csrf_headers(client: TestClient) -> dict[str, str]:
    """获取 CSRF 令牌；测试客户端没有令牌时先访问一个公开接口获取。"""

    token = client.cookies.get("csrf_token")
    if token is None:
        client.get("/api/v1/health")
        token = client.cookies.get("csrf_token")
    return {"X-CSRF-Token": token or ""}


def valid_image_map_payload(**overrides) -> dict:
    payload = {
        "map_type": "image",
        "map_asset_url": "/assets/maps/updated.png",
        "tile_url_template": None,
        "map_attribution": "更新后的示意图署名",
        "allow_off_campus": False,
        "image_width": 2400,
        "image_height": 1600,
        "default_map_x": 0.5,
        "default_map_y": 0.5,
        "default_latitude": None,
        "default_longitude": None,
        "default_zoom": 1,
        "boundary_radius_meters": None,
    }
    payload.update(overrides)
    return payload


def test_campus_list_only_returns_active_campuses(client: TestClient, engine: Engine) -> None:
    """验收标准 1：默认校园可以从配置中读取，未开放校园不出现在公开列表。"""

    create_image_campus(engine, "campus_active")
    create_image_campus(engine, "campus_inactive", is_active=False)

    response = client.get(CAMPUSES_URL)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["campus_id"] == "campus_active"
    assert data["items"][0]["map_type"] == "image"


def test_campus_detail_and_map_config(client: TestClient, engine: Engine) -> None:
    """验收标准 2、6：校园详情与地图配置可以通过接口读取。"""

    create_image_campus(engine, "campus_detail")

    detail = client.get(f"{CAMPUSES_URL}/campus_detail")
    assert detail.status_code == 200
    assert detail.json()["data"]["campus_name"] == "图片校园-campus_detail"
    assert detail.json()["data"]["image_width"] == 2000

    map_config = client.get(f"{CAMPUSES_URL}/campus_detail/map")
    assert map_config.status_code == 200
    assert map_config.json()["data"]["map_type"] == "image"
    assert map_config.json()["data"]["map_asset_url"] == "/assets/maps/campus_detail.png"

    missing = client.get(f"{CAMPUSES_URL}/not_exists")
    assert missing.status_code == 404
    assert missing.json()["message"] == "校园不存在。"


def test_inactive_campus_is_not_public(client: TestClient, engine: Engine) -> None:
    """未开放的校园不能通过公开接口读取。"""

    create_image_campus(engine, "hidden_campus", is_active=False)

    response = client.get(f"{CAMPUSES_URL}/hidden_campus")

    assert response.status_code == 404
    assert response.json()["message"] == "该校园当前未开放访问。"


def test_points_only_include_approved_shops_with_minimal_fields(
    client: TestClient, engine: Engine
) -> None:
    """验收标准 8、9：公开点位只返回已审核店铺，且只包含展示点位所需字段。"""

    create_submitter(engine)
    create_image_campus(engine, "points_campus")
    create_shop(engine, 101, "points_campus", map_x=0.2, map_y=0.3)
    create_shop(engine, 102, "points_campus", status="pending", map_x=0.4, map_y=0.4)
    create_shop(
        engine,
        103,
        "points_campus",
        status="rejected",
        rejection_reason="测试拒绝原因",
        map_x=0.6,
        map_y=0.6,
    )

    response = client.get(f"{CAMPUSES_URL}/points_campus/shops/points")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["campus_id"] == "points_campus"
    assert data["map_type"] == "image"
    assert len(data["items"]) == 1

    point = data["items"][0]
    assert point["id"] == 101
    # 游客只能拿到点位最小字段，不能读取简介、照片、评价或经纬度
    assert set(point.keys()) == {"id", "name", "shop_type", "map_x", "map_y"}


def test_points_are_isolated_between_campuses(client: TestClient, engine: Engine) -> None:
    """验收标准 7：不同校园的点位相互隔离，不会混合展示。"""

    create_submitter(engine)
    create_image_campus(engine, "campus_a")
    create_image_campus(engine, "campus_b")
    create_shop(engine, 201, "campus_a", map_x=0.1, map_y=0.1)
    create_shop(engine, 202, "campus_b", map_x=0.9, map_y=0.9)

    points_a = client.get(f"{CAMPUSES_URL}/campus_a/shops/points").json()["data"]["items"]
    points_b = client.get(f"{CAMPUSES_URL}/campus_b/shops/points").json()["data"]["items"]

    assert [item["id"] for item in points_a] == [201]
    assert [item["id"] for item in points_b] == [202]


def test_coordinate_system_is_not_mixed(client: TestClient, engine: Engine) -> None:
    """验收标准 11：图片模式不返回经纬度，真实地图模式不返回图片坐标。"""

    create_submitter(engine)
    create_image_campus(engine, "mixed_image")
    create_real_campus(engine, "mixed_real", radius=None)
    # 故意同时写入两套坐标，接口仍必须按校园底图类型只返回对应的一套。
    create_shop(
        engine,
        301,
        "mixed_image",
        map_x=0.3,
        map_y=0.4,
        latitude=30.75,
        longitude=103.98,
    )
    create_shop(
        engine,
        302,
        "mixed_real",
        map_x=0.7,
        map_y=0.8,
        latitude=30.7501,
        longitude=103.9801,
    )

    image_point = client.get(f"{CAMPUSES_URL}/mixed_image/shops/points").json()["data"]["items"][0]
    real_point = client.get(f"{CAMPUSES_URL}/mixed_real/shops/points").json()["data"]["items"][0]

    assert set(image_point.keys()) == {"id", "name", "shop_type", "map_x", "map_y"}
    assert set(real_point.keys()) == {"id", "name", "shop_type", "latitude", "longitude"}


def test_real_campus_filters_off_campus_points(client: TestClient, engine: Engine) -> None:
    """验收标准 5、7：真实地图模式按校园范围过滤校外店铺，配置允许时不过滤。"""

    create_submitter(engine)
    create_real_campus(engine, "radius_campus", allow_off_campus=False, radius=1000)
    create_shop(engine, 401, "radius_campus", latitude=30.7505, longitude=103.9800)  # 约 55 米
    create_shop(engine, 402, "radius_campus", latitude=30.7900, longitude=103.9800)  # 约 4.4 公里

    inside = client.get(f"{CAMPUSES_URL}/radius_campus/shops/points").json()["data"]["items"]
    assert [item["id"] for item in inside] == [401]

    # 修改配置允许展示校外店铺后，两个点位都应返回
    with Session(engine) as session:
        campus = session.get(Campus, "radius_campus")
        campus.allow_off_campus = True
        session.commit()

    all_points = client.get(f"{CAMPUSES_URL}/radius_campus/shops/points").json()["data"]["items"]
    assert sorted(item["id"] for item in all_points) == [401, 402]


def test_admin_can_update_campus_map(client: TestClient, engine: Engine) -> None:
    """管理员可以更新校园地图配置，公开接口立即生效。"""

    create_admin(engine)
    create_image_campus(engine, "update_campus")
    login_admin(client)

    response = client.put(
        f"/api/v1/admin/campuses/update_campus/map",
        json=valid_image_map_payload(default_zoom=2, map_attribution="新的署名"),
        headers=csrf_headers(client),
    )

    assert response.status_code == 200
    assert response.json()["message"] == "校园地图配置已更新。"

    map_config = client.get(f"{CAMPUSES_URL}/update_campus/map").json()["data"]
    assert map_config["default_zoom"] == 2
    assert map_config["map_attribution"] == "新的署名"
    assert map_config["map_asset_url"] == "/assets/maps/updated.png"


def test_update_campus_map_validates_config(client: TestClient, engine: Engine) -> None:
    """地图配置必须经过校验，错误提示为中文。"""

    create_admin(engine)
    create_image_campus(engine, "validate_campus")
    login_admin(client)

    missing_image_fields = client.put(
        "/api/v1/admin/campuses/validate_campus/map",
        json=valid_image_map_payload(image_width=None, image_height=None),
        headers=csrf_headers(client),
    )
    assert missing_image_fields.status_code == 422
    errors = missing_image_fields.json()["data"]["errors"]
    assert errors[0]["message"] == "图片底图模式必须提供底图地址、图片宽高和默认中心点。"

    invalid_type = client.put(
        "/api/v1/admin/campuses/validate_campus/map",
        json=valid_image_map_payload(map_type="satellite"),
        headers=csrf_headers(client),
    )
    assert invalid_type.status_code == 422
    assert invalid_type.json()["data"]["errors"][0]["message"] == (
        "地图类型只允许 image（图片底图）或 real（真实地图）。"
    )


def test_campus_config_requires_admin(client: TestClient, engine: Engine) -> None:
    """普通用户与游客不能修改校园地图配置。"""

    create_image_campus(engine, "permission_campus")

    guest = client.put(
        "/api/v1/admin/campuses/permission_campus/map",
        json=valid_image_map_payload(),
        headers=csrf_headers(client),
    )
    assert guest.status_code == 401

    create_admin(engine)
    login_admin(client)
    assert client.post("/api/v1/auth/logout", headers=csrf_headers(client)).status_code == 200

    with Session(engine) as session:
        session.add(
            User(
                username="普通地图用户",
                password_hash=hash_password("普通用户密码-2026"),
                role="user",
                is_active=True,
            )
        )
        session.commit()
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"username": "普通地图用户", "password": "普通用户密码-2026"},
        ).status_code
        == 200
    )

    ordinary = client.put(
        "/api/v1/admin/campuses/permission_campus/map",
        json=valid_image_map_payload(),
        headers=csrf_headers(client),
    )
    assert ordinary.status_code == 403
    assert ordinary.json()["message"] == "当前操作需要管理员权限。"


def test_admin_can_create_and_deactivate_campus(client: TestClient, engine: Engine) -> None:
    """管理员可以新增校园并通过配置停用校园（更换校园不需要修改业务代码）。"""

    create_admin(engine)
    login_admin(client)

    payload = {
        "campus_id": "new_campus",
        "campus_name": "新增测试校园",
        "map_type": "real",
        "map_asset_url": None,
        "tile_url_template": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        "map_attribution": "地图数据 © OpenStreetMap 贡献者",
        "allow_off_campus": True,
        "image_width": None,
        "image_height": None,
        "default_map_x": None,
        "default_map_y": None,
        "default_latitude": 30.75,
        "default_longitude": 103.98,
        "default_zoom": 15,
        "boundary_radius_meters": 800,
        "is_active": True,
    }

    created = client.post(ADMIN_CREATE_CAMPUS_URL, json=payload, headers=csrf_headers(client))
    assert created.status_code == 201
    assert created.json()["data"]["campus_id"] == "new_campus"

    duplicated = client.post(ADMIN_CREATE_CAMPUS_URL, json=payload, headers=csrf_headers(client))
    assert duplicated.status_code == 409
    assert duplicated.json()["message"] == "该校园标识已存在，请更换后重试。"

    deactivated = client.patch(
        f"{ADMIN_CREATE_CAMPUS_URL}/new_campus",
        json={"is_active": False},
        headers=csrf_headers(client),
    )
    assert deactivated.status_code == 200
    assert client.get(f"{CAMPUSES_URL}/new_campus").status_code == 404


def make_png_bytes(width: int = 600, height: int = 400) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "#ffffff").save(buffer, format="PNG")
    return buffer.getvalue()


def test_admin_can_upload_campus_map(client: TestClient, engine: Engine, tmp_path, monkeypatch) -> None:
    """验收标准 6：管理员可以上传底图，上传后的底图可以通过 /assets/maps 访问。"""

    monkeypatch.setattr(settings, "map_dir", str(tmp_path / "maps"))
    create_admin(engine)
    login_admin(client)

    response = client.post(
        UPLOAD_URL,
        files={"file": ("campus.png", make_png_bytes(), "image/png")},
        headers=csrf_headers(client),
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["map_asset_url"].startswith("/assets/maps/")
    assert data["image_width"] == 600
    assert data["image_height"] == 400

    filename = Path(data["map_asset_url"]).name
    # 未被校园配置引用时不能访问
    assert client.get(f"/assets/maps/{filename}").status_code == 404

    create_image_campus(engine, "uploaded_campus")
    with Session(engine) as session:
        campus = session.get(Campus, "uploaded_campus")
        campus.map_asset_url = data["map_asset_url"]
        campus.image_width = data["image_width"]
        campus.image_height = data["image_height"]
        session.commit()

    served = client.get(f"/assets/maps/{filename}")
    assert served.status_code == 200
    assert len(served.content) > 0


def test_upload_validates_file_type_and_size(client: TestClient, engine: Engine, tmp_path, monkeypatch) -> None:
    """底图上传必须校验扩展名、真实内容与文件大小，并受管理员权限保护。"""

    monkeypatch.setattr(settings, "map_dir", str(tmp_path / "maps"))
    create_admin(engine)
    login_admin(client)

    wrong_extension = client.post(
        UPLOAD_URL,
        files={"file": ("campus.txt", b"not an image", "text/plain")},
        headers=csrf_headers(client),
    )
    assert wrong_extension.status_code == 415
    assert wrong_extension.json()["message"] == "底图只支持 PNG、JPEG 或 WebP 格式。"

    fake_image = client.post(
        UPLOAD_URL,
        files={"file": ("campus.png", b"not a real image", "image/png")},
        headers=csrf_headers(client),
    )
    assert fake_image.status_code == 415
    assert fake_image.json()["message"] == "文件内容不是有效的图片。"

    oversized = client.post(
        UPLOAD_URL,
        files={"file": ("campus.png", b"0" * (5 * 1024 * 1024 + 1), "image/png")},
        headers=csrf_headers(client),
    )
    assert oversized.status_code == 413
    assert oversized.json()["message"] == "底图文件不能超过 5 MB。"

    too_small = client.post(
        UPLOAD_URL,
        files={"file": ("campus.png", make_png_bytes(100, 100), "image/png")},
        headers=csrf_headers(client),
    )
    assert too_small.status_code == 400
    assert too_small.json()["message"] == "底图宽高不能小于 200 像素。"


def test_upload_requires_admin(client: TestClient, engine: Engine, tmp_path, monkeypatch) -> None:
    """游客与普通用户不能上传校园底图。"""

    monkeypatch.setattr(settings, "map_dir", str(tmp_path / "maps"))

    guest = client.post(
        UPLOAD_URL,
        files={"file": ("campus.png", make_png_bytes(), "image/png")},
        headers=csrf_headers(client),
    )
    assert guest.status_code == 401

    with Session(engine) as session:
        session.add(
            User(
                username="普通上传用户",
                password_hash=hash_password("普通上传密码-2026"),
                role="user",
                is_active=True,
            )
        )
        session.commit()
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"username": "普通上传用户", "password": "普通上传密码-2026"},
        ).status_code
        == 200
    )

    ordinary = client.post(
        UPLOAD_URL,
        files={"file": ("campus.png", make_png_bytes(), "image/png")},
        headers=csrf_headers(client),
    )
    assert ordinary.status_code == 403


def test_import_campuses_from_config_directory(client: TestClient, engine: Engine, tmp_path) -> None:
    """验收标准 1、6：可以通过配置文件新增或更新校园，不需要修改业务代码。"""

    config_dir = tmp_path / "campuses"
    config_dir.mkdir()
    config_file = config_dir / "imported.json"
    config_file.write_text(
        json.dumps(
            {
                "campus_id": "imported_campus",
                "campus_name": "导入测试校园",
                "map_type": "image",
                "map_asset_url": "/assets/maps/imported.png",
                "tile_url_template": None,
                "map_attribution": "导入测试署名",
                "allow_off_campus": False,
                "image_width": 1200,
                "image_height": 800,
                "default_map_x": 0.5,
                "default_map_y": 0.5,
                "default_latitude": None,
                "default_longitude": None,
                "default_zoom": 1,
                "boundary_radius_meters": None,
                "is_active": True,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with Session(engine) as session:
        first = import_campuses_from_directory(session, config_dir)
    assert first["created"] == ["imported_campus"]

    # 修改名称后再次导入应更新而不是重复新增
    payload = json.loads(config_file.read_text(encoding="utf-8"))
    payload["campus_name"] = "导入测试校园（已更新）"
    config_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with Session(engine) as session:
        second = import_campuses_from_directory(session, config_dir)
    assert second["updated"] == ["imported_campus"]

    detail = client.get(f"{CAMPUSES_URL}/imported_campus")
    assert detail.status_code == 200
    assert detail.json()["data"]["campus_name"] == "导入测试校园（已更新）"
