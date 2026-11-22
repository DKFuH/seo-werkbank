"""Site-scoped, source-aware SEO research records.

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "seo_research_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_seo_research_records_site_id", "seo_research_records", ["site_id"])
    op.create_index("ix_seo_research_site_kind", "seo_research_records", ["site_id", "kind"])


def downgrade() -> None:
    op.drop_index("ix_seo_research_site_kind", table_name="seo_research_records")
    op.drop_index("ix_seo_research_records_site_id", table_name="seo_research_records")
    op.drop_table("seo_research_records")
