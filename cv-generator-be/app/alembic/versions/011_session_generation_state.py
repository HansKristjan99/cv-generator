"""session generation state

Revision ID: 011_session_generation_state
Revises: 010_merge_009_heads
Create Date: 2026-05-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "011_session_generation_state"
down_revision = "010_merge_009_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cv_sessions",
        sa.Column("status", sa.Text(), nullable=False, server_default="idle"),
    )
    op.add_column("cv_sessions", sa.Column("error", sa.Text(), nullable=True))
    op.add_column("cv_sessions", sa.Column("job_description", sa.Text(), nullable=True))
    op.drop_table("jobs")


def downgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cv_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cv_session_id"], ["cv_sessions.id"], ondelete="CASCADE"),
    )
    op.drop_column("cv_sessions", "job_description")
    op.drop_column("cv_sessions", "error")
    op.drop_column("cv_sessions", "status")
