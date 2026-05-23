"""flatten skills into a per-user keyword cloud

Drops skill categories and the proficiency column: skills become a flat,
de-duplicated list of keyword strings per user. Grouping now happens only at
CV-generation time, not in storage.

Revision ID: 015_flatten_skills
Revises: 014_cv_session_source
Create Date: 2026-05-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "015_flatten_skills"
down_revision = "014_cv_session_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("fk_skills_skill_category_id_skill_categories", "skills", type_="foreignkey")
    op.drop_column("skills", "skill_category_id")
    op.drop_column("skills", "proficiency")
    op.drop_table("skill_categories")

    # Collapse to one row per (user_id, name), case-insensitive, before enforcing uniqueness.
    op.execute(
        """
        DELETE FROM skills a
        USING skills b
        WHERE a.user_id = b.user_id
          AND lower(a.name) = lower(b.name)
          AND a.ctid > b.ctid
        """
    )
    op.create_unique_constraint("uq_skills_user_id_name", "skills", ["user_id", "name"])


def downgrade() -> None:
    op.drop_constraint("uq_skills_user_id_name", "skills", type_="unique")
    op.create_table(
        "skill_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.add_column("skills", sa.Column("proficiency", sa.Text(), nullable=True))
    op.add_column(
        "skills",
        sa.Column("skill_category_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_skills_skill_category_id_skill_categories",
        "skills",
        "skill_categories",
        ["skill_category_id"],
        ["id"],
        ondelete="CASCADE",
    )
