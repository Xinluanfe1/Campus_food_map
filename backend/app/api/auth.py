"""注册、登录、退出与当前用户接口。"""

from fastapi import APIRouter, Request, Response

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.csrf import generate_csrf_token
from app.core.rate_limit import enforce_rate_limit
from app.core.security import ACCESS_TOKEN_COOKIE, CSRF_TOKEN_COOKIE, create_access_token
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.schemas.user import UserPublic
from app.services.auth_service import authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["注册与登录"])

# 本地开发使用的频率限制参数（单实例内存实现）。
REGISTER_RATE_LIMIT = 5
REGISTER_RATE_WINDOW_SECONDS = 900
LOGIN_RATE_LIMIT = 10
LOGIN_RATE_WINDOW_SECONDS = 300


def _client_identity(request: Request) -> str:
    """获取请求来源标识，用于频率限制。"""

    if request.client is not None and request.client.host:
        return request.client.host
    return "unknown"


def _user_payload(user: User) -> dict:
    """把用户对象转换为不含敏感字段的响应数据。"""

    return UserPublic.model_validate(user).model_dump(mode="json")


def _set_auth_cookies(response: Response, user_id: int, role: str) -> None:
    """写入 HttpOnly 认证 Cookie 与前端可读的 CSRF Cookie。"""

    max_age = settings.access_token_expire_minutes * 60
    response.set_cookie(
        ACCESS_TOKEN_COOKIE,
        create_access_token(user_id, role),
        max_age=max_age,
        httponly=True,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        path="/",
    )
    response.set_cookie(
        CSRF_TOKEN_COOKIE,
        generate_csrf_token(),
        max_age=max_age,
        httponly=False,  # 前端需要读取该值并放入 X-CSRF-Token 请求头
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    """清除认证与 CSRF Cookie。"""

    response.delete_cookie(ACCESS_TOKEN_COOKIE, path="/")
    response.delete_cookie(CSRF_TOKEN_COOKIE, path="/")


@router.post("/register", status_code=201, summary="注册普通用户")
def register(payload: RegisterRequest, request: Request, session: DbSession) -> dict:
    enforce_rate_limit(
        "register",
        _client_identity(request),
        REGISTER_RATE_LIMIT,
        REGISTER_RATE_WINDOW_SECONDS,
    )
    user = register_user(session, payload.username, payload.password)
    return {"success": True, "message": "注册成功，请登录。", "data": _user_payload(user)}


@router.post("/login", summary="登录")
def login(payload: LoginRequest, request: Request, response: Response, session: DbSession) -> dict:
    enforce_rate_limit(
        "login",
        _client_identity(request),
        LOGIN_RATE_LIMIT,
        LOGIN_RATE_WINDOW_SECONDS,
    )
    user = authenticate_user(session, payload.username, payload.password)
    _set_auth_cookies(response, user.id, user.role)
    return {"success": True, "message": "登录成功。", "data": _user_payload(user)}


@router.post("/logout", summary="退出登录")
def logout(response: Response, _current_user: CurrentUser) -> dict:
    _clear_auth_cookies(response)
    return {"success": True, "message": "已退出登录。", "data": None}


@router.get("/me", summary="获取当前用户信息")
def read_current_user(current_user: CurrentUser) -> dict:
    return {"success": True, "message": "获取成功", "data": _user_payload(current_user)}
