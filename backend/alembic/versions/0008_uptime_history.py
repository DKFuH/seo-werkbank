"""Uptime check history and incidents for the Website Health monitor.

Revision ID: 0008
Revises: 0007
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "uptime_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("monitor_id", sa.Integer(), sa.ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("checked_at", sa.DateTime(), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("response_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.String(300), nullable=True),
    )
    op.create_index("ix_uptime_checks_monitor_id", "uptime_checks", ["monitor_id"])
    op.create_index("ix_uptime_checks_checked_at", "uptime_checks", ["checked_at"])
    op.create_index("ix_uptime_checks_monitor_time", "uptime_checks", ["monitor_id", "checked_at"])
    op.create_table(
        "uptime_incidents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("monitor_id", sa.Integer(), sa.ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("checks", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_uptime_incidents_monitor_id", "uptime_incidents", ["monitor_id"])
    op.create_index("ix_uptime_incidents_started_at", "uptime_incidents", ["started_at"])


def downgrade() -> None:
    op.drop_table("uptime_incidents")
    op.drop_table("uptime_checks")
