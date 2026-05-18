"""cv_sessions

Revision ID: 004_cv_sessions
Revises: 003_skill_categories
Create Date: 2026-05-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004_cv_sessions"
down_revision = "003_skill_categories"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cv_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", sa.Text(), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("conversation_id", name="uq_cv_sessions_conversation_id"),
    )
    op.create_index("ix_cv_sessions_user_id_created_at", "cv_sessions", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_cv_sessions_user_id_created_at", "cv_sessions")
    op.drop_table("cv_sessions")
