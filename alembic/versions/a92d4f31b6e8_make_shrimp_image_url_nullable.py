"""make shrimp image url nullable

Revision ID: a92d4f31b6e8
Revises: 7d2f4b8a9c10
Create Date: 2026-08-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a92d4f31b6e8"
down_revision: Union[str, Sequence[str], None] = "7d2f4b8a9c10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "shrimp_images",
        "url",
        existing_type=sa.String(length=1000),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "shrimp_images",
        "url",
        existing_type=sa.String(length=1000),
        nullable=False,
    )
