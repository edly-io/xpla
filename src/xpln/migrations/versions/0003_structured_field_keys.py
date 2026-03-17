"""Split field_store single-key columns into structured multi-column keys.

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-17
"""

from typing import Sequence, Union

# pylint: disable=no-member
from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The 5 key columns shared by all 3 tables
_KEY_COLUMNS = [
    sa.Column("course_id", sa.String(), nullable=False),
    sa.Column("activity_name", sa.String(), nullable=False),
    sa.Column("activity_id", sa.String(), nullable=False),
    sa.Column("user_id", sa.String(), nullable=False),
    sa.Column("key", sa.String(), nullable=False),
]

_KEY_NAMES = ["course_id", "activity_name", "activity_id", "user_id", "key"]


def _create_indexes(table_name: str) -> None:
    for col_name in _KEY_NAMES:
        op.create_index(f"ix_{table_name}_{col_name}", table_name, [col_name])


def upgrade() -> None:
    # Drop old tables
    op.drop_table("fieldlogseq")
    op.drop_table("fieldlogentry")
    op.drop_table("fieldentry")

    # Recreate with structured keys
    op.create_table(
        "fieldentry",
        sa.Column("id", sa.Integer(), primary_key=True),
        *[c.copy() for c in _KEY_COLUMNS],
        sa.Column("value", sa.Text(), nullable=False),
        sa.UniqueConstraint(*_KEY_NAMES),
    )
    _create_indexes("fieldentry")

    op.create_table(
        "fieldlogentry",
        sa.Column("id", sa.Integer(), primary_key=True),
        *[c.copy() for c in _KEY_COLUMNS],
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.UniqueConstraint(*_KEY_NAMES, "entry_id"),
    )
    _create_indexes("fieldlogentry")

    op.create_table(
        "fieldlogseq",
        sa.Column("id", sa.Integer(), primary_key=True),
        *[c.copy() for c in _KEY_COLUMNS],
        sa.Column("next_id", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint(*_KEY_NAMES),
    )
    _create_indexes("fieldlogseq")


def downgrade() -> None:
    op.drop_table("fieldlogseq")
    op.drop_table("fieldlogentry")
    op.drop_table("fieldentry")

    # Restore old single-key schema
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
