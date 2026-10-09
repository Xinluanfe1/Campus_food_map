"""密码哈希与 JWT 令牌处理。"""

from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

# Cookie 与请求头名称集中定义，前后端与测试统一引用。
ACCESS_TOKEN_COOKIE = "access_token"
CSRF_TOKEN_COOKIE = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"

JWT_ISSUER = "campus-food-map"

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """生成 Argon2id 密码哈希，数据库不保存明文密码。"""

    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """校验密码与哈希是否匹配，哈希格式异常时按校验失败处理。"""

    try:
        return password_hasher.verify(password, password_hash)
    except Exception:  # noqa: BLE001 - 任何哈希异常都视为校验失败
        return False


def create_access_token(user_id: int, role: str) -> str:
    """签发 JWT 访问令牌。"""

    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iss": JWT_ISSUER,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.resolved_jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    """解析 JWT；令牌无效或过期时返回 None。"""

    try:
        return jwt.decode(
            token,
            settings.resolved_jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=JWT_ISSUER,
        )
    except jwt.PyJWTError:
        return None
