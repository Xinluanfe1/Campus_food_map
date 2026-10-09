"""备份与恢复测试：对应第八步验收标准 6、7。"""

import json
import zipfile
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.backup import DATABASE_ARCNAME, MANIFEST_NAME, create_backup
from app.db.restore import restore_backup
from app.db.session import BACKEND_DIR, create_db_engine
from app.models import Campus, Review, Shop, User


def migrate(database_url: str) -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")


def prepare_project(tmp_path: Path) -> dict[str, Path | str]:
    """准备一套包含数据库、底图、店铺照片与校园配置的临时项目目录。"""

    database_dir = tmp_path / "database"
    maps_dir = tmp_path / "maps"
    photos_dir = tmp_path / "shop_photos"
    config_dir = tmp_path / "config" / "campuses"
    for directory in (database_dir, maps_dir, photos_dir, config_dir):
        directory.mkdir(parents=True, exist_ok=True)

    database_url = f"sqlite:///{(database_dir / 'campus_food.db').as_posix()}"
    migrate(database_url)

    engine = create_db_engine(database_url)
    try:
        with Session(engine) as session:
            session.add(
                Campus(
                    campus_id="backup_campus",
                    campus_name="备份测试校园",
                    map_type="image",
                    map_asset_url="/assets/maps/backup.png",
                    map_attribution="备份测试署名",
                    allow_off_campus=False,
                    image_width=1200,
                    image_height=800,
                    default_map_x=0.5,
                    default_map_y=0.5,
                    default_zoom=1,
                    is_active=True,
                )
            )
            session.add(
                User(
                    id=1,
                    username="备份用户",
                    password_hash=hash_password("备份用户密码-2026"),
                    role="user",
                    is_active=True,
                )
            )
            session.commit()
            session.add(
                Shop(
                    id=901,
                    campus_id="backup_campus",
                    name="备份测试店铺",
                    description="用于备份恢复测试的店铺。",
                    shop_type="shop",
                    submitted_by=1,
                    status="approved",
                    map_x=0.2,
                    map_y=0.3,
                )
            )
            session.commit()
            session.add(
                Review(
                    id=901,
                    shop_id=901,
                    user_id=1,
                    rating=5,
                    content="备份前的评价。",
                    status="visible",
                )
            )
            session.commit()
    finally:
        engine.dispose()

    (maps_dir / "backup.png").write_bytes(b"map-bytes")
    (photos_dir / "photo.png").write_bytes(b"photo-bytes")
    (config_dir / "backup_campus.json").write_text(
        json.dumps({"campus_id": "backup_campus"}, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "database_url": database_url,
        "maps_dir": maps_dir,
        "photos_dir": photos_dir,
        "config_dir": config_dir,
        "backup_path": tmp_path / "backup.zip",
    }


def test_backup_contains_database_files_and_config(tmp_path: Path) -> None:
    """验收标准 6：备份包含数据库、底图、店铺照片与校园配置。"""

    project = prepare_project(tmp_path)

    result = create_backup(
        project["backup_path"],
        database_url=str(project["database_url"]),
        map_dir=project["maps_dir"],
        upload_dir=project["photos_dir"],
        config_dir=project["config_dir"],
    )

    assert Path(result["output"]).is_file()
    with zipfile.ZipFile(project["backup_path"]) as archive:
        names = archive.namelist()
        assert MANIFEST_NAME in names
        assert DATABASE_ARCNAME in names
        assert "maps/backup.png" in names
        assert "shop_photos/photo.png" in names
        assert "config/campuses/backup_campus.json" in names
        manifest = json.loads(archive.read(MANIFEST_NAME).decode("utf-8"))

    assert manifest["counts"]["campuses"] == 1
    assert manifest["counts"]["shops"] == 1
    assert manifest["counts"]["reviews"] == 1


def test_restore_recovers_database_and_files(tmp_path: Path) -> None:
    """验收标准 7：恢复后核心数据与文件可以正常读取。"""

    project = prepare_project(tmp_path)
    create_backup(
        project["backup_path"],
        database_url=str(project["database_url"]),
        map_dir=project["maps_dir"],
        upload_dir=project["photos_dir"],
        config_dir=project["config_dir"],
    )

    # 模拟数据损坏：删除评价与底图文件，并新增一条无关记录
    engine = create_db_engine(str(project["database_url"]))
    try:
        with Session(engine) as session:
            review = session.get(Review, 901)
            session.delete(review)
            session.commit()
    finally:
        engine.dispose()
    (project["maps_dir"] / "backup.png").unlink()

    result = restore_backup(
        project["backup_path"],
        database_url=str(project["database_url"]),
        map_dir=project["maps_dir"],
        upload_dir=project["photos_dir"],
        config_dir=project["config_dir"],
    )

    assert result["dry_run"] is False
    assert result["safety_copy"] is not None
    restored_files = result["restored_files"]
    assert restored_files["maps"] == 1
    assert restored_files["shop_photos"] == 1
    assert restored_files["campus_configs"] == 1

    # 数据恢复
    engine = create_db_engine(str(project["database_url"]))
    try:
        with Session(engine) as session:
            assert session.scalar(select(func.count()).select_from(Review)) == 1
            review = session.get(Review, 901)
            assert review is not None
            assert review.content == "备份前的评价。"
            assert session.get(Shop, 901).name == "备份测试店铺"
    finally:
        engine.dispose()

    # 文件恢复
    assert (project["maps_dir"] / "backup.png").read_bytes() == b"map-bytes"
    assert (project["photos_dir"] / "photo.png").read_bytes() == b"photo-bytes"


def test_restore_dry_run_does_not_modify_data(tmp_path: Path) -> None:
    """--dry-run 只校验备份，不写入任何文件。"""

    project = prepare_project(tmp_path)
    create_backup(
        project["backup_path"],
        database_url=str(project["database_url"]),
        map_dir=project["maps_dir"],
        upload_dir=project["photos_dir"],
        config_dir=project["config_dir"],
    )

    (project["maps_dir"] / "backup.png").unlink()
    result = restore_backup(
        project["backup_path"],
        database_url=str(project["database_url"]),
        map_dir=project["maps_dir"],
        upload_dir=project["photos_dir"],
        config_dir=project["config_dir"],
        dry_run=True,
    )

    assert result["dry_run"] is True
    assert result["restored_files"]["maps"] == 1
    assert not (project["maps_dir"] / "backup.png").exists()


def test_restore_rejects_unsafe_archive(tmp_path: Path) -> None:
    """恢复前必须拒绝路径穿越与缺少清单的备份文件。"""

    project = prepare_project(tmp_path)

    unsafe = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(unsafe, "w") as archive:
        archive.writestr("../evil.txt", "bad")
        archive.writestr(MANIFEST_NAME, json.dumps({"format_version": 1}))

    with pytest.raises(ValueError, match="不安全的路径"):
        restore_backup(
            unsafe,
            database_url=str(project["database_url"]),
            map_dir=project["maps_dir"],
            upload_dir=project["photos_dir"],
            config_dir=project["config_dir"],
        )

    no_manifest = tmp_path / "no-manifest.zip"
    with zipfile.ZipFile(no_manifest, "w") as archive:
        archive.writestr("maps/backup.png", b"map-bytes")

    with pytest.raises(ValueError, match="缺少清单"):
        restore_backup(
            no_manifest,
            database_url=str(project["database_url"]),
            map_dir=project["maps_dir"],
            upload_dir=project["photos_dir"],
            config_dir=project["config_dir"],
        )
