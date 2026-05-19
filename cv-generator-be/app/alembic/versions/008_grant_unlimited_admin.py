"""grant_unlimited_admin

Revision ID: 008_grant_unlimited_admin
Revises: 007_unlimited_users
Create Date: 2026-05-19
"""

from alembic import op

revision = "008_grant_unlimited_admin"
down_revision = "007_unlimited_users"
branch_labels = None
depends_on = None

_EMAIL = "hans.kristjan.veri@gmail.com"


def upgrade() -> None:
    op.execute(f"UPDATE users SET is_unlimited = true WHERE email = '{_EMAIL}'")


def downgrade() -> None:
    op.execute(f"UPDATE users SET is_unlimited = false WHERE email = '{_EMAIL}'")
