"""cv_session job_requirements

Caches the requirements-gate analysis (extracted once per chat) on the session,
linked to the CV session it belongs to.

Revision ID: 016_cv_session_job_requirements
Revises: 015_flatten_skills
Create Date: 2026-05-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "016_cv_session_job_requirements"
down_revision = "015_flatten_skills"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cv_sessions",
        sa.Column("job_requirements", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cv_sessions", "job_requirements")
