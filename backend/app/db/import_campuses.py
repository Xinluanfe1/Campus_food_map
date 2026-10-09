"""校园配置导入脚本：把 config/campuses/*.json 写入数据库（幂等）。

用途：更换校园或新增校园时只需要添加配置文件并执行本脚本，不需要修改业务代码。

用法（在 backend 目录执行）：
    python -m app.db.import_campuses
    python -m app.db.import_campuses --path ../config/campuses
"""

import argparse
import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.errors import BusinessError
from app.db.session import BACKEND_DIR, create_db_engine
from app.services.campus_service import import_campuses_from_directory

DEFAULT_CONFIG_DIR = BACKEND_DIR.parent / "config" / "campuses"


def main() -> None:
    parser = argparse.ArgumentParser(description="从配置文件导入校园配置")
    parser.add_argument(
        "--path",
        default=str(DEFAULT_CONFIG_DIR),
        help="校园配置目录，默认为项目下的 config/campuses",
    )
    parser.add_argument("--database-url", default=None, help="覆盖数据库连接地址")
    args = parser.parse_args()

    directory = Path(args.path).resolve()
    if not directory.is_dir():
        print(f"配置目录不存在：{directory}")
        return

    engine = create_db_engine(args.database_url)
    try:
        with Session(engine) as session:
            result = import_campuses_from_directory(session, directory)
    except BusinessError as error:
        print(f"导入失败：{error.message}")
        return
    except json.JSONDecodeError as error:
        print(f"导入失败：校园配置文件不是合法的 JSON（{error}）")
        return
    finally:
        engine.dispose()

    print("校园配置导入完成。")
    print(
        f"新增校园：{len(result['created'])} 个"
        + (f"（{'、'.join(result['created'])}）" if result["created"] else "")
    )
    print(
        f"更新校园：{len(result['updated'])} 个"
        + (f"（{'、'.join(result['updated'])}）" if result["updated"] else "")
    )


if __name__ == "__main__":
    main()
