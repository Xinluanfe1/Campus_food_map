"""认证业务逻辑：注册与登录校验。"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import BusinessError
from app.core.security import hash_password, verify_password
from app.models import User

DUPLICATE_USERNAME_MESSAGE = "该用户名已被使用，请更换后重试。"


def register_user(session: Session, username: str, password: str) -> User:
    """注册普通用户。

    注册接口固定创建 ``user`` 角色，客户端无法指定管理员角色；
    用户名重复时返回 409（提交事务，避免并发下产生重复账号）。
    """

    existing_user = session.scalar(select(User).where(User.username == username))
    if existing_user is not None:
        raise BusinessError(409, DUPLICATE_USERNAME_MESSAGE)

    user = User(
        username=username,
        password_hash=hash_password(password),
        role="user",
        is_active=True,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as error:  # 数据库唯一约束兜底
        session.rollback()
        raise BusinessError(409, DUPLICATE_USERNAME_MESSAGE) from error

    session.refresh(user)
    return user


def authenticate_user(session: Session, username: str, password: str) -> User:
    """校验用户名与密码，失败时返回 401 中文错误。"""

    user = session.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.password_hash):
        raise BusinessError(401, "用户名或密码错误。")
    if not user.is_active:
        raise BusinessError(403, "账号已被停用，请联系管理员。")
    return user
