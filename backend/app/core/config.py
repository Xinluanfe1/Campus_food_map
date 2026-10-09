"""后端配置读取。

配置优先从环境变量与 .env 文件读取，未配置时使用本地开发默认值。
"""

import logging
import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# 开发环境未配置 JWT_SECRET 时使用的临时密钥；服务重启后登录状态会失效。
_DEV_FALLBACK_SECRET = secrets.token_urlsafe(48)
_dev_secret_warning_emitted = False


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "校园美食地图"
    version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = True

    api_prefix: str = "/api/v1"
    host: str = "127.0.0.1"
    port: int = 8000

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    database_url: str = "sqlite:///../data/campus_food.db"
    upload_dir: str = "../data/shop_photos"
    map_dir: str = "../data/maps"

    # 初始化管理员密码：仅在初始化脚本创建管理员账号时使用，不写入代码仓库。
    admin_initial_password: str | None = None

    # 认证与安全配置（第三步）
    jwt_secret: str | None = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    # 百度地图 JSAPI 密钥：仅通过环境变量提供，不写入代码仓库。
    # 只有使用百度地图提供方的校园才会读取该值。
    baidu_map_ak: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        """把逗号分隔的前端地址转换为列表。"""

        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def resolved_jwt_secret(self) -> str:
        """返回实际使用的 JWT 密钥。

        生产环境必须通过环境变量提供密钥；开发环境允许使用临时随机密钥，
        但服务重启后已签发的令牌会失效。
        """

        global _dev_secret_warning_emitted

        if self.jwt_secret:
            return self.jwt_secret
        if self.app_env == "production":
            raise RuntimeError("生产环境必须通过环境变量 JWT_SECRET 提供密钥，不能使用默认值。")
        if not _dev_secret_warning_emitted:
            logger.warning("开发环境未配置 JWT_SECRET，已启用临时密钥；重启后端后需要重新登录。")
            _dev_secret_warning_emitted = True
        return _DEV_FALLBACK_SECRET


settings = Settings()
