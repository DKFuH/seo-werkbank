"""Import metadata and privacy-preserving aggregated access log tables.

Revision ID: 0011
Revises: 0010
"""
import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "log_imports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("format", sa.String(24), nullable=False),
        sa.Column("state", sa.String(20), nullable=False, server_default="processing"),
        sa.Column("lines_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lines_parsed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lines_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_log_imports_site_id", "log_imports", ["site_id"])
    op.create_table(
        "log_aggregates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("import_id", sa.Integer(), sa.ForeignKey("log_imports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("path", sa.String(2048), nullable=False),
        sa.Column("status", sa.Integer(), nullable=False),
        sa.Column("agent_class", sa.String(30), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
    )
    op.create_index("ix_log_aggregates_import_id", "log_aggregates", ["import_id"])
    op.create_index("ix_log_aggregate_day", "log_aggregates", ["import_id", "day"])
    op.create_table(
        "log_404",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("import_id", sa.Integer(), sa.ForeignKey("log_imports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("path", sa.String(2048), nullable=False),
        sa.Column("referrer_host", sa.String(255), nullable=False, server_default=""),
        sa.Column("agent_class", sa.String(30), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("first_seen", sa.DateTime(), nullable=False),
        sa.Column("last_seen", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_log_404_import_id", "log_404", ["import_id"])


def downgrade() -> None:
    op.drop_index("ix_log_404_import_id", table_name="log_404")
    op.drop_table("log_404")
    op.drop_index("ix_log_aggregate_day", table_name="log_aggregates")
    op.drop_index("ix_log_aggregates_import_id", table_name="log_aggregates")
    op.drop_table("log_aggregates")
    op.drop_index("ix_log_imports_site_id", table_name="log_imports")
    op.drop_table("log_imports")
