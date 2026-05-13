"""Remove can_take from locker_permissions

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-13

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("locker_permissions", "can_take")


def downgrade() -> None:
    op.add_column(
        "locker_permissions",
        sa.Column("can_take", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
