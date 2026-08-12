"""add shrimp slug and remove order tracking fields

Revision ID: 9bd6d7a1b2c3
Revises: dfdf42b8c577
Create Date: 2026-08-12 19:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "9bd6d7a1b2c3"
down_revision: Union[str, Sequence[str], None] = "dfdf42b8c577"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("shrimp", sa.Column("slug", sa.String(length=255), nullable=True))

    op.execute(
        """
        WITH normalized AS (
            SELECT
                id,
                COALESCE(
                    NULLIF(
                        trim(
                            both '-' from regexp_replace(
                                regexp_replace(lower(name), '[^a-z0-9]+', '-', 'g'),
                                '-+',
                                '-',
                                'g'
                            )
                        ),
                        ''
                    ),
                    'shrimp-' || left(id::text, 8)
                ) AS base_slug,
                created_at
            FROM shrimp
        ),
        ranked AS (
            SELECT
                id,
                base_slug,
                row_number() OVER (
                    PARTITION BY base_slug
                    ORDER BY created_at, id
                ) AS duplicate_number
            FROM normalized
        )
        UPDATE shrimp
        SET slug = CASE
            WHEN ranked.duplicate_number = 1 THEN ranked.base_slug
            ELSE ranked.base_slug || '-' || ranked.duplicate_number::text
        END
        FROM ranked
        WHERE shrimp.id = ranked.id
        """
    )

    op.alter_column("shrimp", "slug", nullable=False)
    op.create_index(op.f("ix_shrimp_slug"), "shrimp", ["slug"], unique=True)

    op.drop_column("orders", "admin_note")
    op.drop_column("orders", "carrier")
    op.drop_column("orders", "tracking_number")
    op.drop_column("orders", "tracking_url")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "orders",
        sa.Column("tracking_url", sa.Text(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column(
            "tracking_number",
            sa.String(length=100),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "orders",
        sa.Column("carrier", sa.String(length=100), autoincrement=False, nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("admin_note", sa.Text(), autoincrement=False, nullable=True),
    )

    op.drop_index(op.f("ix_shrimp_slug"), table_name="shrimp")
    op.drop_column("shrimp", "slug")
