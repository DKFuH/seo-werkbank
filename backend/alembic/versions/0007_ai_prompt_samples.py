"""Store explicit AI prompt tests and sampled model answers.

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_prompt_tests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("brand_terms", sa.JSON(), nullable=False),
        sa.Column("competitor_terms", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ai_prompt_tests_site_id", "ai_prompt_tests", ["site_id"])
    op.create_table(
        "ai_prompt_samples",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("test_id", sa.Integer(), sa.ForeignKey("ai_prompt_tests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model_name", sa.String(120), nullable=True),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ai_prompt_samples_test_id", "ai_prompt_samples", ["test_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_prompt_samples_test_id", table_name="ai_prompt_samples")
    op.drop_table("ai_prompt_samples")
    op.drop_index("ix_ai_prompt_tests_site_id", table_name="ai_prompt_tests")
    op.drop_table("ai_prompt_tests")
