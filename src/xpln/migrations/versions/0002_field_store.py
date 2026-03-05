"""Add field_store tables: fieldentry, fieldlogentry, fieldlogseq.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-05
"""

from typing import Sequence, Union

# pylint: disable=no-member
from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fieldentry",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
    )
    op.create_table(
        "fieldlogentry",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("key", "entry_id"),
    )
    op.create_table(
        "fieldlogseq",
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("next_id", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("fieldlogseq")
    op.drop_table("fieldlogentry")
    op.drop_table("fieldentry")
