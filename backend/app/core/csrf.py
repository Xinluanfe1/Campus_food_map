"""CSRF 防护：双提交 Cookie 方案。

服务端下发可被前端读取的 csrf_token Cookie（非 HttpOnly），前端在所有写操作中
通过 X-CSRF-Token 请求头回传相同值，服务端比较两者是否一致，防止跨站请求伪造。
注册与登录接口没有已登录状态，因此不参与 CSRF 校验，但受频率限制约束。
"""

import hmac
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.security import CSRF_HEADER_NAME, CSRF_TOKEN_COOKIE

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_EXEMPT_PATHS = {"/api/v1/auth/register", "/api/v1/auth/login"}
API_PREFIX = "/api/v1"


def generate_csrf_token() -> str:
    """生成随机 CSRF 令牌。"""

    return secrets.token_urlsafe(32)


class CsrfProtectionMiddleware(BaseHTTPMiddleware):
    """校验写操作的 CSRF 令牌，并确保前端能拿到 CSRF Cookie。"""

    async def dispatch(self, request: Request, call_next) -> Response:  # noqa: ANN001
        path = request.url.path
        needs_check = (
            path.startswith(API_PREFIX)
            and request.method not in SAFE_METHODS
            and path not in CSRF_EXEMPT_PATHS
        )

        if needs_check:
            cookie_token = request.cookies.get(CSRF_TOKEN_COOKIE)
            header_token = request.headers.get(CSRF_HEADER_NAME)
            if (
                not cookie_token
                or not header_token
                or not hmac.compare_digest(cookie_token, header_token)
            ):
                return JSONResponse(
                    status_code=403,
                    content={
                        "success": False,
                        "message": "请求校验失败，请刷新页面后重试。",
                        "data": None,
                    },
                )

        response = await call_next(request)

        csrf_cookie_already_set = any(
            header_name.decode("latin-1").lower() == "set-cookie"
            and CSRF_TOKEN_COOKIE in header_value.decode("latin-1")
            for header_name, header_value in getattr(response, "raw_headers", [])
        )
        if (
            path.startswith(API_PREFIX)
            and not request.cookies.get(CSRF_TOKEN_COOKIE)
            and not csrf_cookie_already_set
        ):
            response.set_cookie(
                CSRF_TOKEN_COOKIE,
                generate_csrf_token(),
                max_age=settings.access_token_expire_minutes * 60,
                httponly=False,
                samesite=settings.cookie_samesite,
                secure=settings.cookie_secure,
                path="/",
            )

        return response
