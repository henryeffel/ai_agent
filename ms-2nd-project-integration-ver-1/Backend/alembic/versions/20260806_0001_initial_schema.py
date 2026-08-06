"""Create action workflow and knowledge tables."""

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa


revision = "20260806_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == "postgresql"
    if is_postgresql:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "action_plans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("meeting_id", sa.String(100), nullable=False),
        sa.Column("evidence_chunk_ids", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("approved_by", sa.String(320), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_action_plans_meeting_id", "action_plans", ["meeting_id"])
    op.create_index("ix_action_plans_status", "action_plans", ["status"])

    op.create_table(
        "action_executions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("action_id", sa.String(100), nullable=False),
        sa.Column("action_plan_id", sa.String(36), nullable=False),
        sa.Column("tool", sa.String(30), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(100), nullable=True),
        sa.Column("external_resource_id", sa.String(500), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["action_plan_id"], ["action_plans.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("action_id", name="uq_action_executions_action_id"),
    )
    op.create_index("ix_action_executions_action_id", "action_executions", ["action_id"])
    op.create_index("ix_action_executions_action_plan_id", "action_executions", ["action_plan_id"])
    op.create_index("ix_action_executions_status", "action_executions", ["status"])

    embedding_type = Vector(2048) if is_postgresql else sa.JSON()
    op.create_table(
        "document_chunks",
        sa.Column("chunk_id", sa.String(100), primary_key=True),
        sa.Column("document_id", sa.String(100), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("section", sa.String(300), nullable=True),
        sa.Column("source_url", sa.String(2000), nullable=True),
        sa.Column("document_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("document_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("embedding", embedding_type, nullable=False),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_category", "document_chunks", ["category"])


def downgrade():
    op.drop_index("ix_document_chunks_category", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("ix_action_executions_status", table_name="action_executions")
    op.drop_index("ix_action_executions_action_plan_id", table_name="action_executions")
    op.drop_index("ix_action_executions_action_id", table_name="action_executions")
    op.drop_table("action_executions")
    op.drop_index("ix_action_plans_status", table_name="action_plans")
    op.drop_index("ix_action_plans_meeting_id", table_name="action_plans")
    op.drop_table("action_plans")
