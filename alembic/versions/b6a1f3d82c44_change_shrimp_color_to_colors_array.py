"""change shrimp color to colors array

Revision ID: b6a1f3d82c44
Revises: a92d4f31b6e8
Create Date: 2026-08-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b6a1f3d82c44"
down_revision: Union[str, Sequence[str], None] = "a92d4f31b6e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "shrimp",
        sa.Column(
            "colors",
            postgresql.ARRAY(sa.String(length=64)),
            nullable=False,
            server_default=sa.text("'{}'::character varying[]"),
        ),
    )
    op.execute(
        """
        UPDATE shrimp
        SET colors = regexp_split_to_array(color, '\\s*/\\s*')
        WHERE color IS NOT NULL AND btrim(color) <> ''
        """
    )
    op.drop_column("shrimp", "color")
    op.alter_column("shrimp", "colors", server_default=None)


def downgrade() -> None:
    op.add_column("shrimp", sa.Column("color", sa.String(length=64), nullable=True))
    op.execute("UPDATE shrimp SET color = array_to_string(colors, ' / ')")
    op.drop_column("shrimp", "colors")
