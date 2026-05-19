"""unlimited_users

Revision ID: 007_unlimited_users
Revises: 006_templates
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa

revision = "007_unlimited_users"
down_revision = "006_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_unlimited", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("users", "is_unlimited")
