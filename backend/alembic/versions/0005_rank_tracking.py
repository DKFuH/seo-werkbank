"""Add explicit rank targets and observation history.

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rank_targets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("keyword", sa.String(500), nullable=False),
        sa.Column("engine", sa.String(24), nullable=False),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column("language", sa.String(2), nullable=False),
        sa.Column("device", sa.String(12), nullable=False),
        sa.Column("location", sa.String(120), nullable=True),
        sa.Column("landing_url", sa.String(2048), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_rank_targets_site_id", "rank_targets", ["site_id"])
    op.create_index("ix_rank_targets_site_keyword", "rank_targets", ["site_id", "keyword"])
    op.create_table(
        "rank_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("target_id", sa.Integer(), sa.ForeignKey("rank_targets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("result_url", sa.String(2048), nullable=True),
        sa.Column("search_depth", sa.Integer(), nullable=False),
        sa.Column("serp_features", sa.JSON(), nullable=False),
        sa.Column("notes", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_rank_observations_target_id", "rank_observations", ["target_id"])


def downgrade() -> None:
    op.drop_index("ix_rank_observations_target_id", table_name="rank_observations")
    op.drop_table("rank_observations")
    op.drop_index("ix_rank_targets_site_keyword", table_name="rank_targets")
    op.drop_index("ix_rank_targets_site_id", table_name="rank_targets")
    op.drop_table("rank_targets")
