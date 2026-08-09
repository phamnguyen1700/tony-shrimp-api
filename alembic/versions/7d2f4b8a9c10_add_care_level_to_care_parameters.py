"""add care level to care parameters

Revision ID: 7d2f4b8a9c10
Revises: 5479f052302a
Create Date: 2026-08-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7d2f4b8a9c10"
down_revision: Union[str, Sequence[str], None] = "5479f052302a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "care_parameters",
        sa.Column(
            "care_level",
            sa.String(length=32),
            nullable=False,
            server_default="beginner",
        ),
    )
    op.alter_column("care_parameters", "care_level", server_default=None)


def downgrade() -> None:
    op.drop_column("care_parameters", "care_level")
