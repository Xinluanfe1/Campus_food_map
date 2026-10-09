"""管理员初始化命令（受控管理流程）。

管理员角色只能通过初始化配置或本受控命令赋予，普通用户注册接口不允许指定角色。

用法：
    python -m app.db.create_admin --username 平台管理员
    python -m app.db.create_admin --username 平台管理员 --password "强密码"
    python -m app.db.create_admin --username 平台管理员 --promote-existing
    python -m app.db.create_admin --username 平台管理员 --reset-password
"""

import argparse
import secrets

from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import create_db_engine
from app.models import User


def _resolve_password(provided: str | None) -> tuple[str, bool]:
    """确定管理员密码：优先命令行，其次环境变量，最后生成随机密码。"""

    if provided:
        return provided, False
    if settings.admin_initial_password:
        return settings.admin_initial_password, False
    return secrets.token_urlsafe(12), True


def main() -> None:
    parser = argparse.ArgumentParser(description="创建或维护管理员账号（受控管理流程）")
    parser.add_argument("--username", required=True, help="管理员用户名")
    parser.add_argument("--password", default=None, help="管理员密码；未提供时读取环境变量或自动生成")
    parser.add_argument("--database-url", default=None, help="覆盖数据库连接地址")
    parser.add_argument("--promote-existing", action="store_true", help="把已存在的普通用户提升为管理员")
    parser.add_argument("--reset-password", action="store_true", help="为已存在的管理员重置密码")
    args = parser.parse_args()

    engine = create_db_engine(args.database_url)
    password_hasher = PasswordHash.recommended()
    try:
        with Session(engine) as session:
            user = session.scalar(select(User).where(User.username == args.username))

            if user is None:
                raw_password, generated = _resolve_password(args.password)
                session.add(
                    User(
                        username=args.username,
                        password_hash=password_hasher.hash(raw_password),
                        role="admin",
                        is_active=True,
                    )
                )
                session.commit()
                print(f"已创建管理员账号：{args.username}")
                if generated:
                    print(f"随机初始密码（请立即记录并修改）：{raw_password}")
                return

            if user.role == "user":
                if not args.promote_existing:
                    print(f"用户 {args.username} 当前是普通用户，未做修改。")
                    print("如需提升为管理员，请显式使用 --promote-existing。")
                    return
                raw_password, generated = _resolve_password(args.password)
                user.role = "admin"
                if args.password:
                    user.password_hash = password_hasher.hash(raw_password)
                session.commit()
                print(f"已将用户 {args.username} 提升为管理员。")
                if generated and args.password:
                    print(f"随机初始密码（请立即记录并修改)：{raw_password}")
                return

            if not args.reset_password:
                print(f"管理员 {args.username} 已存在，未做修改。")
                print("如需重置密码，请显式使用 --reset-password。")
                return

            raw_password, generated = _resolve_password(args.password)
            user.password_hash = password_hasher.hash(raw_password)
            session.commit()
            print(f"已重置管理员 {args.username} 的密码。")
            if generated:
                print(f"随机新密码（请立即记录并修改）：{raw_password}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
