"""cache rendered pdf bytes on saved cvs/cls

Revision ID: 020_saved_doc_pdf_cache
Revises: 019_job_applications
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa


revision = "020_saved_doc_pdf_cache"
down_revision = "019_job_applications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cvs", sa.Column("pdf_base64", sa.Text(), nullable=True))
    op.add_column("cls", sa.Column("pdf_base64", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("cls", "pdf_base64")
    op.drop_column("cvs", "pdf_base64")
