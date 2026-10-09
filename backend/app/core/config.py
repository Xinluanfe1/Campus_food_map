"""后端配置读取。

配置优先从环境变量与 .env 文件读取，未配置时使用本地开发默认值。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    @property
    def cors_origin_list(self) -> list[str]:
        """把逗号分隔的前端地址转换为列表。"""

        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()
