"""Create all tables

Revision ID: 0001
Revises:
Create Date: 2026-04-04

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Lockers (aucune dépendance) ---
    op.create_table(
        "lockers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("locker_type", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_lockers_id"), "lockers", ["id"], unique=False)
    op.create_index(
        op.f("ix_lockers_locker_type"), "lockers", ["locker_type"], unique=False
    )

    # --- Categories (aucune dépendance) ---
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        op.f("ix_categories_id"), "categories", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_categories_name"), "categories", ["name"], unique=False
    )

    # --- Pending Cards (aucune dépendance) ---
    op.create_table(
        "pending_cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.String(), nullable=False),
        sa.Column(
            "scanned_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column("status", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("card_id"),
    )
    op.create_index(
        op.f("ix_pending_cards_id"), "pending_cards", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_pending_cards_card_id"),
        "pending_cards",
        ["card_id"],
        unique=False,
    )

    # --- Items (dépend de categories) ---
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("reference", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference"),
    )
    op.create_index(op.f("ix_items_id"), "items", ["id"], unique=False)
    op.create_index(op.f("ix_items_name"), "items", ["name"], unique=False)
    op.create_index(
        op.f("ix_items_reference"), "items", ["reference"], unique=False
    )
    op.create_index(
        op.f("ix_items_category_id"), "items", ["category_id"], unique=False
    )

    # --- Stock (dépend de items + lockers) ---
    op.create_table(
        "stock",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("locker_id", sa.Integer(), nullable=False),
        sa.Column("unit_measure", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.ForeignKeyConstraint(["locker_id"], ["lockers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "item_id", "locker_id", name="unique_stock_item_locker"
        ),
    )
    op.create_index(op.f("ix_stock_id"), "stock", ["id"], unique=False)
    op.create_index(
        op.f("ix_stock_item_id"), "stock", ["item_id"], unique=False
    )
    op.create_index(
        op.f("ix_stock_locker_id"), "stock", ["locker_id"], unique=False
    )

    # --- Locker Permissions (dépend de lockers) ---
    op.create_table(
        "locker_permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("locker_id", sa.Integer(), nullable=False),
        sa.Column(
            "subject_type", sa.String(), nullable=False, server_default="role"
        ),
        sa.Column("role_name", sa.String(), nullable=True),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("can_view", sa.Boolean(), nullable=True),
        sa.Column("can_open", sa.Boolean(), nullable=True),
        sa.Column("can_edit", sa.Boolean(), nullable=True),
        sa.Column("can_take", sa.Boolean(), nullable=True),
        sa.Column("can_manage", sa.Boolean(), nullable=True),
        sa.Column("valid_until", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["locker_id"], ["lockers.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "locker_id",
            "role_name",
            "user_id",
            name="unique_permission_target",
        ),
    )
    op.create_index(
        op.f("ix_locker_permissions_id"),
        "locker_permissions",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_locker_permissions_role_name"),
        "locker_permissions",
        ["role_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_locker_permissions_user_id"),
        "locker_permissions",
        ["user_id"],
        unique=False,
    )

    # --- Access Logs (dépend de lockers) ---
    op.create_table(
        "access_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("locker_id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("result", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("can_open", sa.Boolean(), nullable=True),
        sa.Column("can_view", sa.Boolean(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["locker_id"], ["lockers.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_access_logs_id"), "access_logs", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_access_logs_card_id"),
        "access_logs",
        ["card_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_access_logs_user_id"),
        "access_logs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_access_logs_locker_id"),
        "access_logs",
        ["locker_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("access_logs")
    op.drop_table("locker_permissions")
    op.drop_table("stock")
    op.drop_table("items")
    op.drop_table("pending_cards")
    op.drop_table("categories")
    op.drop_table("lockers")
