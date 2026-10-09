"""注册与登录的请求结构。"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RegisterRequest(BaseModel):
    """注册请求：只允许用户名和密码。

    使用 ``extra="forbid"`` 拒绝额外字段，防止客户端提交 role 等敏感字段。
    """

    model_config = ConfigDict(extra="forbid")

    username: str = Field(..., description="用户名，2 至 20 个字符")
    password: str = Field(..., description="密码，至少 8 个字符")

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        username = value.strip()
        if not 2 <= len(username) <= 20:
            raise ValueError("用户名长度需为 2 至 20 个字符。")
        return username

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("密码长度至少为 8 个字符。")
        if len(value) > 128:
            raise ValueError("密码长度不能超过 128 个字符。")
        return value


class LoginRequest(BaseModel):
    """登录请求。"""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        username = value.strip()
        if not username:
            raise ValueError("请输入用户名。")
        return username

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value:
            raise ValueError("请输入密码。")
        return value
