"""skill_categories

Revision ID: 003_skill_categories
Revises: 002_memory_notes
Create Date: 2026-05-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003_skill_categories"
down_revision = "002_memory_notes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "skill_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.execute("DELETE FROM skills")
    op.add_column(
        "skills",
        sa.Column("skill_category_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_foreign_key(
        "fk_skills_skill_category_id_skill_categories",
        "skills",
        "skill_categories",
        ["skill_category_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_skills_skill_category_id_skill_categories", "skills", type_="foreignkey")
    op.drop_column("skills", "skill_category_id")
    op.drop_table("skill_categories")
