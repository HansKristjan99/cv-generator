"""billing subscriptions

Revision ID: 018_billing_subscriptions
Revises: 017_drop_cv_session_kind
Create Date: 2026-05-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "018_billing_subscriptions"
down_revision = "017_drop_cv_session_kind"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("stripe_customer_id", sa.Text(), nullable=True))
    op.create_unique_constraint(
        "uq_users_stripe_customer_id",
        "users",
        ["stripe_customer_id"],
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subscription_type", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("stripe_customer_id", sa.Text(), nullable=False),
        sa.Column("stripe_subscription_id", sa.Text(), nullable=False),
        sa.Column("stripe_price_id", sa.Text(), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "stripe_subscription_id",
            name="uq_subscriptions_stripe_subscription_id",
        ),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_constraint("uq_users_stripe_customer_id", "users", type_="unique")
    op.drop_column("users", "stripe_customer_id")
