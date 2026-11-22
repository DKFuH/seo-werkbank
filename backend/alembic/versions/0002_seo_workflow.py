"""Add site-scoped SEO work items and dated GSC performance snapshots.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "seo_work_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("target_url", sa.String(2048), nullable=True),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("evidence_url", sa.String(2048), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_seo_work_items_site_id", "seo_work_items", ["site_id"])
    op.create_index("ix_seo_work_items_site_kind", "seo_work_items", ["site_id", "kind"])
    op.create_table(
        "seo_performance_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("work_item_id", sa.Integer(), sa.ForeignKey("seo_work_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(20), nullable=False),
        sa.Column("source", sa.String(10), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("clicks", sa.Float(), nullable=False),
        sa.Column("impressions", sa.Float(), nullable=False),
        sa.Column("position", sa.Float(), nullable=True),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_seo_performance_snapshots_work_item_id", "seo_performance_snapshots", ["work_item_id"])


def downgrade() -> None:
    op.drop_index("ix_seo_performance_snapshots_work_item_id", table_name="seo_performance_snapshots")
    op.drop_table("seo_performance_snapshots")
    op.drop_index("ix_seo_work_items_site_kind", table_name="seo_work_items")
    op.drop_index("ix_seo_work_items_site_id", table_name="seo_work_items")
    op.drop_table("seo_work_items")
