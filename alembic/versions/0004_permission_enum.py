"""Refactor locker_permissions: replace boolean columns with permission_level enum

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-14
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add permission_level column (nullable during backfill)
    op.add_column("locker_permissions", sa.Column("permission_level", sa.String(20), nullable=True))

    # 2. Backfill: can_edit wins > can_open > can_view (hierarchical)
    op.execute("""
        UPDATE locker_permissions
        SET permission_level = CASE
            WHEN can_edit  = TRUE THEN 'can_edit'
            WHEN can_open  = TRUE THEN 'can_open'
            ELSE 'can_view'
        END
    """)

    # 3. Make NOT NULL
    op.alter_column("locker_permissions", "permission_level", nullable=False)

    # 4. Drop old unique constraint before dropping its columns
    op.drop_constraint("unique_permission_target", "locker_permissions", type_="unique")

    # 5. Drop old boolean and user-override columns
    for col in ("can_view", "can_open", "can_edit", "can_manage", "subject_type", "user_id"):
        op.drop_column("locker_permissions", col)

    # Recreate cleaner unique constraint
    op.create_unique_constraint("unique_permission_role_locker", "locker_permissions", ["locker_id", "role_name"])

    # 6. Recreate role_name index
    op.execute("DROP INDEX IF EXISTS ix_locker_permissions_role_name")
    op.execute("DROP INDEX IF EXISTS ix_locker_permissions_user_id")
    op.create_index("ix_locker_permissions_role_name", "locker_permissions", ["role_name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_locker_permissions_role_name", table_name="locker_permissions")
    op.drop_constraint("unique_permission_role_locker", "locker_permissions", type_="unique")
    op.add_column("locker_permissions", sa.Column("user_id", sa.String(), nullable=True))
    op.add_column("locker_permissions", sa.Column("subject_type", sa.String(), nullable=False, server_default="role"))
    op.add_column("locker_permissions", sa.Column("can_manage", sa.Boolean(), nullable=True))
    op.add_column("locker_permissions", sa.Column("can_edit", sa.Boolean(), nullable=True))
    op.add_column("locker_permissions", sa.Column("can_open", sa.Boolean(), nullable=True))
    op.add_column("locker_permissions", sa.Column("can_view", sa.Boolean(), nullable=True))
    op.create_unique_constraint("unique_permission_target", "locker_permissions", ["locker_id", "role_name", "user_id"])
    op.drop_column("locker_permissions", "permission_level")
