"""图片上传与校验（校园底图）。"""

import io
import uuid
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.core.errors import BusinessError
from app.db.session import resolve_storage_dir

# 扩展名与真实图片格式必须一致，避免伪造扩展名绕过校验。
EXTENSION_FORMATS: dict[str, str] = {
    ".png": "PNG",
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".webp": "WEBP",
}
FORMAT_EXTENSIONS = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_SIDE = 8000
MIN_IMAGE_SIDE = 200


def save_campus_map(upload: UploadFile) -> dict[str, object]:
    """校验并保存校园底图，返回公开访问地址与图片尺寸。"""

    original_name = upload.filename or ""
    extension = Path(original_name).suffix.lower()
    if extension not in EXTENSION_FORMATS:
        raise BusinessError(415, "底图只支持 PNG、JPEG 或 WebP 格式。")

    content = upload.file.read(MAX_FILE_SIZE_BYTES + 1)
    if not content:
        raise BusinessError(400, "上传文件为空，请重新选择图片。")
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise BusinessError(413, "底图文件不能超过 5 MB。")

    try:
        with Image.open(io.BytesIO(content)) as image:
            image.verify()
        with Image.open(io.BytesIO(content)) as image:
            width, height = image.size
            image_format = image.format
    except (UnidentifiedImageError, OSError) as error:
        raise BusinessError(415, "文件内容不是有效的图片。") from error

    if image_format is None or image_format not in FORMAT_EXTENSIONS:
        raise BusinessError(415, "底图只支持 PNG、JPEG 或 WebP 格式。")
    if EXTENSION_FORMATS[extension] != image_format:
        raise BusinessError(415, "文件扩展名与图片实际格式不一致。")
    if width < MIN_IMAGE_SIDE or height < MIN_IMAGE_SIDE:
        raise BusinessError(400, "底图宽高不能小于 200 像素。")
    if width > MAX_IMAGE_SIDE or height > MAX_IMAGE_SIDE:
        raise BusinessError(400, "底图宽高不能超过 8000 像素。")

    target_directory = resolve_storage_dir(settings.map_dir)
    target_directory.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{FORMAT_EXTENSIONS[image_format]}"
    (target_directory / stored_name).write_bytes(content)

    return {
        "map_asset_url": f"/assets/maps/{stored_name}",
        "image_width": width,
        "image_height": height,
    }
