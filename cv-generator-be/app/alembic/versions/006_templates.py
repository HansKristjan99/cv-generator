"""templates

Revision ID: 006_templates
Revises: 005_invent_count
Create Date: 2026-05-18
"""

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "006_templates"
down_revision = "005_invent_count"
branch_labels = None
depends_on = None

_TEMPLATES = [
    {"id": str(uuid.uuid4()), "name": "Default", "slug": "default"},
    {"id": str(uuid.uuid4()), "name": "Harvard Classic", "slug": "harvard_classic"},
    {"id": str(uuid.uuid4()), "name": "Rover", "slug": "rover"},
]


def upgrade() -> None:
    op.create_table(
        "templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.UniqueConstraint("slug", name="uq_templates_slug"),
    )

    templates_table = sa.table(
        "templates",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.Text()),
        sa.column("slug", sa.Text()),
    )
    op.bulk_insert(templates_table, _TEMPLATES)

    op.add_column(
        "users",
        sa.Column(
            "preferred_template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "preferred_template_id")
    op.drop_table("templates")
