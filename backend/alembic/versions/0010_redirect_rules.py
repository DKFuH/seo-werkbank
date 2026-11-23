"""Redirect planning records.

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "redirect_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=False),
        sa.Column("target_url", sa.String(2048), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("origin", sa.String(20), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_redirect_rules_site_id", "redirect_rules", ["site_id"])
    op.create_index("ix_redirect_rules_site_state", "redirect_rules", ["site_id", "state"])


def downgrade() -> None:
    op.drop_index("ix_redirect_rules_site_state", table_name="redirect_rules")
    op.drop_index("ix_redirect_rules_site_id", table_name="redirect_rules")
    op.drop_table("redirect_rules")
