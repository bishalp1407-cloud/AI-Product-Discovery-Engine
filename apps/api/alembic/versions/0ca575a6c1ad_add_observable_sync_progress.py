"""add observable sync progress

Revision ID: 0ca575a6c1ad
Revises: dff6ecaf942c
Create Date: 2026-09-05 13:43:14.056780

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.

revision: str = "0ca575a6c1ad"
down_revision: Union[str, Sequence[str], None] = "dff6ecaf942c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # sync_batch_logs does not exist in Neon, so create it.
    op.create_table(
        "sync_batch_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("sync_job_id", sa.UUID(), nullable=False),
        sa.Column("batch_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("processed_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["sync_job_id"],
            ["sync_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_sync_batch_logs_sync_job_id"),
        "sync_batch_logs",
        ["sync_job_id"],
        unique=False,
    )

    # These four columns already exist in Neon because the original
    # malformed migration partially executed before failing.
    #
    # Only current_stage is still missing.
    op.add_column(
        "sync_jobs",
        sa.Column(
            "current_stage",
            sa.String(length=30),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_column("sync_jobs", "current_stage")

    op.drop_index(
        op.f("ix_sync_batch_logs_sync_job_id"),
        table_name="sync_batch_logs",
    )

    op.drop_table("sync_batch_logs")

    # The following four columns are intentionally NOT dropped.
    # They existed in Neon before this repaired migration was applied.