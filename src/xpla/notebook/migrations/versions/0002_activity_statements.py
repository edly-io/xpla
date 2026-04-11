"""Activity statements

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-11 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "activitystatement",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("activity_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("activity_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("verb", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("activitystatement", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_activitystatement_activity_id"),
            ["activity_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_activitystatement_activity_name"),
            ["activity_name"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_activitystatement_course_id"),
            ["course_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_activitystatement_user_id"),
            ["user_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("activitystatement", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_activitystatement_user_id"))
        batch_op.drop_index(batch_op.f("ix_activitystatement_course_id"))
        batch_op.drop_index(batch_op.f("ix_activitystatement_activity_name"))
        batch_op.drop_index(batch_op.f("ix_activitystatement_activity_id"))

    op.drop_table("activitystatement")
