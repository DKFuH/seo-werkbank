"""Enforce unique redirect source per site.

Revision ID: 0013
Revises: 0012

Existing duplicate rows are intentionally not deleted: users must review
and resolve them before applying the constraint.
"""
import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    duplicates = connection.execute(sa.text(
        "SELECT site_id, source_url, COUNT(*) AS n "
        "FROM redirect_rules GROUP BY site_id, source_url HAVING COUNT(*) > 1 LIMIT 1"
    )).first()
    if duplicates:
        raise RuntimeError(
            "Redirect migration 0013: duplicate sources already exist. "
            "Review redirect_rules for (site_id, source_url) duplicates before upgrade."
        )
    op.create_index("ux_redirect_rules_site_source", "redirect_rules",
                    ["site_id", "source_url"], unique=True)


def downgrade() -> None:
    op.drop_index("ux_redirect_rules_site_source", table_name="redirect_rules")
