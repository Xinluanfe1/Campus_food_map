"""数据库初始化脚本。

用途：
1. 通过 Alembic 迁移创建或升级数据库结构（不使用 create_all 替代迁移）。
2. 写入演示校园、管理员、测试用户、示例店铺、评价与互动数据。
3. 重复执行时按主键跳过已存在记录，不会重复插入。

用法：
    python -m app.db.init_db
    python -m app.db.init_db --admin-password "强密码"
    python -m app.db.init_db --database-url sqlite:///临时验证.db
"""

import argparse
import secrets

from alembic import command
from alembic.config import Config
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import seed_data
from app.db.session import BACKEND_DIR, create_db_engine, ensure_storage_directories, resolve_sqlite_url
from app.models import Campus, Report, Review, ReviewReaction, ReviewReply, Shop, User


def run_migrations(database_url: str) -> None:
    """使用 Alembic 把数据库结构升级到最新版本。"""

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", resolve_sqlite_url(database_url))
    command.upgrade(config, "head")


def init_database(
    database_url: str | None = None,
    admin_password: str | None = None,
    run_migrations_flag: bool = True,
) -> dict[str, object]:
    """初始化数据库并写入演示数据，返回本次执行结果的统计信息。"""

    url = database_url or settings.database_url

    if run_migrations_flag:
        run_migrations(url)

    storage_directories = ensure_storage_directories()

    admin_seed_password = admin_password or settings.admin_initial_password
    password_generated = False
    if admin_seed_password is None:
        admin_seed_password = secrets.token_urlsafe(12)
        password_generated = True

    password_hasher = PasswordHash.recommended()
    inserted = 0
    skipped = 0

    engine = create_db_engine(url)
    try:
        with Session(engine) as session:
            if session.get(Campus, seed_data.CAMPUS_SEED["campus_id"]) is None:
                session.add(Campus(**seed_data.CAMPUS_SEED))
                inserted += 1
            else:
                skipped += 1

            for item in seed_data.USERS_SEED:
                if session.get(User, item["id"]) is not None:
                    skipped += 1
                    continue
                raw_password = (
                    admin_seed_password if item["role"] == "admin" else seed_data.DEMO_USER_PASSWORD
                )
                session.add(
                    User(
                        id=item["id"],
                        username=item["username"],
                        password_hash=password_hasher.hash(raw_password),
                        role=item["role"],
                        is_active=item["is_active"],
                    )
                )
                inserted += 1

            for item in seed_data.SHOPS_SEED:
                if session.get(Shop, item["id"]) is not None:
                    skipped += 1
                    continue
                session.add(Shop(**item))
                inserted += 1

            for item in seed_data.REVIEWS_SEED:
                if session.get(Review, item["id"]) is not None:
                    skipped += 1
                    continue
                session.add(Review(**item))
                inserted += 1

            for item in seed_data.REVIEW_REACTIONS_SEED:
                if session.get(ReviewReaction, item["id"]) is not None:
                    skipped += 1
                    continue
                session.add(ReviewReaction(**item))
                inserted += 1

            for item in seed_data.REVIEW_REPLIES_SEED:
                if session.get(ReviewReply, item["id"]) is not None:
                    skipped += 1
                    continue
                session.add(ReviewReply(**item))
                inserted += 1

            for item in seed_data.REPORTS_SEED:
                if session.get(Report, item["id"]) is not None:
                    skipped += 1
                    continue
                session.add(Report(**item))
                inserted += 1

            session.commit()
    finally:
        engine.dispose()

    return {
        "inserted": inserted,
        "skipped": skipped,
        "admin_password_generated": password_generated,
        "admin_password": admin_seed_password if password_generated else "",
        "storage_directories": [str(path) for path in storage_directories],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="初始化校园美食地图数据库并写入演示数据")
    parser.add_argument(
        "--database-url",
        default=None,
        help="覆盖数据库连接地址，默认使用配置中的 DATABASE_URL",
    )
    parser.add_argument(
        "--admin-password",
        default=None,
        help="管理员初始密码；未提供时读取环境变量 ADMIN_INITIAL_PASSWORD，仍为空则自动生成随机密码",
    )
    parser.add_argument(
        "--skip-migrations",
        action="store_true",
        help="跳过 Alembic 迁移，仅写入演示数据",
    )
    args = parser.parse_args()

    result = init_database(
        database_url=args.database_url,
        admin_password=args.admin_password,
        run_migrations_flag=not args.skip_migrations,
    )

    print("数据库初始化完成。")
    print(f"新插入记录：{result['inserted']} 条；已存在并跳过：{result['skipped']} 条。")
    if result["admin_password_generated"]:
        print("已为管理员账号生成随机初始密码，请立即记录并在首次登录后修改：")
        print(f"  用户名：admin")
        print(f"  初始密码：{result['admin_password']}")
    else:
        print("管理员账号密码使用了命令行参数或环境变量提供的值。")
    print(f"演示普通用户统一密码：{seed_data.DEMO_USER_PASSWORD}")
    print("已确认存储目录：")
    for directory in result["storage_directories"]:
        print(f"  {directory}")


if __name__ == "__main__":
    main()
