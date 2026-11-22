"""Manually recorded AI visibility observations.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_visibility_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(30), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("brand_mentioned", sa.Boolean(), nullable=False),
        sa.Column("cited_url", sa.String(2048), nullable=True),
        sa.Column("evidence_url", sa.String(2048), nullable=True),
        sa.Column("response_excerpt", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ai_visibility_observations_site_id", "ai_visibility_observations", ["site_id"])
    op.create_index("ix_ai_visibility_site_platform_date", "ai_visibility_observations", ["site_id", "platform", "observed_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_visibility_site_platform_date", table_name="ai_visibility_observations")
    op.drop_index("ix_ai_visibility_observations_site_id", table_name="ai_visibility_observations")
    op.drop_table("ai_visibility_observations")
