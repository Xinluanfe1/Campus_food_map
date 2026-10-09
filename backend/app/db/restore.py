"""从备份压缩包恢复数据。

用法（在 backend 目录执行）：
    python -m app.db.restore --input ../backups/campus_food_backup_xxx.zip
    python -m app.db.restore --input ../backups/xxx.zip --dry-run

安全措施：
1. 校验压缩包内文件名，拒绝绝对路径与 ../ 路径穿越；
2. 恢复前校验数据库快照包含全部业务表；
3. 覆盖现有数据库前自动生成带时间戳的安全副本；
4. 支持 --dry-run 仅校验不写入。
"""

import argparse
import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.db.backup import DATABASE_ARCNAME, MANIFEST_NAME, REQUIRED_TABLES, database_path
from app.db.session import resolve_storage_dir
from app.db.backup import DEFAULT_CONFIG_DIR

ALLOWED_PREFIXES = ("database/", "maps/", "shop_photos/", "config/campuses/")


def _safe_members(archive: zipfile.ZipFile) -> list[str]:
    """校验归档成员路径，返回合法的成员列表。"""

    members: list[str] = []
    for name in archive.namelist():
        if name == MANIFEST_NAME:
            members.append(name)
            continue
        if name.endswith("/"):
            continue
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError(f"压缩包包含不安全的路径：{name}")
        if not name.startswith(ALLOWED_PREFIXES):
            raise ValueError(f"压缩包包含未知内容：{name}")
        members.append(name)
    return members


def _validate_database(snapshot_path: Path) -> None:
    """校验数据库快照可读且包含全部业务表。"""

    connection = sqlite3.connect(snapshot_path)
    try:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        missing = [table for table in REQUIRED_TABLES if table not in tables]
        if missing:
            raise ValueError(f"备份数据库缺少数据表：{'、'.join(missing)}")
        connection.execute("PRAGMA integrity_check").fetchone()
    finally:
        connection.close()


def restore_backup(
    archive_path: Path,
    *,
    database_url: str | None = None,
    map_dir: Path | None = None,
    upload_dir: Path | None = None,
    config_dir: Path | None = None,
    dry_run: bool = False,
) -> dict[str, object]:
    """从备份压缩包恢复数据库、图片与配置。"""

    if not archive_path.is_file():
        raise FileNotFoundError(f"备份文件不存在：{archive_path}")

    target_database = database_path(database_url)
    maps_directory = map_dir or resolve_storage_dir(settings.map_dir)
    photos_directory = upload_dir or resolve_storage_dir(settings.upload_dir)
    campus_config_directory = config_dir or DEFAULT_CONFIG_DIR

    with tempfile.TemporaryDirectory(prefix="cfm-restore-") as temp_dir:
        temp_path = Path(temp_dir)
        with zipfile.ZipFile(archive_path) as archive:
            members = _safe_members(archive)
            if MANIFEST_NAME not in members:
                raise ValueError("备份文件缺少清单（manifest.json），无法确认内容。")
            archive.extractall(temp_path, members=members)

        manifest = json.loads((temp_path / MANIFEST_NAME).read_text(encoding="utf-8"))
        snapshot_path = temp_path / Path(DATABASE_ARCNAME)
        _validate_database(snapshot_path)

        restored_files = {"maps": 0, "shop_photos": 0, "campus_configs": 0}
        plan = (
            ("maps", maps_directory),
            ("shop_photos", photos_directory),
            ("config/campuses", campus_config_directory),
        )

        if dry_run:
            # 只统计将要恢复的文件数量
            for member in members:
                for prefix, _ in plan:
                    if member.startswith(prefix + "/"):
                        key = {
                            "maps": "maps",
                            "shop_photos": "shop_photos",
                            "config/campuses": "campus_configs",
                        }[prefix]
                        restored_files[key] += 1
            return {
                "dry_run": True,
                "archive": str(archive_path),
                "manifest": manifest,
                "restored_files": restored_files,
            }

        target_database.parent.mkdir(parents=True, exist_ok=True)
        safety_copy: Path | None = None
        if target_database.is_file():
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            safety_copy = target_database.with_name(f"{target_database.name}.before-restore-{timestamp}.bak")
            shutil.copy2(target_database, safety_copy)

        for member in members:
            source = temp_path / member
            if not source.is_file():
                continue
            if member == DATABASE_ARCNAME:
                shutil.copy2(source, target_database)
                continue
            if member.startswith("maps/"):
                maps_directory.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, maps_directory / Path(member).name)
                restored_files["maps"] += 1
            elif member.startswith("shop_photos/"):
                photos_directory.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, photos_directory / Path(member).name)
                restored_files["shop_photos"] += 1
            elif member.startswith("config/campuses/"):
                campus_config_directory.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, campus_config_directory / Path(member).name)
                restored_files["campus_configs"] += 1

    return {
        "dry_run": False,
        "archive": str(archive_path),
        "database": str(target_database),
        "safety_copy": str(safety_copy) if safety_copy else None,
        "restored_files": restored_files,
        "manifest": manifest,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="从备份压缩包恢复数据")
    parser.add_argument("--input", required=True, help="备份文件路径")
    parser.add_argument("--database-url", default=None, help="覆盖数据库连接地址")
    parser.add_argument("--dry-run", action="store_true", help="只校验备份，不写入任何文件")
    args = parser.parse_args()

    try:
        result = restore_backup(Path(args.input).resolve(), database_url=args.database_url, dry_run=args.dry_run)
    except (FileNotFoundError, ValueError, zipfile.BadZipFile) as error:
        print(f"恢复失败：{error}")
        return

    if result["dry_run"]:
        print("备份校验通过（--dry-run，未写入任何文件）。")
    else:
        print("恢复完成。")
        print(f"数据库：{result['database']}")
        if result["safety_copy"]:
            print(f"恢复前的数据库安全副本：{result['safety_copy']}")
    files = result["restored_files"]
    print(f"恢复文件：底图 {files['maps']}、店铺照片 {files['shop_photos']}、校园配置 {files['campus_configs']}")


if __name__ == "__main__":
    main()
