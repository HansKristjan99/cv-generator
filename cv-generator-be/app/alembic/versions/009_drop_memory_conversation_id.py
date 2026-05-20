"""drop_memory_conversation_id

Revision ID: 009_drop_memory_conversation_id
Revises: 008_grant_unlimited_admin
Create Date: 2026-05-20
"""

from alembic import op
import sqlalchemy as sa

revision = "009_drop_memory_conversation_id"
down_revision = "008_grant_unlimited_admin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("users", "memory_conversation_id")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column("memory_conversation_id", sa.Text(), nullable=True),
    )
