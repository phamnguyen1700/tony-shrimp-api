"""add stock reservation status

Revision ID: e18252849768
Revises: c51f2d7a8e90
Create Date: 2026-08-18 03:10:33.409846
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e18252849768"
down_revision: Union[str, Sequence[str], None] = "c51f2d7a8e90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "stock_reservation_status",
            sa.String(length=32),
            nullable=True,
        ),
    )

    op.execute("""
        UPDATE orders
        SET stock_reservation_status = CASE
            WHEN payment_status = 'paid' THEN 'consumed'
            ELSE 'released'
        END
        """)

    op.alter_column(
        "orders",
        "stock_reservation_status",
        existing_type=sa.String(length=32),
        nullable=False,
    )

    op.create_index(
        op.f("ix_orders_stock_reservation_status"),
        "orders",
        ["stock_reservation_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_orders_stock_reservation_status"),
        table_name="orders",
    )

    op.drop_column(
        "orders",
        "stock_reservation_status",
    )
