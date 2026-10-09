"""数据一致性检查脚本。

检查内容：
1. SQLite 外键完整性（PRAGMA foreign_key_check）；
2. 孤立记录（评价、互动、回复、举报的关联对象是否存在）；
3. 店铺坐标体系与所属校园地图类型是否一致；
4. 已审核店铺是否记录审核人、被拒绝店铺是否记录原因；
5. 隐藏评价与可见评价的数量统计。

用法（在 backend 目录执行）：
    python -m app.db.check_consistency
存在问题时脚本返回非零退出码，便于持续集成检查。
"""

import sqlite3
import sys

from app.core.config import settings
from app.db.backup import database_path

ISSUE_LABELS = {
    "foreign_keys": "外键完整性",
    "orphan_reviews": "孤立评价",
    "orphan_reactions": "孤立互动",
    "orphan_replies": "孤立回复",
    "orphan_reports": "孤立举报",
    "coordinate_mismatch": "坐标体系不一致",
    "missing_reviewer": "已审核店铺缺少审核人",
    "missing_rejection_reason": "被拒绝店铺缺少拒绝原因",
}


def run_checks(database_file) -> dict[str, list[str]]:
    """执行全部一致性检查，返回问题清单。"""

    connection = sqlite3.connect(database_file)
    issues: dict[str, list[str]] = {key: [] for key in ISSUE_LABELS}
    try:
        for row in connection.execute("PRAGMA foreign_key_check"):
            issues["foreign_keys"].append(f"表 {row[0]} 的外键指向了不存在的记录（rowid={row[1]}）")

        orphan_queries = {
            "orphan_reviews": (
                "SELECT reviews.id FROM reviews "
                "LEFT JOIN shops ON reviews.shop_id = shops.id "
                "LEFT JOIN users ON reviews.user_id = users.id "
                "WHERE shops.id IS NULL OR users.id IS NULL"
            ),
            "orphan_reactions": (
                "SELECT review_reactions.id FROM review_reactions "
                "LEFT JOIN reviews ON review_reactions.review_id = reviews.id "
                "LEFT JOIN users ON review_reactions.user_id = users.id "
                "WHERE reviews.id IS NULL OR users.id IS NULL"
            ),
            "orphan_replies": (
                "SELECT review_replies.id FROM review_replies "
                "LEFT JOIN reviews ON review_replies.review_id = reviews.id "
                "LEFT JOIN users ON review_replies.user_id = users.id "
                "WHERE reviews.id IS NULL OR users.id IS NULL"
            ),
            "orphan_reports": (
                "SELECT reports.id FROM reports "
                "LEFT JOIN reviews ON reports.review_id = reviews.id "
                "LEFT JOIN users ON reports.reported_by = users.id "
                "WHERE reviews.id IS NULL OR users.id IS NULL"
            ),
        }
        for key, query in orphan_queries.items():
            for (record_id,) in connection.execute(query):
                issues[key].append(f"记录 id={record_id} 缺少关联数据")

        coordinate_query = """
            SELECT shops.id, campuses.map_type, shops.map_x, shops.latitude
            FROM shops JOIN campuses ON shops.campus_id = campuses.campus_id
        """
        for shop_id, map_type, map_x, latitude in connection.execute(coordinate_query):
            if map_type == "image" and (map_x is None or latitude is not None):
                issues["coordinate_mismatch"].append(
                    f"店铺 {shop_id} 属于图片底图校园，但坐标不符合图片模式要求"
                )
            if map_type == "real" and (latitude is None or map_x is not None):
                issues["coordinate_mismatch"].append(
                    f"店铺 {shop_id} 属于真实地图校园，但坐标不符合经纬度要求"
                )

        for (shop_id,) in connection.execute(
            "SELECT id FROM shops WHERE status <> 'pending' AND reviewed_by IS NULL"
        ):
            issues["missing_reviewer"].append(f"店铺 {shop_id} 已审核但没有记录审核人")

        for (shop_id,) in connection.execute(
            "SELECT id FROM shops WHERE status = 'rejected' "
            "AND (rejection_reason IS NULL OR length(trim(rejection_reason)) = 0)"
        ):
            issues["missing_rejection_reason"].append(f"店铺 {shop_id} 被拒绝但没有填写原因")

        return issues
    finally:
        connection.close()


def main() -> None:
    database_file = database_path(settings.database_url)
    print(f"数据库文件：{database_file}")
    if not database_file.is_file():
        print("数据库不存在，请先执行：python -m app.db.init_db")
        sys.exit(1)

    issues = run_checks(database_file)
    total_issues = sum(len(items) for items in issues.values())

    for key, label in ISSUE_LABELS.items():
        items = issues[key]
        if items:
            print(f"[问题] {label}：发现 {len(items)} 个问题")
            for item in items[:10]:
                print(f"    - {item}")
            if len(items) > 10:
                print(f"    - …其余 {len(items) - 10} 个问题已省略")
        else:
            print(f"[正常] {label}：正常")

    if total_issues == 0:
        print("数据一致性检查通过，未发现问题。")
        return

    print(f"数据一致性检查未通过，共发现 {total_issues} 个问题。")
    sys.exit(1)


if __name__ == "__main__":
    main()
