"""merge 009 migration heads

Revision ID: 010_merge_009_heads
Revises: 009_conversation_history, 009_drop_memory_conversation_id
Create Date: 2026-05-21
"""

revision = "010_merge_009_heads"
down_revision = ("009_conversation_history", "009_drop_memory_conversation_id")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
