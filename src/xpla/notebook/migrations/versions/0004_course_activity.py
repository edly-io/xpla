"""Add course_activity table for dashboard activities.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-09
"""

from typing import Sequence, Union

# pylint: disable=no-member
from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "courseactivity",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "course_id",
            sa.String(),
            sa.ForeignKey("course.id"),
            nullable=False,
        ),
        sa.Column("activity_type", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("courseactivity")
