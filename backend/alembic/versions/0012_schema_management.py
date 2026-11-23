"""Schema templates and explicit JSON-LD proposal discriminator.

Revision ID: 0012
Revises: 0011
"""
import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("seo_content_proposals") as batch:
        batch.add_column(sa.Column("content_type", sa.String(40), nullable=False, server_default="text/plain"))
    op.create_table(
        "schema_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("schema_type", sa.String(80), nullable=False),
        sa.Column("url_pattern", sa.String(300), nullable=False, server_default="*"),
        sa.Column("field_mapping", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_schema_templates_site_id", "schema_templates", ["site_id"])


def downgrade() -> None:
    op.drop_index("ix_schema_templates_site_id", table_name="schema_templates")
    op.drop_table("schema_templates")
    with op.batch_alter_table("seo_content_proposals") as batch:
        batch.drop_column("content_type")
