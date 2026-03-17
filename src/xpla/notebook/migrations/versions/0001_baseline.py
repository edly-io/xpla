"""Baseline: course, page, pageactivity tables.

Revision ID: 0001
Revises:
Create Date: 2026-03-05
"""

from typing import Sequence, Union

# pylint: disable=no-member
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "page",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "course_id",
            sa.String(),
            sa.ForeignKey("course.id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "pageactivity",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "page_id",
            sa.String(),
            sa.ForeignKey("page.id"),
            nullable=False,
        ),
        sa.Column("activity_type", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("pageactivity")
    op.drop_table("page")
    op.drop_table("course")
