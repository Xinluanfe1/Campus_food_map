"""店铺提交、修改、审核与详情构造。"""

import re

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import BusinessError
from app.db.base import utc_now
from app.db.session import resolve_storage_dir
from app.models import Campus, Shop, User
from app.schemas.shop import RatingSummary, ShopDetailData, ShopSubmitRequest, ShopUpdateRequest
from app.services.campus_service import is_point_off_campus
from app.services.rating_service import shop_rating_summary

PHOTO_URL_PATTERN = re.compile(r"^/media/shop_photos/[A-Za-z0-9][A-Za-z0-9._-]*$")
CORE_FIELDS = ("name", "description", "shop_type")
COORDINATE_FIELDS = ("map_x", "map_y", "latitude", "longitude")


def _validate_photo_url(photo_url: str | None) -> str | None:
    """校验照片路径格式，并确认文件真实存在于上传目录。"""

    if photo_url is None:
        return None
    if not PHOTO_URL_PATTERN.match(photo_url):
        raise BusinessError(422, "照片路径不合法，请重新上传照片。")

    filename = photo_url.rsplit("/", 1)[-1]
    file_path = resolve_storage_dir(settings.upload_dir) / filename
    if not file_path.is_file():
        raise BusinessError(422, "照片文件不存在，请重新上传。")
    return photo_url


def _validate_coordinates(payload, campus: Campus) -> dict[str, float | None]:  # noqa: ANN001
    """按校园底图类型校验坐标，返回写入数据库的坐标字段。"""

    if campus.map_type == "image":
        if payload.map_x is None or payload.map_y is None:
            raise BusinessError(422, "该校园使用图片底图，请在地图上选择点位。")
        if payload.latitude is not None or payload.longitude is not None:
            raise BusinessError(422, "图片底图模式不能提交经纬度坐标。")
        return {"map_x": payload.map_x, "map_y": payload.map_y, "latitude": None, "longitude": None}

    if payload.latitude is None or payload.longitude is None:
        raise BusinessError(422, "该校园使用真实地图，请在地图上选择位置。")
    if payload.map_x is not None or payload.map_y is not None:
        raise BusinessError(422, "真实地图模式不能提交图片坐标。")
    if is_point_off_campus(campus, payload.latitude, payload.longitude):
        raise BusinessError(422, "店铺位置超出校园范围，请重新选择点位。")
    return {"map_x": None, "map_y": None, "latitude": payload.latitude, "longitude": payload.longitude}


def get_shop_or_404(session: Session, shop_id: int) -> Shop:
    """按主键读取店铺，不存在时返回 404 中文错误。"""

    shop = session.get(Shop, shop_id)
    if shop is None:
        raise BusinessError(404, "店铺不存在。")
    return shop


def create_shop(session: Session, campus: Campus, user: User, payload: ShopSubmitRequest) -> Shop:
    """提交新店铺：状态固定为待审核，客户端不能指定审核状态。"""

    coordinates = _validate_coordinates(payload, campus)
    shop = Shop(
        campus_id=campus.campus_id,
        name=payload.name,
        description=payload.description,
        shop_type=payload.shop_type,
        photo_url=_validate_photo_url(payload.photo_url),
        submitted_by=user.id,
        status="pending",
        **coordinates,
    )
    session.add(shop)
    session.commit()
    session.refresh(shop)
    return shop


def update_shop(session: Session, shop: Shop, user: User, payload: ShopUpdateRequest) -> Shop:
    """修改店铺：仅提交者或管理员可以操作，核心信息变化后重新进入待审核。"""

    if user.role != "admin" and shop.submitted_by != user.id:
        raise BusinessError(403, "只能修改自己提交的店铺。")

    campus = session.get(Campus, shop.campus_id)
    if campus is None:
        raise BusinessError(404, "店铺所属校园不存在。")

    updates: dict[str, object] = {}
    core_changed = False

    for field in CORE_FIELDS:
        value = getattr(payload, field)
        if value is not None and value != getattr(shop, field):
            updates[field] = value
            core_changed = True

    if any(getattr(payload, field) is not None for field in COORDINATE_FIELDS):
        for field, value in _validate_coordinates(payload, campus).items():
            if value != getattr(shop, field):
                updates[field] = value
                core_changed = True

    if payload.photo_url is not None and payload.photo_url != shop.photo_url:
        updates["photo_url"] = _validate_photo_url(payload.photo_url)

    if core_changed:
        # 名称、简介、类型或位置变化后必须重新审核，避免已公开内容被直接替换。
        updates.update(
            {
                "status": "pending",
                "reviewed_by": None,
                "reviewed_at": None,
                "rejection_reason": None,
            }
        )

    for field, value in updates.items():
        setattr(shop, field, value)

    session.commit()
    session.refresh(shop)
    return shop


def get_visible_shop(session: Session, campus: Campus, shop_id: int, user: User) -> Shop:
    """读取店铺详情：公开店铺所有登录用户可见，未公开店铺只有提交者和管理员可见。"""

    shop = session.get(Shop, shop_id)
    if shop is None or shop.campus_id != campus.campus_id:
        raise BusinessError(404, "店铺不存在或未公开。")
    if shop.status != "approved" and user.role != "admin" and shop.submitted_by != user.id:
        raise BusinessError(404, "店铺不存在或未公开。")
    return shop


def approve_shop(session: Session, shop_id: int, admin: User) -> Shop:
    """管理员审核通过店铺。"""

    shop = get_shop_or_404(session, shop_id)
    if shop.status != "pending":
        raise BusinessError(400, "只有待审核店铺可以执行审核操作。")

    shop.status = "approved"
    shop.reviewed_by = admin.id
    shop.reviewed_at = utc_now()
    shop.rejection_reason = None
    session.commit()
    session.refresh(shop)
    return shop


def reject_shop(session: Session, shop_id: int, admin: User, reason: str) -> Shop:
    """管理员拒绝店铺并记录拒绝原因。"""

    shop = get_shop_or_404(session, shop_id)
    if shop.status != "pending":
        raise BusinessError(400, "只有待审核店铺可以执行审核操作。")

    shop.status = "rejected"
    shop.reviewed_by = admin.id
    shop.reviewed_at = utc_now()
    shop.rejection_reason = reason
    session.commit()
    session.refresh(shop)
    return shop


def build_detail_payload(session: Session, shop: Shop, map_type: str) -> dict:
    """构造店铺详情响应：按校园底图类型只返回对应坐标，并附带评分统计。"""

    rating = shop_rating_summary(session, shop)
    coordinates = (
        {"map_x": shop.map_x, "map_y": shop.map_y}
        if map_type == "image"
        else {"latitude": shop.latitude, "longitude": shop.longitude}
    )
    average_rating = rating["average_rating"]
    weighted_rating = rating["weighted_rating"]

    return ShopDetailData(
        id=shop.id,
        campus_id=shop.campus_id,
        name=shop.name,
        description=shop.description,
        shop_type=shop.shop_type,
        photo_url=shop.photo_url,
        status=shop.status,
        created_at=shop.created_at,
        updated_at=shop.updated_at,
        rating=RatingSummary(
            average_rating=round(float(average_rating), 2) if average_rating is not None else None,
            weighted_rating=round(float(weighted_rating), 2) if weighted_rating is not None else None,
            review_count=int(rating["review_count"]),
            like_count=int(rating["like_count"]),
            dislike_count=int(rating["dislike_count"]),
        ),
        **coordinates,
    ).model_dump(mode="json")
