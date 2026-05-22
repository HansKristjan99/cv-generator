"""cv_session kind (cv | cover_letter)

Revision ID: 013_cv_session_kind
Revises: 012_cv_session_page_count
Create Date: 2026-05-22
"""

from alembic import op
import sqlalchemy as sa

revision = "013_cv_session_kind"
down_revision = "012_cv_session_page_count"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cv_sessions",
        sa.Column("kind", sa.Text(), nullable=False, server_default="cv"),
    )


def downgrade() -> None:
    op.drop_column("cv_sessions", "kind")
