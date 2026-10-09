"""校园增加真实地图范围半径

迁移说明：开发文档要求真实地图模式下后端也必须执行校外范围过滤，
因此为 campuses 增加可选字段 boundary_radius_meters（以校园默认中心为圆心的范围半径，单位米）。
字段为空表示尚未配置范围，此时后端不做半径过滤；取值必须大于 0（由接口层校验）。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261009_0002"
down_revision: str | None = "20261009_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """升级说明：为校园表增加真实地图范围半径字段。"""

    with op.batch_alter_table("campuses") as batch_op:
        batch_op.add_column(
            sa.Column(
                "boundary_radius_meters",
                sa.Float(),
                nullable=True,
                comment="真实地图校园范围半径（米），可为空",
            )
        )


def downgrade() -> None:
    """回滚说明：删除真实地图范围半径字段。"""

    with op.batch_alter_table("campuses") as batch_op:
        batch_op.drop_column("boundary_radius_meters")
