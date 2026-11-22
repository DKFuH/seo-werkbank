"""Editable and separately approvable SEO content proposals.

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "seo_content_proposals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("work_item_id", sa.Integer(), sa.ForeignKey("seo_work_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("proposed_text", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("marked_published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_seo_content_proposals_work_item_id", "seo_content_proposals", ["work_item_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_seo_content_proposals_work_item_id", table_name="seo_content_proposals")
    op.drop_table("seo_content_proposals")
