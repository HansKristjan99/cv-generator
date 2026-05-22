"""cv_session source CV (text + pdf) for previewing the submitted CV

Revision ID: 014_cv_session_source
Revises: 013_cv_session_kind
Create Date: 2026-05-22
"""

from alembic import op
import sqlalchemy as sa

revision = "014_cv_session_source"
down_revision = "013_cv_session_kind"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cv_sessions", sa.Column("source_cv_text", sa.Text(), nullable=True))
    op.add_column("cv_sessions", sa.Column("source_cv_pdf_base64", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("cv_sessions", "source_cv_pdf_base64")
    op.drop_column("cv_sessions", "source_cv_text")
