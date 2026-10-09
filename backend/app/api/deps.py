"""API 依赖：数据库会话、当前用户与管理员权限校验。"""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.errors import BusinessError
from app.core.security import ACCESS_TOKEN_COOKIE, decode_access_token
from app.db.session import get_session
from app.models import User

DbSession = Annotated[Session, Depends(get_session)]


def get_current_user(request: Request, session: DbSession) -> User:
    """从 HttpOnly Cookie 解析当前登录用户；未登录或令牌无效时返回 401。"""

    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if not token:
        raise BusinessError(401, "当前操作需要登录。")

    payload = decode_access_token(token)
    if payload is None:
        raise BusinessError(401, "登录状态已失效，请重新登录。")

    try:
        user_id = int(payload.get("sub", ""))
    except (TypeError, ValueError) as error:
        raise BusinessError(401, "登录状态已失效，请重新登录。") from error

    user = session.get(User, user_id)
    if user is None:
        raise BusinessError(401, "登录状态已失效，请重新登录。")
    if not user.is_active:
        raise BusinessError(403, "账号已被停用，请联系管理员。")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(current_user: CurrentUser) -> User:
    """管理员角色校验；普通用户访问管理员接口时返回 403。"""

    if current_user.role != "admin":
        raise BusinessError(403, "当前操作需要管理员权限。")
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]
