"""数据库检查脚本：输出表清单、记录数量、外键定义与索引状态。

用法（在 backend 目录执行）：
    python -m app.db.check_db
"""

import sqlite3
from pathlib import Path

from app.core.config import settings
from app.db.session import resolve_sqlite_url

BUSINESS_TABLES = (
    "campuses",
    "users",
    "shops",
    "reviews",
    "review_reactions",
    "review_replies",
    "reports",
)


def database_path() -> Path:
    """返回当前配置对应的 SQLite 文件路径。"""

    url = resolve_sqlite_url(settings.database_url)
    return Path(url.removeprefix("sqlite:///"))


def main() -> None:
    path = database_path()
    print(f"数据库文件：{path}")

    if not path.exists():
        print("数据库文件不存在，请先执行：python -m app.db.init_db")
        return

    connection = sqlite3.connect(path)
    try:
        # 与后端保持一致：检查脚本也显式启用外键约束。
        connection.execute("PRAGMA foreign_keys=ON")

        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        print(f"数据表（{len(tables)} 张）：{'、'.join(tables)}")

        print("记录数量：")
        for table in BUSINESS_TABLES:
            if table in tables:
                count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                print(f"  {table}：{count} 条")

        print("外键定义：")
        for table in ("shops", "reviews", "review_reactions", "review_replies", "reports"):
            definitions = [
                f"{row[3]} -> {row[2]}.{row[4]}（删除规则：{row[6]}）"
                for row in connection.execute(f"PRAGMA foreign_key_list('{table}')")
            ]
            print(f"  {table}：")
            for definition in definitions:
                print(f"    {definition}")

        print("索引：")
        for table in ("shops", "reviews", "review_reactions", "review_replies", "reports"):
            index_names = [row[1] for row in connection.execute(f"PRAGMA index_list('{table}')")]
            print(f"  {table}：{'、'.join(index_names)}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
