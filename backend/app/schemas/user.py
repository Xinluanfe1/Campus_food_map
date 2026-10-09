"""用户相关的响应结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserPublic(BaseModel):
    """对外的用户信息，不包含密码哈希等敏感字段。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    is_active: bool
    created_at: datetime
