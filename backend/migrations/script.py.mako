"""${message}

迁移说明：${message}
生成时间：${create_date}
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels)}
depends_on: str | Sequence[str] | None = ${repr(depends_on)}


def upgrade() -> None:
    """升级说明：${message}"""

    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """回滚说明：撤销本次迁移涉及的数据库结构变更。"""

    ${downgrades if downgrades else "pass"}
