"""cv_session page count

Revision ID: 012_cv_session_page_count
Revises: 011_session_generation_state
Create Date: 2026-05-22
"""

from alembic import op
import sqlalchemy as sa

revision = "012_cv_session_page_count"
down_revision = "011_session_generation_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cv_sessions",
        sa.Column("page_count", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("cv_sessions", "page_count")
