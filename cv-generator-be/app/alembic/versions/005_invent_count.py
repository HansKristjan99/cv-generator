"""invent_count

Revision ID: 005_invent_count
Revises: 004_cv_sessions
Create Date: 2026-05-18
"""

from alembic import op
import sqlalchemy as sa

revision = "005_invent_count"
down_revision = "004_cv_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cv_sessions",
        sa.Column("invent_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("cv_sessions", "invent_count")
