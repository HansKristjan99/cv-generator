"""drop cv_session kind

A session is always a CV; cover letters are produced per-turn (via /cover), not as a
session type, so the session-level cv/cover_letter discriminator is removed.

Revision ID: 017_drop_cv_session_kind
Revises: 016_cv_session_job_requirements
Create Date: 2026-05-24
"""

from alembic import op
import sqlalchemy as sa

revision = "017_drop_cv_session_kind"
down_revision = "016_cv_session_job_requirements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("cv_sessions", "kind")


def downgrade() -> None:
    op.add_column(
        "cv_sessions",
        sa.Column("kind", sa.Text(), nullable=False, server_default="cv"),
    )
