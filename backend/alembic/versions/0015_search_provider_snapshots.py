"""Search provider evidence snapshots."""
import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "search_provider_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(24), nullable=False),
        sa.Column("operation", sa.String(40), nullable=False),
        sa.Column("property_url", sa.String(2048), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_search_provider_snapshots_site_id", "search_provider_snapshots", ["site_id"])


def downgrade():
    op.drop_index("ix_search_provider_snapshots_site_id", table_name="search_provider_snapshots")
    op.drop_table("search_provider_snapshots")
