"""校园配置读取、点位查询与管理操作。"""

import json
import math
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import BusinessError
from app.models import Campus, Shop
from app.schemas.campus import CampusCreateRequest, CampusMapUpdateRequest, CampusPatchRequest

EARTH_RADIUS_METERS = 6371000.0


def haversine_meters(latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float) -> float:
    """计算两个经纬度点之间的球面距离（米）。"""

    phi_a = math.radians(latitude_a)
    phi_b = math.radians(latitude_b)
    delta_phi = math.radians(latitude_b - latitude_a)
    delta_lambda = math.radians(longitude_b - longitude_a)
    haversine = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi_a) * math.cos(phi_b) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_METERS * math.asin(math.sqrt(haversine))


def list_active_campuses(session: Session) -> list[Campus]:
    """返回允许公开访问的校园列表。"""

    return list(
        session.scalars(
            select(Campus)
            .where(Campus.is_active.is_(True))
            .order_by(Campus.created_at.asc(), Campus.campus_id.asc())
        ).all()
    )


def get_campus(session: Session, campus_id: str, *, include_inactive: bool = False) -> Campus:
    """按标识读取校园；未开放或不存在时返回 404 中文错误。"""

    campus = session.get(Campus, campus_id)
    if campus is None:
        raise BusinessError(404, "校园不存在。")
    if not campus.is_active and not include_inactive:
        raise BusinessError(404, "该校园当前未开放访问。")
    return campus


def is_off_campus(campus: Campus, shop: Shop) -> bool:
    """判断真实地图模式下店铺是否超出校园配置的范围半径。"""

    if campus.allow_off_campus or campus.boundary_radius_meters is None:
        return False
    if campus.default_latitude is None or campus.default_longitude is None:
        return False
    if shop.latitude is None or shop.longitude is None:
        return False

    distance = haversine_meters(
        campus.default_latitude,
        campus.default_longitude,
        shop.latitude,
        shop.longitude,
    )
    return distance > campus.boundary_radius_meters


def list_public_shop_points(session: Session, campus: Campus) -> list[Shop]:
    """查询公开点位：只返回审核通过的店铺，并按校园底图类型过滤坐标。"""

    shops = session.scalars(
        select(Shop)
        .where(Shop.campus_id == campus.campus_id, Shop.status == "approved")
        .order_by(Shop.id.asc())
    ).all()

    visible: list[Shop] = []
    for shop in shops:
        if campus.map_type == "image":
            # 图片模式只展示落在底图范围内的点位（坐标范围由数据库约束保证）。
            if shop.map_x is not None and shop.map_y is not None:
                visible.append(shop)
        elif shop.latitude is not None and shop.longitude is not None:
            if not is_off_campus(campus, shop):
                visible.append(shop)
    return visible


def create_campus(session: Session, payload: CampusCreateRequest) -> Campus:
    """新增校园配置（管理员）。"""

    if session.get(Campus, payload.campus_id) is not None:
        raise BusinessError(409, "该校园标识已存在，请更换后重试。")

    campus = Campus(**payload.model_dump())
    session.add(campus)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise BusinessError(400, "校园配置不符合数据库校验规则，请检查后重试。") from error
    session.refresh(campus)
    return campus


def update_campus_map(session: Session, campus_id: str, payload: CampusMapUpdateRequest) -> Campus:
    """更新校园地图配置（管理员，完整替换地图相关字段）。"""

    campus = get_campus(session, campus_id, include_inactive=True)
    for field, value in payload.model_dump().items():
        setattr(campus, field, value)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise BusinessError(400, "校园地图配置不符合数据库校验规则，请检查后重试。") from error
    session.refresh(campus)
    return campus


def patch_campus(session: Session, campus_id: str, payload: CampusPatchRequest) -> Campus:
    """修改校园基本信息与展示状态（管理员）。"""

    campus = get_campus(session, campus_id, include_inactive=True)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(campus, field, value)
    session.commit()
    session.refresh(campus)
    return campus


def import_campuses_from_directory(session: Session, directory: Path) -> dict[str, list[str]]:
    """从配置文件目录导入或更新校园（幂等，用于更换校园时无需修改业务代码）。"""

    created: list[str] = []
    updated: list[str] = []

    for path in sorted(directory.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        try:
            payload = CampusCreateRequest.model_validate(raw)
        except ValidationError as error:
            first_error = error.errors()[0]
            message = str(first_error.get("msg", "配置不合法")).removeprefix("Value error, ")
            raise BusinessError(400, f"校园配置文件 {path.name} 校验失败：{message}") from error

        campus = session.get(Campus, payload.campus_id)
        if campus is None:
            session.add(Campus(**payload.model_dump()))
            created.append(payload.campus_id)
        else:
            for field, value in payload.model_dump().items():
                setattr(campus, field, value)
            updated.append(payload.campus_id)

    session.commit()
    return {"created": created, "updated": updated}
