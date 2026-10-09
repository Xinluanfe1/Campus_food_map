"""图片上传与校验（校园底图与店铺照片）。"""

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


def _validate_image(upload: UploadFile, noun: str) -> tuple[bytes, str, int, int]:
    """校验图片的扩展名、真实内容、格式一致性与尺寸。

    返回（文件内容、规范的扩展名、宽度、高度）。所有错误提示均为中文。
    """

    original_name = upload.filename or ""
    extension = Path(original_name).suffix.lower()
    if extension not in EXTENSION_FORMATS:
        raise BusinessError(415, f"{noun}只支持 PNG、JPEG 或 WebP 格式。")

    content = upload.file.read(MAX_FILE_SIZE_BYTES + 1)
    if not content:
        raise BusinessError(400, "上传文件为空，请重新选择图片。")
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise BusinessError(413, f"{noun}文件不能超过 5 MB。")

    try:
        with Image.open(io.BytesIO(content)) as image:
            image.verify()
        with Image.open(io.BytesIO(content)) as image:
            width, height = image.size
            image_format = image.format
    except (UnidentifiedImageError, OSError) as error:
        raise BusinessError(415, "文件内容不是有效的图片。") from error

    if image_format is None or image_format not in FORMAT_EXTENSIONS:
        raise BusinessError(415, f"{noun}只支持 PNG、JPEG 或 WebP 格式。")
    if EXTENSION_FORMATS[extension] != image_format:
        raise BusinessError(415, "文件扩展名与图片实际格式不一致。")
    if width < MIN_IMAGE_SIDE or height < MIN_IMAGE_SIDE:
        raise BusinessError(400, f"{noun}宽高不能小于 {MIN_IMAGE_SIDE} 像素。")
    if width > MAX_IMAGE_SIDE or height > MAX_IMAGE_SIDE:
        raise BusinessError(400, f"{noun}宽高不能超过 {MAX_IMAGE_SIDE} 像素。")

    return content, FORMAT_EXTENSIONS[image_format], width, height


def _store_image(content: bytes, extension: str, directory: Path, url_prefix: str) -> str:
    """按 UUID 命名保存图片，返回公开访问地址。"""

    directory.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{extension}"
    (directory / stored_name).write_bytes(content)
    return f"{url_prefix}/{stored_name}"


def save_campus_map(upload: UploadFile) -> dict[str, object]:
    """校验并保存校园底图，返回公开访问地址与图片尺寸。"""

    content, extension, width, height = _validate_image(upload, "底图")
    map_url = _store_image(
        content,
        extension,
        resolve_storage_dir(settings.map_dir),
        "/assets/maps",
    )

    return {
        "map_asset_url": map_url,
        "image_width": width,
        "image_height": height,
    }


def save_shop_photo(upload: UploadFile) -> dict[str, object]:
    """校验并保存店铺照片，返回公开访问地址。"""

    content, extension, _width, _height = _validate_image(upload, "照片")
    photo_url = _store_image(
        content,
        extension,
        resolve_storage_dir(settings.upload_dir),
        "/media/shop_photos",
    )
    return {"photo_url": photo_url}
