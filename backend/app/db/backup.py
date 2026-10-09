"""数据库与资源备份脚本。

备份内容（对应开发文档第 8 步）：SQLite 数据库、校园底图、店铺照片、校园配置文件。
数据库使用 SQLite 在线备份接口生成一致快照，避免复制到写入中的文件。

用法（在 backend 目录执行）：
    python -m app.db.backup
    python -m app.db.backup --output ../backups/campus_food.zip
"""

import argparse
import json
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.db.session import BACKEND_DIR, resolve_sqlite_url, resolve_storage_dir

PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_BACKUP_DIR = PROJECT_ROOT / "backups"
DEFAULT_CONFIG_DIR = PROJECT_ROOT / "config" / "campuses"

MANIFEST_NAME = "manifest.json"
DATABASE_ARCNAME = "database/campus_food.db"
REQUIRED_TABLES = (
    "campuses",
    "users",
    "shops",
    "reviews",
    "review_reactions",
    "review_replies",
    "reports",
)


def database_path(database_url: str | None = None) -> Path:
    """返回数据库文件的绝对路径。"""

    url = resolve_sqlite_url(database_url or settings.database_url)
    return Path(url.removeprefix("sqlite:///"))


def _snapshot_database(source_path: Path, target_path: Path) -> None:
    """使用 SQLite 在线备份接口生成一致快照。"""

    source = sqlite3.connect(source_path)
    try:
        target = sqlite3.connect(target_path)
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()


def _collect_counts(snapshot_path: Path) -> dict[str, int]:
    """统计快照中的核心表记录数量，写入清单便于恢复后核对。"""

    connection = sqlite3.connect(snapshot_path)
    try:
        counts: dict[str, int] = {}
        for table in ("campuses", "users", "shops", "reviews", "review_reactions", "review_replies", "reports"):
            counts[table] = int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        return counts
    finally:
        connection.close()


def create_backup(
    output_path: Path | None = None,
    *,
    database_url: str | None = None,
    map_dir: Path | None = None,
    upload_dir: Path | None = None,
    config_dir: Path | None = None,
) -> dict[str, object]:
    """创建包含数据库、图片与配置的备份压缩包。"""

    source_database = database_path(database_url)
    if not source_database.is_file():
        raise FileNotFoundError(f"数据库文件不存在：{source_database}")

    maps_directory = map_dir or resolve_storage_dir(settings.map_dir)
    photos_directory = upload_dir or resolve_storage_dir(settings.upload_dir)
    campus_config_directory = config_dir or DEFAULT_CONFIG_DIR

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target_path = output_path or (DEFAULT_BACKUP_DIR / f"campus_food_backup_{timestamp}.zip")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="cfm-backup-") as temp_dir:
        temp_path = Path(temp_dir)
        snapshot_path = temp_path / "campus_food.db"
        _snapshot_database(source_database, snapshot_path)
        counts = _collect_counts(snapshot_path)

        files: list[dict[str, str]] = [
            {"arcname": DATABASE_ARCNAME, "type": "database"},
        ]

        def collect(directory: Path, prefix: str, kind: str) -> None:
            if not directory.is_dir():
                return
            for item in sorted(directory.iterdir()):
                if item.is_file():
                    files.append(
                        {"arcname": f"{prefix}/{item.name}", "type": kind},
                    )

        collect(maps_directory, "maps", "map")
        collect(photos_directory, "shop_photos", "shop_photo")
        collect(campus_config_directory, "config/campuses", "campus_config")

        manifest = {
            "format_version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "database_file": DATABASE_ARCNAME,
            "counts": counts,
            "files": files,
        }

        with zipfile.ZipFile(target_path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(snapshot_path, DATABASE_ARCNAME)
            for entry in files:
                if entry["type"] == "database":
                    continue
                source_path, _, name = entry["arcname"].partition("/")
                directory = {
                    "maps": maps_directory,
                    "shop_photos": photos_directory,
                    "config": campus_config_directory,
                }[source_path]
                target_name = name.split("/", 1)[-1]
                archive.write(directory / target_name, entry["arcname"])
            archive.writestr(MANIFEST_NAME, json.dumps(manifest, ensure_ascii=False, indent=2))

    return {
        "output": str(target_path),
        "counts": counts,
        "files": len(files),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="备份数据库、图片与校园配置")
    parser.add_argument("--output", default=None, help="备份文件路径，默认保存在项目 backups 目录")
    parser.add_argument("--database-url", default=None, help="覆盖数据库连接地址")
    args = parser.parse_args()

    output_path = Path(args.output).resolve() if args.output else None
    try:
        result = create_backup(output_path, database_url=args.database_url)
    except FileNotFoundError as error:
        print(f"备份失败：{error}")
        return

    print("备份完成。")
    print(f"备份文件：{result['output']}")
    counts = result["counts"]
    print(
        "记录数量："
        f"校园 {counts['campuses']}、用户 {counts['users']}、店铺 {counts['shops']}、"
        f"评价 {counts['reviews']}、互动 {counts['review_reactions']}、"
        f"回复 {counts['review_replies']}、举报 {counts['reports']}"
    )
    print(f"归档文件数：{result['files']}")


if __name__ == "__main__":
    main()
