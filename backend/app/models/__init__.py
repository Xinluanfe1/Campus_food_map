"""数据库模型汇总：导入全部实体，保证元数据完整。"""

from app.models.campus import Campus
from app.models.report import Report
from app.models.review import Review
from app.models.review_reaction import ReviewReaction
from app.models.review_reply import ReviewReply
from app.models.shop import Shop
from app.models.user import User

__all__ = [
    "Campus",
    "Report",
    "Review",
    "ReviewReaction",
    "ReviewReply",
    "Shop",
    "User",
]
