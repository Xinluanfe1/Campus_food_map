"""静态资源访问：仅允许访问已被校园配置引用的底图文件。"""

import re

from fastapi import APIRouter
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.config import settings
from app.core.errors import BusinessError
from app.db.session import resolve_storage_dir
from app.models import Campus

router = APIRouter(tags=["静态资源"])

SAFE_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@router.get("/assets/maps/{filename}", summary="访问已配置的校园底图")
def read_campus_map(filename: str, session: DbSession) -> FileResponse:
    if not SAFE_FILENAME_PATTERN.match(filename) or ".." in filename:
        raise BusinessError(404, "文件不存在。")

    asset_url = f"/assets/maps/{filename}"
    referenced = session.scalar(select(Campus.campus_id).where(Campus.map_asset_url == asset_url))
    if referenced is None:
        raise BusinessError(404, "该底图未被任何校园配置引用。")

    directory = resolve_storage_dir(settings.map_dir).resolve()
    file_path = (directory / filename).resolve()
    if directory not in file_path.parents or not file_path.is_file():
        raise BusinessError(404, "文件不存在。")

    return FileResponse(file_path)
