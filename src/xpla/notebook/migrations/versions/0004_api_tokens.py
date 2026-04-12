"""API tokens

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-12 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "apitoken",
        sa.Column("token", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("token"),
    )
    with op.batch_alter_table("apitoken", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_apitoken_user_id"), ["user_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("apitoken", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_apitoken_user_id"))
    op.drop_table("apitoken")
