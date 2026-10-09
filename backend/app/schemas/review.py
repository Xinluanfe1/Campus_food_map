"""评价、顶踩、回复与举报的请求与响应结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

REACTION_TYPES = {"like", "dislike"}
REACTION_TYPE_MESSAGE = "互动类型只允许 like（点赞）或 dislike（点踩）。"
RESOLVE_ACTION = "hide_review"
RESOLVE_ACTION_MESSAGE = "处理动作只允许 hide_review（隐藏评价）；驳回举报请使用 dismiss 接口。"


class ReviewCreateRequest(BaseModel):
    """创建或更新评价请求（同一用户对同一家店铺只会保留一条主评价）。"""

    model_config = ConfigDict(extra="forbid")

    rating: int = Field(..., description="评分，1 至 5 的整数")
    content: str = Field(..., max_length=2000, description="文字评价")

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, value: int) -> int:
        if not 1 <= value <= 5:
            raise ValueError("评分必须是 1 至 5 的整数。")
        return value

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("评价内容不能为空。")
        return text


class ReviewUpdateRequest(BaseModel):
    """编辑评价请求：至少提供一个字段。"""

    model_config = ConfigDict(extra="forbid")

    rating: int | None = Field(None, description="评分，1 至 5 的整数")
    content: str | None = Field(None, max_length=2000, description="文字评价")

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, value: int | None) -> int | None:
        if value is not None and not 1 <= value <= 5:
            raise ValueError("评分必须是 1 至 5 的整数。")
        return value

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        if not text:
            raise ValueError("评价内容不能为空。")
        return text

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "ReviewUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("请至少提供一个需要修改的字段。")
        return self


class ReactionRequest(BaseModel):
    """设置点赞或点踩请求。"""

    model_config = ConfigDict(extra="forbid")

    reaction_type: str = Field(..., description="互动类型：like 或 dislike")

    @field_validator("reaction_type")
    @classmethod
    def validate_reaction_type(cls, value: str) -> str:
        if value not in REACTION_TYPES:
            raise ValueError(REACTION_TYPE_MESSAGE)
        return value


class ReplyCreateRequest(BaseModel):
    """回复评价请求（只支持一级回复）。"""

    model_config = ConfigDict(extra="forbid")

    content: str = Field(..., max_length=1000, description="回复内容")

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("回复内容不能为空。")
        return text


class ReportCreateRequest(BaseModel):
    """举报评价请求。"""

    model_config = ConfigDict(extra="forbid")

    reason: str = Field(..., max_length=500, description="举报理由")

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("请填写举报理由。")
        return text


class ReportResolveRequest(BaseModel):
    """处理举报请求：隐藏评价并记录处理备注。"""

    model_config = ConfigDict(extra="forbid")

    action: str = Field(RESOLVE_ACTION, description="处理动作，仅允许 hide_review")
    handling_note: str | None = Field(None, max_length=500, description="处理备注")

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        if value != RESOLVE_ACTION:
            raise ValueError(RESOLVE_ACTION_MESSAGE)
        return value

    @field_validator("handling_note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None


class ReportDismissRequest(BaseModel):
    """驳回举报请求：保留评价。"""

    model_config = ConfigDict(extra="forbid")

    handling_note: str | None = Field(None, max_length=500, description="处理备注")

    @field_validator("handling_note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None


class ReviewReplyItem(BaseModel):
    """评价回复列表项。"""

    id: int
    user_id: int
    username: str
    content: str
    created_at: datetime


class ReviewItem(BaseModel):
    """评价列表项：包含互动统计、当前用户互动状态与一级回复。"""

    id: int
    user_id: int
    username: str
    rating: int
    content: str
    created_at: datetime
    updated_at: datetime
    like_count: int
    dislike_count: int
    my_reaction: str | None
    is_mine: bool
    replies: list[ReviewReplyItem]


class ReportItem(BaseModel):
    """举报列表项（管理员）：包含被举报评价、店铺与举报人信息。"""

    id: int
    review_id: int
    review_content: str | None
    review_status: str | None
    shop_id: int | None
    shop_name: str | None
    reporter_id: int
    reporter_username: str
    reason: str
    status: str
    handled_by: int | None
    handled_at: datetime | None
    handling_note: str | None
    created_at: datetime
