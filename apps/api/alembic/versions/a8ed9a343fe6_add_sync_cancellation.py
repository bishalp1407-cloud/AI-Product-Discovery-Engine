"""add sync cancellation

Revision ID: a8ed9a343fe6
Revises: 0ca575a6c1ad
Create Date: 2026-09-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8ed9a343fe6"
down_revision: Union[str, Sequence[str], None] = "0ca575a6c1ad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "sync_jobs",
        sa.Column(
            "cancel_requested",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column(
        "sync_jobs",
        "cancel_requested",
    )