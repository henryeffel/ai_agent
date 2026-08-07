"""Persist human-readable evidence details on action plans."""

from alembic import op
import sqlalchemy as sa


revision = "20260807_0002"
down_revision = "20260806_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "action_plans",
        sa.Column("evidence", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade():
    op.drop_column("action_plans", "evidence")
