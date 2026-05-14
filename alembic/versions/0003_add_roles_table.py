"""Add roles table and seed system roles

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-14
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels = None
depends_on = None

SYSTEM_ROLES = [
    {"name": "admin",      "label": "Administrateur système", "tier": 5, "is_system": True,  "is_manager": True,  "is_role_admin": True,  "capacities": ["create_lockers", "configure_system", "audit_log_full"]},
    {"name": "presidence", "label": "Présidence",             "tier": 4, "is_system": True,  "is_manager": True,  "is_role_admin": True,  "capacities": ["audit_log_full", "cascade_delete_role"]},
    {"name": "codir",      "label": "Comité de direction",    "tier": 3, "is_system": True,  "is_manager": True,  "is_role_admin": True,  "capacities": ["audit_log_full"]},
    {"name": "tresorerie", "label": "Trésorerie",             "tier": 3, "is_system": True,  "is_manager": False, "is_role_admin": False, "capacities": ["purchase_orders", "manage_suppliers"]},
    {"name": "bureau",     "label": "Bureau",                 "tier": 2, "is_system": True,  "is_manager": True,  "is_role_admin": False, "capacities": []},
    {"name": "membre",     "label": "Membre",                 "tier": 0, "is_system": True,  "is_manager": False, "is_role_admin": False, "capacities": []},
]


def upgrade() -> None:
    import json
    roles_table = op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_manager", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_role_admin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("capacities", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_roles_id",   "roles", ["id"],   unique=False)
    op.create_index("ix_roles_name", "roles", ["name"], unique=False)

    op.bulk_insert(roles_table, [
        {**r, "capacities": json.dumps(r["capacities"])} for r in SYSTEM_ROLES
    ])


def downgrade() -> None:
    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_index("ix_roles_id",   table_name="roles")
    op.drop_table("roles")
