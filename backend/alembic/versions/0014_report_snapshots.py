"""Immutable report snapshots.

Revision ID: 0014
Revises: 0013
"""
import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("origin", sa.String(24), nullable=False, server_default="manual"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_report_snapshots_site_id", "report_snapshots", ["site_id"])


def downgrade() -> None:
    op.drop_index("ix_report_snapshots_site_id", table_name="report_snapshots")
    op.drop_table("report_snapshots")
