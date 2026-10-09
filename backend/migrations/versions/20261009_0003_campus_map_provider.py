"""校园增加真实地图提供方

迁移说明：为支持可选的百度地图 JSAPI 提供方，为 campuses 增加 map_provider 字段，
默认值为 tiles（瓦片地图，与原有行为一致）。百度模式下 tile_url_template 存放
百度 JSAPI SDK 地址（不含 AK），AK 只能通过部署环境的 BAIDU_MAP_AK 提供，不写入仓库。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261009_0003"
down_revision: str | None = "20261009_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """升级说明：为校园表增加真实地图提供方字段。"""

    with op.batch_alter_table("campuses") as batch_op:
        batch_op.add_column(
            sa.Column(
                "map_provider",
                sa.String(length=20),
                nullable=False,
                server_default="tiles",
                comment="真实地图提供方：tiles（瓦片）或 baidu（百度 JSAPI）",
            )
        )


def downgrade() -> None:
    """回滚说明：删除真实地图提供方字段。"""

    with op.batch_alter_table("campuses") as batch_op:
        batch_op.drop_column("map_provider")
