"""权限矩阵回归测试：对应第八步验收标准 9（不存在明显的越权访问）。"""

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Campus, Review, Shop, User

ORDINARY_USERNAME = "权限普通用户"
ORDINARY_PASSWORD = "权限普通用户密码-2026"
OTHER_USERNAME = "权限其他用户"
OTHER_PASSWORD = "权限其他用户密码-2026"


def setup_data(engine: Engine) -> None:
    with Session(engine) as session:
        session.add(
            Campus(
                campus_id="perm_campus",
                campus_name="权限测试校园",
                map_type="image",
                map_asset_url="/assets/maps/perm.png",
                map_attribution="权限测试署名",
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
                username="权限店铺作者",
                password_hash=hash_password("权限店铺作者密码-2026"),
                role="user",
                is_active=True,
            )
        )
        session.add(
            User(
                id=2,
                username=ORDINARY_USERNAME,
                password_hash=hash_password(ORDINARY_PASSWORD),
                role="user",
                is_active=True,
            )
        )
        session.add(
            User(
                id=3,
                username=OTHER_USERNAME,
                password_hash=hash_password(OTHER_PASSWORD),
                role="user",
                is_active=True,
            )
        )
        session.commit()
        session.add(
            Shop(
                id=1201,
                campus_id="perm_campus",
                name="权限测试店铺",
                description="用于权限测试的店铺。",
                shop_type="shop",
                submitted_by=1,
                status="approved",
                map_x=0.4,
                map_y=0.5,
            )
        )
        session.commit()
        session.add(
            Review(
                id=1201,
                shop_id=1201,
                user_id=1,
                rating=5,
                content="权限测试评价。",
                status="visible",
            )
        )
        session.commit()


GUEST_401_ENDPOINTS = (
    ("GET", "/api/v1/shops/1201/reviews"),
    ("GET", "/api/v1/campuses/perm_campus/shops/1201"),
    ("GET", "/api/v1/campuses/perm_campus/rankings/shops"),
    ("GET", "/api/v1/campuses/perm_campus/rankings/contributors"),
    ("GET", "/api/v1/campuses/perm_campus/search?q=权限"),
    ("GET", "/api/v1/users/me/shops"),
    ("GET", "/api/v1/users/me/contributions"),
    ("GET", "/api/v1/admin/shops/pending"),
    ("GET", "/api/v1/admin/reports"),
)

GUEST_WRITE_ENDPOINTS = (
    ("POST", "/api/v1/shops/1201/reviews"),
    ("POST", "/api/v1/reviews/1201/replies"),
    ("POST", "/api/v1/reviews/1201/reports"),
    ("PUT", "/api/v1/reviews/1201/reaction"),
    ("PATCH", "/api/v1/reviews/1201"),
    ("DELETE", "/api/v1/reviews/1201"),
    ("POST", "/api/v1/admin/shops/1201/approve"),
    ("POST", "/api/v1/admin/reports/1/dismiss"),
    ("PUT", "/api/v1/admin/campuses/perm_campus/map"),
    ("POST", "/api/v1/admin/campuses"),
)


def csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get("csrf_token")
    if token is None:
        client.get("/api/v1/health")
        token = client.cookies.get("csrf_token")
    return {"X-CSRF-Token": token or ""}


def test_guest_is_rejected_everywhere(client: TestClient, engine: Engine) -> None:
    """游客访问受保护接口一律返回 401。"""

    setup_data(engine)

    for method, url in GUEST_401_ENDPOINTS:
        response = client.request(method, url, headers=csrf_headers(client))
        assert response.status_code == 401, f"{method} {url} 返回了 {response.status_code}"

    for method, url in GUEST_WRITE_ENDPOINTS:
        response = client.request(method, url, json={}, headers=csrf_headers(client))
        assert response.status_code == 401, f"{method} {url} 返回了 {response.status_code}"


def test_ordinary_user_cannot_access_admin_endpoints(client: TestClient, engine: Engine) -> None:
    """普通用户访问管理员接口一律返回 403。"""

    setup_data(engine)
    login = client.post(
        "/api/v1/auth/login",
        json={"username": ORDINARY_USERNAME, "password": ORDINARY_PASSWORD},
    )
    assert login.status_code == 200

    admin_reads = (
        "/api/v1/admin/shops/pending",
        "/api/v1/admin/reports",
    )
    for url in admin_reads:
        response = client.get(url)
        assert response.status_code == 403
        assert response.json()["message"] == "当前操作需要管理员权限。"

    admin_writes = (
        ("POST", "/api/v1/admin/shops/1201/approve"),
        ("POST", "/api/v1/admin/reports/1/dismiss"),
        ("PUT", "/api/v1/admin/campuses/perm_campus/map"),
        ("POST", "/api/v1/admin/campuses"),
    )
    for method, url in admin_writes:
        response = client.request(method, url, json={}, headers=csrf_headers(client))
        assert response.status_code == 403, f"{method} {url} 返回了 {response.status_code}"


def test_ordinary_user_cannot_modify_others_content(client: TestClient, engine: Engine) -> None:
    """普通用户不能修改他人的店铺或评价。"""

    setup_data(engine)
    login = client.post(
        "/api/v1/auth/login",
        json={"username": OTHER_USERNAME, "password": OTHER_PASSWORD},
    )
    assert login.status_code == 200

    shop_update = client.patch(
        "/api/v1/shops/1201",
        json={"name": "被篡改的名称"},
        headers=csrf_headers(client),
    )
    assert shop_update.status_code == 403
    assert shop_update.json()["message"] == "只能修改自己提交的店铺。"

    review_update = client.patch(
        "/api/v1/reviews/1201",
        json={"rating": 1},
        headers=csrf_headers(client),
    )
    assert review_update.status_code == 403
    assert review_update.json()["message"] == "只能修改或删除自己的评价。"

    review_delete = client.delete("/api/v1/reviews/1201", headers=csrf_headers(client))
    assert review_delete.status_code == 403
