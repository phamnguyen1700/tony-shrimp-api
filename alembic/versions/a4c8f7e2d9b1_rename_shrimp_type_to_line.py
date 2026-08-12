"""rename shrimp type to line

Revision ID: a4c8f7e2d9b1
Revises: 9bd6d7a1b2c3
Create Date: 2026-08-12 19:35:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4c8f7e2d9b1"
down_revision: Union[str, Sequence[str], None] = "9bd6d7a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column("shrimp", "type", new_column_name="line")


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("shrimp", "line", new_column_name="type")
