"""Keyword portfolio: tracking flag, label, target URL, measurement, priority and a change journal.

Revision ID: 0009
Revises: 0008
"""
import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("keywords") as batch:
        batch.add_column(sa.Column("tracked", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("label", sa.String(40), nullable=True))
        batch.add_column(sa.Column("target_url", sa.String(2048), nullable=True))
        batch.add_column(sa.Column("measurement", sa.String(20), nullable=False, server_default="national"))
        batch.add_column(sa.Column("priority", sa.Integer(), nullable=False, server_default="2"))
    op.create_table(
        "keyword_notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("keyword_id", sa.Integer(), sa.ForeignKey("keywords.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("details", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_keyword_notes_keyword_id", "keyword_notes", ["keyword_id"])


def downgrade() -> None:
    op.drop_table("keyword_notes")
    with op.batch_alter_table("keywords") as batch:
        for col in ("priority", "measurement", "target_url", "label", "tracked"):
            batch.drop_column(col)
