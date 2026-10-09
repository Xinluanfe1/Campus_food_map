"""注册、登录、退出与权限测试：对应第三步验收标准。"""

from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models import Campus, Shop, User

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
LOGOUT_URL = "/api/v1/auth/logout"
ME_URL = "/api/v1/auth/me"
MY_SHOPS_URL = "/api/v1/users/me/shops"
PENDING_SHOPS_URL = "/api/v1/admin/shops/pending"

USERNAME = "测试新用户"
PASSWORD = "本地测试密码-2026"
ADMIN_PASSWORD = "管理员测试密码-2026"


def register(client: TestClient, username: str = USERNAME, password: str = PASSWORD):
    return client.post(REGISTER_URL, json={"username": username, "password": password})


def login(client: TestClient, username: str = USERNAME, password: str = PASSWORD):
    return client.post(LOGIN_URL, json={"username": username, "password": password})


def create_user(
    engine: Engine,
    username: str,
    password: str,
    role: str = "user",
    is_active: bool = True,
) -> int:
    """直接写入一个用户记录，用于测试管理员与非启用账号场景。"""

    with Session(engine) as session:
        user = User(
            username=username,
            password_hash=hash_password(password),
            role=role,
            is_active=is_active,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.id


def create_pending_shop(engine: Engine, submitted_by: int) -> None:
    """写入一个待审核店铺，用于管理员接口测试。"""

    with Session(engine) as session:
        session.add(
            Campus(
                campus_id="swjtu_xipu",
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
        )
        session.commit()
        session.add(
            Shop(
                id=1,
                campus_id="swjtu_xipu",
                name="待审核测试店铺",
                description="用于测试管理员权限的店铺。",
                shop_type="shop",
                submitted_by=submitted_by,
                status="pending",
                map_x=0.3,
                map_y=0.4,
            )
        )
        session.commit()


def test_register_creates_normal_user(client: TestClient, engine: Engine) -> None:
    """验收标准 1、3、9：可以注册普通账号，密码以哈希形式保存。"""

    response = register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert "注册成功" in body["message"]
    assert body["data"]["username"] == USERNAME
    assert body["data"]["role"] == "user"
    assert "password" not in body["data"]
    # 时间字段必须按 ISO 8601 返回并带 UTC 标识
    assert body["data"]["created_at"].endswith("Z")

    with Session(engine) as session:
        user = session.scalar(select(User).where(User.username == USERNAME))
        assert user is not None
        assert user.password_hash != PASSWORD
        assert user.password_hash.startswith("$argon2")


def test_register_rejects_duplicate_username(client: TestClient) -> None:
    """验收标准 2：用户名重复时拒绝注册并返回 409 中文提示。"""

    assert register(client).status_code == 201
    response = register(client)

    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert body["message"] == "该用户名已被使用，请更换后重试。"
    assert body["data"] is None


def test_register_rejects_role_field(client: TestClient, engine: Engine) -> None:
    """验收标准 8：普通用户不能在注册请求中指定管理员角色。"""

    response = client.post(
        REGISTER_URL,
        json={"username": "非法管理员", "password": PASSWORD, "role": "admin"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "请求参数校验失败" in body["message"]
    assert body["data"]["errors"][0]["message"] == "请求包含不允许的字段。"

    with Session(engine) as session:
        assert session.scalar(select(User).where(User.username == "非法管理员")) is None


def test_register_validates_input_with_chinese_messages(client: TestClient) -> None:
    """所有输入校验错误必须返回中文提示。"""

    short_username = client.post(REGISTER_URL, json={"username": "a", "password": PASSWORD})
    assert short_username.status_code == 422
    assert (
        short_username.json()["data"]["errors"][0]["message"] == "用户名长度需为 2 至 20 个字符。"
    )

    short_password = client.post(REGISTER_URL, json={"username": "合法用户名", "password": "123"})
    assert short_password.status_code == 422
    assert short_password.json()["data"]["errors"][0]["message"] == "密码长度至少为 8 个字符。"

    missing_password = client.post(REGISTER_URL, json={"username": "合法用户名"})
    assert missing_password.status_code == 422
    assert missing_password.json()["data"]["errors"][0]["message"] == "缺少必填字段。"


def test_login_rejects_wrong_password(client: TestClient) -> None:
    """登录失败返回 401 中文提示。"""

    assert register(client).status_code == 201
    response = login(client, password="错误的密码-2026")

    assert response.status_code == 401
    assert response.json()["message"] == "用户名或密码错误。"


def test_login_sets_secure_cookies(client: TestClient) -> None:
    """验收标准 4：登录成功写入 HttpOnly 认证 Cookie 与 CSRF Cookie。"""

    assert register(client).status_code == 201
    response = login(client)

    assert response.status_code == 200
    assert response.json()["data"]["role"] == "user"

    set_cookie_headers = response.headers.get_list("set-cookie")
    access_cookie = next(item for item in set_cookie_headers if item.startswith("access_token="))
    csrf_cookie = next(item for item in set_cookie_headers if item.startswith("csrf_token="))

    assert "HttpOnly" in access_cookie
    assert "SameSite=lax" in access_cookie
    assert "HttpOnly" not in csrf_cookie


def test_me_requires_login(client: TestClient) -> None:
    """验收标准 6：未登录访问受保护接口返回 401，且响应格式统一。"""

    response = client.get(ME_URL)

    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["message"] == "当前操作需要登录。"
    assert body["data"] is None


def test_login_me_logout_flow(client: TestClient) -> None:
    """验收标准 4、5：登录后可获取当前用户信息，退出后登录状态失效。"""

    assert register(client).status_code == 201
    assert login(client).status_code == 200

    me_response = client.get(ME_URL)
    assert me_response.status_code == 200
    me_body = me_response.json()
    assert me_body["data"]["username"] == USERNAME
    assert me_body["data"]["role"] == "user"
    assert "password_hash" not in me_body["data"]

    # 缺少 CSRF 请求头时拒绝退出，防止跨站伪造请求。
    without_csrf = client.post(LOGOUT_URL)
    assert without_csrf.status_code == 403
    assert without_csrf.json()["message"] == "请求校验失败，请刷新页面后重试。"

    csrf_token = client.cookies.get("csrf_token")
    logout_response = client.post(LOGOUT_URL, headers={"X-CSRF-Token": csrf_token})
    assert logout_response.status_code == 200
    assert logout_response.json()["message"] == "已退出登录。"

    assert client.get(ME_URL).status_code == 401


def test_tampered_or_forged_token_is_rejected(client: TestClient) -> None:
    """损坏的令牌与用错误密钥伪造的令牌都不能通过认证。"""

    with TestClient(app) as anonymous_client:
        malformed = anonymous_client.get(
            ME_URL,
            headers={"Cookie": "access_token=invalid-token-value"},
        )
    assert malformed.status_code == 401
    assert malformed.json()["message"] == "登录状态已失效，请重新登录。"

    forged_token = jwt.encode(
        {
            "sub": "1",
            "role": "admin",
            "iss": "campus-food-map",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        "这是一个长度足够的伪造密钥-仅用于自动化测试-0123456789",
        algorithm="HS256",
    )
    with TestClient(app) as anonymous_client:
        forged = anonymous_client.get(
            ME_URL,
            headers={"Cookie": f"access_token={forged_token}"},
        )
    assert forged.status_code == 401


def test_inactive_user_cannot_login(client: TestClient, engine: Engine) -> None:
    """被停用的账号不能登录。"""

    create_user(engine, username="停用账号", password=PASSWORD, is_active=False)
    response = login(client, username="停用账号")

    assert response.status_code == 403
    assert response.json()["message"] == "账号已被停用，请联系管理员。"


def test_protected_user_endpoint_requires_login(client: TestClient) -> None:
    """受保护的用户接口在未登录时返回 401，登录后可正常访问。"""

    assert client.get(MY_SHOPS_URL).status_code == 401

    assert register(client).status_code == 201
    assert login(client).status_code == 200

    response = client.get(MY_SHOPS_URL)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["items"] == []
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total"] == 0


def test_ordinary_user_cannot_access_admin_endpoint(client: TestClient) -> None:
    """验收标准 7：普通用户访问管理员接口返回 403。"""

    assert register(client).status_code == 201
    assert login(client).status_code == 200

    response = client.get(PENDING_SHOPS_URL)

    assert response.status_code == 403
    assert response.json()["message"] == "当前操作需要管理员权限。"


def test_admin_can_access_admin_endpoint(client: TestClient, engine: Engine) -> None:
    """管理员可以访问管理员接口，普通用户与游客不能。"""

    admin_id = create_user(engine, username="测试管理员", password=ADMIN_PASSWORD, role="admin")
    create_pending_shop(engine, submitted_by=admin_id)

    assert login(client, username="测试管理员", password=ADMIN_PASSWORD).status_code == 200
    response = client.get(PENDING_SHOPS_URL)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["name"] == "待审核测试店铺"
    assert data["items"][0]["status"] == "pending"


def test_login_rate_limit(client: TestClient) -> None:
    """登录接口具备频率限制，超出后返回 429 中文提示。"""

    responses = [login(client, username="不存在的用户", password=PASSWORD) for _ in range(11)]

    assert all(response.status_code == 401 for response in responses[:10])
    assert responses[10].status_code == 429
    assert responses[10].json()["message"] == "操作过于频繁，请稍后再试。"
