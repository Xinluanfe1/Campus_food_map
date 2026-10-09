"""初始数据库结构：校园、用户、店铺、评价、互动、回复与举报表

迁移说明：按《技术路线与开发说明》第六章创建第一阶段全部数据表、外键、
唯一约束、检查约束与高频查询索引。SQLite 不支持原生表注释，中文说明保存在
SQLAlchemy 模型的 comment 属性、本迁移脚本与《数据库字典》中。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261009_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """升级说明：创建第一阶段全部数据库表、约束与索引。"""

    # 校园及其地图配置表
    op.create_table(
        "campuses",
        sa.Column("campus_id", sa.String(length=50), nullable=False, comment="校园唯一标识（稳定字符串，主键）"),
        sa.Column("campus_name", sa.String(length=100), nullable=False, comment="校园名称"),
        sa.Column("map_type", sa.String(length=10), nullable=False, comment="地图类型：image（图片底图）或 real（真实地图）"),
        sa.Column("map_asset_url", sa.String(length=500), nullable=True, comment="图片底图资源路径，真实地图模式可为空"),
        sa.Column("tile_url_template", sa.String(length=500), nullable=True, comment="真实地图瓦片地址模板，图片模式可为空"),
        sa.Column("map_attribution", sa.String(length=300), nullable=True, comment="地图署名文本，真实地图模式必填"),
        sa.Column("allow_off_campus", sa.Boolean(), nullable=False, comment="是否允许展示校园范围以外的店铺"),
        sa.Column("image_width", sa.Integer(), nullable=True, comment="图片底图宽度（像素）"),
        sa.Column("image_height", sa.Integer(), nullable=True, comment="图片底图高度（像素）"),
        sa.Column("default_map_x", sa.Float(), nullable=True, comment="图片底图默认中心横向比例（0 至 1）"),
        sa.Column("default_map_y", sa.Float(), nullable=True, comment="图片底图默认中心纵向比例（0 至 1）"),
        sa.Column("default_latitude", sa.Float(), nullable=True, comment="真实地图默认中心纬度（-90 至 90）"),
        sa.Column("default_longitude", sa.Float(), nullable=True, comment="真实地图默认中心经度（-180 至 180）"),
        sa.Column("default_zoom", sa.Float(), nullable=False, comment="默认缩放级别"),
        sa.Column("is_active", sa.Boolean(), nullable=False, comment="是否允许正常访问"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间（UTC）"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, comment="更新时间（UTC）"),
        sa.CheckConstraint("map_type IN ('image', 'real')", name="map_type_allowed"),
        sa.CheckConstraint(
            "map_type <> 'image' OR (map_asset_url IS NOT NULL AND image_width IS NOT NULL "
            "AND image_height IS NOT NULL AND default_map_x IS NOT NULL AND default_map_y IS NOT NULL)",
            name="image_config_required",
        ),
        sa.CheckConstraint(
            "map_type <> 'real' OR (tile_url_template IS NOT NULL AND map_attribution IS NOT NULL "
            "AND default_latitude IS NOT NULL AND default_longitude IS NOT NULL)",
            name="real_config_required",
        ),
        sa.CheckConstraint(
            "default_map_x IS NULL OR (default_map_x >= 0 AND default_map_x <= 1)",
            name="default_map_x_range",
        ),
        sa.CheckConstraint(
            "default_map_y IS NULL OR (default_map_y >= 0 AND default_map_y <= 1)",
            name="default_map_y_range",
        ),
        sa.CheckConstraint(
            "default_latitude IS NULL OR (default_latitude >= -90 AND default_latitude <= 90)",
            name="default_latitude_range",
        ),
        sa.CheckConstraint(
            "default_longitude IS NULL OR (default_longitude >= -180 AND default_longitude <= 180)",
            name="default_longitude_range",
        ),
        sa.CheckConstraint("default_zoom > 0", name="default_zoom_positive"),
        sa.PrimaryKeyConstraint("campus_id", name="pk_campuses"),
        comment="校园及其地图配置表",
    )

    # 系统用户表
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="用户主键"),
        sa.Column("username", sa.String(length=20), nullable=False, comment="用户名（唯一，2 至 20 个字符）"),
        sa.Column("password_hash", sa.String(length=255), nullable=False, comment="密码哈希（Argon2id，不保存明文密码）"),
        sa.Column("role", sa.String(length=10), nullable=False, comment="用户角色：user（普通用户）或 admin（管理员）"),
        sa.Column("is_active", sa.Boolean(), nullable=False, comment="账号是否启用"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间（UTC）"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, comment="更新时间（UTC）"),
        sa.CheckConstraint("role IN ('user', 'admin')", name="role_allowed"),
        sa.CheckConstraint("length(username) BETWEEN 2 AND 20", name="username_length"),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("username", name="uq_users_username"),
        comment="系统用户表",
    )

    # 校园美食店铺表
    op.create_table(
        "shops",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="店铺主键"),
        sa.Column("campus_id", sa.String(length=50), nullable=False, comment="所属校园标识（外键：campuses.campus_id）"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="店铺名称（必填）"),
        sa.Column("description", sa.Text(), nullable=False, comment="店铺简介（必填）"),
        sa.Column("shop_type", sa.String(length=10), nullable=False, comment="店铺类型：shop（商铺）或 vendor（摊贩）"),
        sa.Column("photo_url", sa.String(length=500), nullable=True, comment="封面照片路径，可为空"),
        sa.Column("submitted_by", sa.Integer(), nullable=False, comment="提交用户 ID（外键：users.id）"),
        sa.Column("status", sa.String(length=10), nullable=False, comment="审核状态：pending、approved 或 rejected"),
        sa.Column("map_x", sa.Float(), nullable=True, comment="图片模式横向比例坐标（0 至 1）"),
        sa.Column("map_y", sa.Float(), nullable=True, comment="图片模式纵向比例坐标（0 至 1）"),
        sa.Column("latitude", sa.Float(), nullable=True, comment="真实地图纬度（-90 至 90）"),
        sa.Column("longitude", sa.Float(), nullable=True, comment="真实地图经度（-180 至 180）"),
        sa.Column("reviewed_by", sa.Integer(), nullable=True, comment="审核管理员 ID（外键：users.id，可为空）"),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True, comment="审核时间（UTC，可为空）"),
        sa.Column("rejection_reason", sa.String(length=500), nullable=True, comment="拒绝原因（被拒绝时必填）"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间（UTC）"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, comment="更新时间（UTC）"),
        sa.CheckConstraint("shop_type IN ('shop', 'vendor')", name="shop_type_allowed"),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="status_allowed"),
        sa.CheckConstraint("length(name) >= 1", name="name_not_empty"),
        sa.CheckConstraint("length(description) >= 1", name="description_not_empty"),
        sa.CheckConstraint("map_x IS NULL OR (map_x >= 0 AND map_x <= 1)", name="map_x_range"),
        sa.CheckConstraint("map_y IS NULL OR (map_y >= 0 AND map_y <= 1)", name="map_y_range"),
        sa.CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)", name="latitude_range"
        ),
        sa.CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)", name="longitude_range"
        ),
        sa.CheckConstraint(
            "(map_x IS NULL AND map_y IS NULL) OR (map_x IS NOT NULL AND map_y IS NOT NULL)",
            name="map_coordinates_paired",
        ),
        sa.CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL) OR (latitude IS NOT NULL AND longitude IS NOT NULL)",
            name="geo_coordinates_paired",
        ),
        sa.CheckConstraint("map_x IS NOT NULL OR latitude IS NOT NULL", name="location_required"),
        sa.CheckConstraint(
            "status <> 'rejected' OR (rejection_reason IS NOT NULL AND length(rejection_reason) >= 1)",
            name="rejection_reason_required",
        ),
        sa.ForeignKeyConstraint(
            ["campus_id"], ["campuses.campus_id"], name="fk_shops_campus_id_campuses", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by"], ["users.id"], name="fk_shops_submitted_by_users", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"], ["users.id"], name="fk_shops_reviewed_by_users", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_shops"),
        comment="校园美食店铺表",
    )
    op.create_index("ix_shops_campus_id_status", "shops", ["campus_id", "status"], unique=False)
    op.create_index("ix_shops_submitted_by", "shops", ["submitted_by"], unique=False)

    # 用户店铺评价表
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="评价主键"),
        sa.Column("shop_id", sa.Integer(), nullable=False, comment="被评价店铺 ID（外键：shops.id）"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="评价用户 ID（外键：users.id）"),
        sa.Column("rating", sa.Integer(), nullable=False, comment="评分（1 至 5 的整数）"),
        sa.Column("content", sa.Text(), nullable=False, comment="文字评价内容（1 至 2000 个字符）"),
        sa.Column("status", sa.String(length=10), nullable=False, comment="评价状态：visible（可见）或 hidden（已隐藏）"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间（UTC）"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, comment="更新时间（UTC）"),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),
        sa.CheckConstraint("length(content) BETWEEN 1 AND 2000", name="content_length"),
        sa.CheckConstraint("status IN ('visible', 'hidden')", name="status_allowed"),
        sa.ForeignKeyConstraint(["shop_id"], ["shops.id"], name="fk_reviews_shop_id_shops", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_reviews_user_id_users", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_reviews"),
        sa.UniqueConstraint("shop_id", "user_id", name="uq_reviews_shop_id_user_id"),
        comment="用户店铺评价表",
    )
    op.create_index("ix_reviews_shop_id_status", "reviews", ["shop_id", "status"], unique=False)

    # 评价点赞与点踩表
    op.create_table(
        "review_reactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="互动主键"),
        sa.Column("review_id", sa.Integer(), nullable=False, comment="目标评价 ID（外键：reviews.id）"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="执行互动的用户 ID（外键：users.id）"),
        sa.Column("reaction_type", sa.String(length=10), nullable=False, comment="互动类型：like（点赞）或 dislike（点踩）"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间（UTC）"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, comment="更新时间（UTC）"),
        sa.CheckConstraint(
            "reaction_type IN ('like', 'dislike')", name="reaction_type_allowed"
        ),
        sa.ForeignKeyConstraint(
            ["review_id"], ["reviews.id"], name="fk_review_reactions_review_id_reviews", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_review_reactions_user_id_users", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_review_reactions"),
        sa.UniqueConstraint("review_id", "user_id", name="uq_review_reactions_review_id_user_id"),
        comment="评价点赞与点踩表",
    )
    op.create_index("ix_review_reactions_user_id", "review_reactions", ["user_id"], unique=False)

    # 评价回复表
    op.create_table(
        "review_replies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="回复主键"),
        sa.Column("review_id", sa.Integer(), nullable=False, comment="所属主评价 ID（外键：reviews.id）"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="回复者用户 ID（外键：users.id）"),
        sa.Column("content", sa.Text(), nullable=False, comment="回复文本（1 至 1000 个字符）"),
        sa.Column("status", sa.String(length=10), nullable=False, comment="回复状态：visible（可见）或 hidden（已隐藏）"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="创建时间（UTC）"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, comment="更新时间（UTC）"),
        sa.CheckConstraint("length(content) BETWEEN 1 AND 1000", name="content_length"),
        sa.CheckConstraint("status IN ('visible', 'hidden')", name="status_allowed"),
        sa.ForeignKeyConstraint(
            ["review_id"], ["reviews.id"], name="fk_review_replies_review_id_reviews", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_review_replies_user_id_users", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_review_replies"),
        comment="评价回复表",
    )
    op.create_index("ix_review_replies_review_id_status", "review_replies", ["review_id", "status"], unique=False)

    # 评价举报及处理记录表
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="举报主键"),
        sa.Column("review_id", sa.Integer(), nullable=False, comment="被举报评价 ID（外键：reviews.id）"),
        sa.Column("reported_by", sa.Integer(), nullable=False, comment="举报用户 ID（外键：users.id）"),
        sa.Column("reason", sa.Text(), nullable=False, comment="举报理由（必填）"),
        sa.Column("status", sa.String(length=10), nullable=False, comment="处理状态：pending、resolved 或 dismissed"),
        sa.Column("handled_by", sa.Integer(), nullable=True, comment="处理管理员 ID（外键：users.id，可为空）"),
        sa.Column("handled_at", sa.DateTime(timezone=True), nullable=True, comment="处理时间（UTC，可为空）"),
        sa.Column("handling_note", sa.Text(), nullable=True, comment="处理备注，可为空"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, comment="举报时间（UTC）"),
        sa.CheckConstraint("status IN ('pending', 'resolved', 'dismissed')", name="status_allowed"),
        sa.CheckConstraint("length(reason) >= 1", name="reason_not_empty"),
        sa.ForeignKeyConstraint(["review_id"], ["reviews.id"], name="fk_reports_review_id_reviews", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reported_by"], ["users.id"], name="fk_reports_reported_by_users", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["handled_by"], ["users.id"], name="fk_reports_handled_by_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_reports"),
        comment="评价举报及处理记录表",
    )
    op.create_index("ix_reports_status", "reports", ["status"], unique=False)
    # 同一用户对同一条评价只能有一条“待处理”举报；partial 索引允许历史已处理举报继续存在。
    op.create_index(
        "uq_reports_pending_review_id_reported_by",
        "reports",
        ["review_id", "reported_by"],
        unique=True,
        sqlite_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    """回滚说明：按依赖顺序撤销第一阶段全部数据库表、约束与索引。"""

    op.drop_index("uq_reports_pending_review_id_reported_by", table_name="reports")
    op.drop_index("ix_reports_status", table_name="reports")
    op.drop_table("reports")

    op.drop_index("ix_review_replies_review_id_status", table_name="review_replies")
    op.drop_table("review_replies")

    op.drop_index("ix_review_reactions_user_id", table_name="review_reactions")
    op.drop_table("review_reactions")

    op.drop_index("ix_reviews_shop_id_status", table_name="reviews")
    op.drop_table("reviews")

    op.drop_index("ix_shops_submitted_by", table_name="shops")
    op.drop_index("ix_shops_campus_id_status", table_name="shops")
    op.drop_table("shops")

    op.drop_table("users")

    op.drop_table("campuses")
