"""店铺提交、审核与详情测试：对应第五步验收标准。"""

import io

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models import Campus, Review, ReviewReaction, Shop, User

USER_USERNAME = "提交用户"
USER_PASSWORD = "提交用户密码-2026"
OTHER_USERNAME = "其他用户"
OTHER_PASSWORD = "其他用户密码-2026"
ADMIN_USERNAME = "审核管理员"
ADMIN_PASSWORD = "审核管理员密码-2026"


def create_user(engine: Engine, username: str, password: str, role: str = "user") -> int:
    with Session(engine) as session:
        user = User(
            username=username,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.id


def create_campus(engine: Engine, campus_id: str = "shop_campus", map_type: str = "image") -> None:
    with Session(engine) as session:
        if map_type == "image":
            session.add(
                Campus(
                    campus_id=campus_id,
                    campus_name="店铺测试校园",
                    map_type="image",
                    map_asset_url=f"/assets/maps/{campus_id}.png",
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
        else:
            session.add(
                Campus(
                    campus_id=campus_id,
                    campus_name="真实地图测试校园",
                    map_type="real",
                    tile_url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                    map_attribution="地图数据 © OpenStreetMap 贡献者",
                    allow_off_campus=False,
                    default_latitude=30.7500,
                    default_longitude=103.9800,
                    default_zoom=16,
                    boundary_radius_meters=1000,
                    is_active=True,
                )
            )
        session.commit()


def login(client: TestClient, username: str, password: str) -> None:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text


def csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get("csrf_token")
    if token is None:
        client.get("/api/v1/health")
        token = client.cookies.get("csrf_token")
    return {"X-CSRF-Token": token or ""}


def make_png_bytes(width: int = 600, height: int = 400) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "#ffffff").save(buffer, format="PNG")
    return buffer.getvalue()


def submit_payload(**overrides) -> dict:
    payload = {
        "name": "测试提交店铺",
        "description": "用于测试提交与审核流程的店铺。",
        "shop_type": "shop",
        "photo_url": None,
        "map_x": 0.25,
        "map_y": 0.35,
        "latitude": None,
        "longitude": None,
    }
    payload.update(overrides)
    return payload


def submit_shop(client: TestClient, campus_id: str, **overrides) -> dict:
    response = client.post(
        f"/api/v1/campuses/{campus_id}/shops",
        json=submit_payload(**overrides),
        headers=csrf_headers(client),
    )
    return response


def prepare_user(engine: Engine, client: TestClient) -> None:
    create_user(engine, USER_USERNAME, USER_PASSWORD)
    create_campus(engine)
    login(client, USER_USERNAME, USER_PASSWORD)


def prepare_admin(engine: Engine, client: TestClient) -> None:
    create_user(engine, ADMIN_USERNAME, ADMIN_PASSWORD, role="admin")
    login(client, ADMIN_USERNAME, ADMIN_PASSWORD)


def test_guest_cannot_submit_shop(client: TestClient, engine: Engine) -> None:
    """验收标准 1：只有登录用户可以提交店铺。"""

    create_campus(engine)
    response = client.post(
        "/api/v1/campuses/shop_campus/shops",
        json=submit_payload(),
        headers=csrf_headers(client),
    )
    assert response.status_code == 401
    assert response.json()["message"] == "当前操作需要登录。"


def test_submit_shop_creates_pending_shop(client: TestClient, engine: Engine) -> None:
    """验收标准 1、3、4、5：提交成功、状态为待审核、照片可为空、不会立即公开。"""

    prepare_user(engine, client)

    response = submit_shop(client, "shop_campus")
    assert response.status_code == 201
    body = response.json()
    assert body["message"] == "已提交，等待管理员审核。"
    assert body["data"]["status"] == "pending"
    assert body["data"]["photo_url"] is None
    assert body["data"]["map_x"] == 0.25

    points = client.get("/api/v1/campuses/shop_campus/shops/points").json()["data"]["items"]
    assert points == []


def test_submit_requires_required_fields(client: TestClient, engine: Engine) -> None:
    """验收标准 2：名称、简介、类型和位置均为必填。"""

    prepare_user(engine, client)

    missing_name = client.post(
        "/api/v1/campuses/shop_campus/shops",
        json={key: value for key, value in submit_payload().items() if key != "name"},
        headers=csrf_headers(client),
    )
    assert missing_name.status_code == 422
    assert missing_name.json()["data"]["errors"][0]["message"] == "缺少必填字段。"

    empty_name = submit_shop(client, "shop_campus", name="   ")
    assert empty_name.status_code == 422
    assert empty_name.json()["data"]["errors"][0]["message"] == "店铺名称不能为空。"

    empty_description = submit_shop(client, "shop_campus", description="  ")
    assert empty_description.status_code == 422
    assert empty_description.json()["data"]["errors"][0]["message"] == "店铺简介不能为空。"

    bad_type = submit_shop(client, "shop_campus", shop_type="restaurant")
    assert bad_type.status_code == 422
    assert bad_type.json()["data"]["errors"][0]["message"] == (
        "店铺类型只允许 shop（商铺）或 vendor（摊贩）。"
    )

    no_location = submit_shop(client, "shop_campus", map_x=None, map_y=None)
    assert no_location.status_code == 422
    assert no_location.json()["data"]["errors"][0]["message"] == (
        "必须提供店铺位置（图片坐标或经纬度）。"
    )


def test_photo_url_must_be_valid(client: TestClient, engine: Engine) -> None:
    """验收标准 15：照片路径经过校验。"""

    prepare_user(engine, client)

    illegal_path = submit_shop(client, "shop_campus", photo_url="/media/shop_photos/../../secret.png")
    assert illegal_path.status_code == 422
    assert illegal_path.json()["data"]["errors"][0]["message"] == (
        "照片路径不合法，请通过照片上传接口获取。"
    )

    missing_file = submit_shop(client, "shop_campus", photo_url="/media/shop_photos/not-exists.png")
    assert missing_file.status_code == 422
    assert missing_file.json()["message"] == "照片文件不存在，请重新上传。"


def test_coordinate_system_must_match_campus(client: TestClient, engine: Engine) -> None:
    """验收标准 1、2：坐标体系必须与校园底图类型一致。"""

    prepare_user(engine, client)
    create_campus(engine, "real_shop_campus", map_type="real")

    image_campus_with_geo = submit_shop(
        client,
        "shop_campus",
        map_x=None,
        map_y=None,
        latitude=30.75,
        longitude=103.98,
    )
    assert image_campus_with_geo.status_code == 422
    assert image_campus_with_geo.json()["message"] == "该校园使用图片底图，请在地图上选择点位。"

    mixed_image = submit_shop(client, "shop_campus", latitude=30.75, longitude=103.98)
    assert mixed_image.status_code == 422
    assert mixed_image.json()["message"] == "图片底图模式不能提交经纬度坐标。"

    real_campus_with_map = submit_shop(client, "real_shop_campus")
    assert real_campus_with_map.status_code == 422
    assert real_campus_with_map.json()["message"] == "该校园使用真实地图，请在地图上选择位置。"


def test_real_campus_rejects_off_campus_position(client: TestClient, engine: Engine) -> None:
    """真实地图模式：超出校园范围的点位不能提交，允许校外店铺时可以通过。"""

    prepare_user(engine, client)
    create_campus(engine, "real_shop_campus", map_type="real")

    far_away = submit_shop(
        client,
        "real_shop_campus",
        map_x=None,
        map_y=None,
        latitude=30.7900,
        longitude=103.9800,
    )
    assert far_away.status_code == 422
    assert far_away.json()["message"] == "店铺位置超出校园范围，请重新选择点位。"

    with Session(engine) as session:
        campus = session.get(Campus, "real_shop_campus")
        campus.allow_off_campus = True
        session.commit()

    accepted = submit_shop(
        client,
        "real_shop_campus",
        map_x=None,
        map_y=None,
        latitude=30.7900,
        longitude=103.9800,
    )
    assert accepted.status_code == 201


def test_admin_approve_publishes_shop(client: TestClient, engine: Engine) -> None:
    """验收标准 6、8：管理员审核通过后店铺立即公开。"""

    prepare_user(engine, client)
    shop_id = submit_shop(client, "shop_campus").json()["data"]["id"]

    # 其他登录用户在待审核阶段看不到详情
    create_user(engine, OTHER_USERNAME, OTHER_PASSWORD)
    logout = client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    assert logout.status_code == 200
    login(client, OTHER_USERNAME, OTHER_PASSWORD)
    hidden = client.get(f"/api/v1/campuses/shop_campus/shops/{shop_id}")
    assert hidden.status_code == 404

    # 普通用户不能审核
    forbidden = client.post(
        f"/api/v1/admin/shops/{shop_id}/approve",
        headers=csrf_headers(client),
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["message"] == "当前操作需要管理员权限。"

    client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    prepare_admin(engine, client)

    approved = client.post(f"/api/v1/admin/shops/{shop_id}/approve", headers=csrf_headers(client))
    assert approved.status_code == 200
    assert approved.json()["message"] == "店铺已审核通过。"

    points = client.get("/api/v1/campuses/shop_campus/shops/points").json()["data"]["items"]
    assert [item["id"] for item in points] == [shop_id]


def test_admin_reject_requires_reason(client: TestClient, engine: Engine) -> None:
    """验收标准 6、7：管理员可以拒绝店铺，拒绝必须填写原因。"""

    prepare_user(engine, client)
    shop_id = submit_shop(client, "shop_campus").json()["data"]["id"]

    client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    prepare_admin(engine, client)

    missing_reason = client.post(
        f"/api/v1/admin/shops/{shop_id}/reject",
        json={"reason": "   "},
        headers=csrf_headers(client),
    )
    assert missing_reason.status_code == 422
    assert missing_reason.json()["data"]["errors"][0]["message"] == "请填写拒绝原因。"

    rejected = client.post(
        f"/api/v1/admin/shops/{shop_id}/reject",
        json={"reason": "店铺信息不完整，请补充准确的位置。"},
        headers=csrf_headers(client),
    )
    assert rejected.status_code == 200
    assert rejected.json()["data"]["status"] == "rejected"
    assert rejected.json()["data"]["rejection_reason"] == "店铺信息不完整，请补充准确的位置。"

    points = client.get("/api/v1/campuses/shop_campus/shops/points").json()["data"]["items"]
    assert points == []

    # 已处理的店铺不能重复审核
    again = client.post(f"/api/v1/admin/shops/{shop_id}/approve", headers=csrf_headers(client))
    assert again.status_code == 400
    assert again.json()["message"] == "只有待审核店铺可以执行审核操作。"


def test_admin_pending_list_contains_submitter_and_position(client: TestClient, engine: Engine) -> None:
    """管理员待审核列表包含提交者与位置预览所需字段。"""

    prepare_user(engine, client)
    shop_id = submit_shop(client, "shop_campus").json()["data"]["id"]

    client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    prepare_admin(engine, client)

    response = client.get("/api/v1/admin/shops/pending")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    item = data["items"][0]
    assert item["id"] == shop_id
    assert item["submitter_username"] == USER_USERNAME
    assert item["map_x"] == 0.25
    assert item["map_y"] == 0.35
    assert item["description"] == "用于测试提交与审核流程的店铺。"


def test_owner_can_update_shop_and_it_reenters_pending(client: TestClient, engine: Engine) -> None:
    """核心信息修改后重新进入待审核；其他用户不能修改。"""

    prepare_user(engine, client)
    shop_id = submit_shop(client, "shop_campus").json()["data"]["id"]

    updated = client.patch(
        f"/api/v1/shops/{shop_id}",
        json={"name": "修改后的店铺名称"},
        headers=csrf_headers(client),
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["name"] == "修改后的店铺名称"
    assert updated.json()["data"]["status"] == "pending"

    client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    prepare_admin(engine, client)
    assert client.post(f"/api/v1/admin/shops/{shop_id}/approve", headers=csrf_headers(client)).status_code == 200

    client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    login(client, USER_USERNAME, USER_PASSWORD)
    renamed = client.patch(
        f"/api/v1/shops/{shop_id}",
        json={"name": "再次修改的名称"},
        headers=csrf_headers(client),
    )
    assert renamed.status_code == 200
    assert renamed.json()["data"]["status"] == "pending"
    points = client.get("/api/v1/campuses/shop_campus/shops/points").json()["data"]["items"]
    assert points == []

    # 其他普通用户不能修改他人提交的店铺
    client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    create_user(engine, OTHER_USERNAME, OTHER_PASSWORD)
    login(client, OTHER_USERNAME, OTHER_PASSWORD)
    forbidden = client.patch(
        f"/api/v1/shops/{shop_id}",
        json={"name": "被他人篡改的名称"},
        headers=csrf_headers(client),
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["message"] == "只能修改自己提交的店铺。"


def test_shop_detail_content_and_permissions(client: TestClient, engine: Engine) -> None:
    """验收标准 10、13：登录用户可以读取店铺详情，游客不能。"""

    prepare_user(engine, client)
    shop_id = submit_shop(client, "shop_campus").json()["data"]["id"]

    client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    prepare_admin(engine, client)
    client.post(f"/api/v1/admin/shops/{shop_id}/approve", headers=csrf_headers(client))
    client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    login(client, USER_USERNAME, USER_PASSWORD)

    detail = client.get(f"/api/v1/campuses/shop_campus/shops/{shop_id}")
    assert detail.status_code == 200
    data = detail.json()["data"]
    assert data["name"] == "测试提交店铺"
    assert data["description"] == "用于测试提交与审核流程的店铺。"
    assert data["shop_type"] == "shop"
    assert data["photo_url"] is None
    assert data["status"] == "approved"
    assert data["map_x"] == 0.25
    assert data["rating"] == {
        "average_rating": None,
        "weighted_rating": None,
        "review_count": 0,
        "like_count": 0,
        "dislike_count": 0,
    }


def test_shop_detail_is_login_protected(client: TestClient, engine: Engine) -> None:
    """验收标准 13：游客不能读取店铺详情。"""

    from app.main import app

    prepare_user(engine, client)
    shop_id = submit_shop(client, "shop_campus").json()["data"]["id"]

    with TestClient(app) as guest_client:
        response = guest_client.get(f"/api/v1/campuses/shop_campus/shops/{shop_id}")

    assert response.status_code == 401
    assert response.json()["message"] == "当前操作需要登录。"


def test_shop_detail_rating_summary(client: TestClient, engine: Engine) -> None:
    """店铺详情返回评分统计：平均分、加权评分、有效评价数与互动数。"""

    prepare_user(engine, client)
    shop_id = submit_shop(client, "shop_campus").json()["data"]["id"]
    other_shop_id = submit_shop(client, "shop_campus", name="第二家测试店铺").json()["data"]["id"]
    create_user(engine, "评价用户二", "评价用户密码-2026")
    create_user(engine, "评价用户三", "评价用户密码-2026")
    create_user(engine, "评价用户四", "评价用户密码-2026")

    with Session(engine) as session:
        shop = session.get(Shop, shop_id)
        shop.status = "approved"
        other_shop = session.get(Shop, other_shop_id)
        other_shop.status = "approved"
        session.add_all(
            [
                Review(id=1, shop_id=shop_id, user_id=1, rating=5, content="很好", status="visible"),
                Review(id=2, shop_id=shop_id, user_id=2, rating=3, content="一般", status="visible"),
                Review(id=3, shop_id=shop_id, user_id=3, rating=1, content="隐藏内容", status="hidden"),
                Review(id=4, shop_id=other_shop_id, user_id=1, rating=2, content="较差", status="visible"),
            ]
        )
        session.add_all(
            [
                ReviewReaction(id=1, review_id=1, user_id=2, reaction_type="like"),
                ReviewReaction(id=2, review_id=2, user_id=3, reaction_type="dislike"),
                ReviewReaction(id=3, review_id=3, user_id=4, reaction_type="like"),
            ]
        )
        session.commit()

    detail = client.get(f"/api/v1/campuses/shop_campus/shops/{shop_id}")
    assert detail.status_code == 200
    rating = detail.json()["data"]["rating"]
    assert rating["review_count"] == 2
    assert rating["average_rating"] == 4.0
    # 校园平均分 = (5 + 3 + 2) / 3 = 3.33…，带平滑参数 m = 5 的加权评分应为 3.52
    assert rating["weighted_rating"] == 3.52
    assert rating["like_count"] == 1
    assert rating["dislike_count"] == 1


def test_shop_photo_upload_and_public_access(client: TestClient, engine: Engine, tmp_path, monkeypatch) -> None:
    """验收标准 15：照片上传经过校验，只有已公开店铺的照片可以访问。"""

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "shop_photos"))
    prepare_user(engine, client)

    uploaded = client.post(
        "/api/v1/uploads/shop-photo",
        files={"file": ("photo.png", make_png_bytes(), "image/png")},
        headers=csrf_headers(client),
    )
    assert uploaded.status_code == 200
    photo_url = uploaded.json()["data"]["photo_url"]
    assert photo_url.startswith("/media/shop_photos/")
    filename = photo_url.rsplit("/", 1)[-1]

    # 尚未被公开店铺引用时不可访问
    assert client.get(f"/media/shop_photos/{filename}").status_code == 404

    submitted = submit_shop(client, "shop_campus", photo_url=photo_url)
    assert submitted.status_code == 201
    shop_id = submitted.json()["data"]["id"]
    assert submitted.json()["data"]["photo_url"] == photo_url

    # 待审核店铺的照片同样不可访问
    assert client.get(f"/media/shop_photos/{filename}").status_code == 404

    client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    prepare_admin(engine, client)
    client.post(f"/api/v1/admin/shops/{shop_id}/approve", headers=csrf_headers(client))

    served = client.get(f"/media/shop_photos/{filename}")
    assert served.status_code == 200
    assert len(served.content) > 0


def test_shop_photo_upload_validation(client: TestClient, engine: Engine, tmp_path, monkeypatch) -> None:
    """照片上传校验扩展名、真实内容与大小，并需要登录。"""

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "shop_photos"))

    # 游客不能上传
    guest = client.post(
        "/api/v1/uploads/shop-photo",
        files={"file": ("photo.png", make_png_bytes(), "image/png")},
        headers=csrf_headers(client),
    )
    assert guest.status_code == 401

    prepare_user(engine, client)

    wrong_type = client.post(
        "/api/v1/uploads/shop-photo",
        files={"file": ("photo.txt", b"not an image", "text/plain")},
        headers=csrf_headers(client),
    )
    assert wrong_type.status_code == 415
    assert wrong_type.json()["message"] == "照片只支持 PNG、JPEG 或 WebP 格式。"

    fake_image = client.post(
        "/api/v1/uploads/shop-photo",
        files={"file": ("photo.png", b"not a real image", "image/png")},
        headers=csrf_headers(client),
    )
    assert fake_image.status_code == 415
    assert fake_image.json()["message"] == "文件内容不是有效的图片。"

    oversized = client.post(
        "/api/v1/uploads/shop-photo",
        files={"file": ("photo.png", b"0" * (5 * 1024 * 1024 + 1), "image/png")},
        headers=csrf_headers(client),
    )
    assert oversized.status_code == 413
    assert oversized.json()["message"] == "照片文件不能超过 5 MB。"
