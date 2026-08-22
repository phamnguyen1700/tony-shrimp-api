"""add shrimp seo metadata

Revision ID: f3c1a7e90b42
Revises: e18252849768
Create Date: 2026-08-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3c1a7e90b42"
down_revision: Union[str, Sequence[str], None] = "e18252849768"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("shrimp", sa.Column("meta_title", sa.String(length=255), nullable=True))
    op.add_column(
        "shrimp",
        sa.Column("meta_description", sa.String(length=320), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("shrimp", "meta_description")
    op.drop_column("shrimp", "meta_title")
