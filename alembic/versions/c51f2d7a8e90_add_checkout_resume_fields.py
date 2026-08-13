"""add checkout resume fields

Revision ID: c51f2d7a8e90
Revises: a4c8f7e2d9b1
Create Date: 2026-08-13

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c51f2d7a8e90"
down_revision: Union[str, Sequence[str], None] = "a4c8f7e2d9b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS stripe_checkout_url TEXT")
    op.execute(
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS "
        "stripe_checkout_expires_at TIMESTAMP WITH TIME ZONE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS stripe_checkout_expires_at")
    op.execute("ALTER TABLE orders DROP COLUMN IF EXISTS stripe_checkout_url")
