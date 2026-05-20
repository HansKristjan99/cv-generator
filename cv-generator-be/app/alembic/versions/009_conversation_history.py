"""conversation_history

Revision ID: 009_conversation_history
Revises: 008_grant_unlimited_admin
Create Date: 2026-05-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "009_conversation_history"
down_revision = "008_grant_unlimited_admin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cv_sessions", sa.Column("title", sa.Text(), nullable=True))

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

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cv_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["cv_session_id"], ["cv_sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_messages_cv_session_id", "messages", ["cv_session_id"])


def downgrade() -> None:
    op.drop_index("ix_messages_cv_session_id", "messages")
    op.drop_table("messages")
    op.drop_table("jobs")
    op.drop_column("cv_sessions", "title")
