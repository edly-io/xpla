"""Add user / user_session tables and course.owner_id.

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-10
"""

from datetime import datetime, timezone
from typing import Sequence, Union
from uuid import uuid4

# pylint: disable=no-member
from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("password_salt", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("email", name="uq_user_email"),
    )
    op.create_index("ix_user_email", "user", ["email"], unique=True)

    op.create_table(
        "usersession",
        sa.Column("token", sa.String(), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("user.id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_usersession_user_id", "usersession", ["user_id"])

    # Add owner_id to course. Existing rows (if any) get adopted by a synthetic
    # "legacy" user so the NOT NULL constraint can be enforced.
    with op.batch_alter_table("course") as batch:
        batch.add_column(sa.Column("owner_id", sa.String(), nullable=True))

    bind = op.get_bind()
    has_courses = bind.execute(sa.text("SELECT 1 FROM course LIMIT 1")).first()
    if has_courses:
        legacy_id = uuid4().hex
        bind.execute(
            sa.text(
                "INSERT INTO user (id, email, password_hash, password_salt, created_at) "
                "VALUES (:id, :email, '', '', :now)"
            ),
            {
                "id": legacy_id,
                "email": f"legacy-{legacy_id}@xpln.local",
                "now": datetime.now(timezone.utc),
            },
        )
        bind.execute(
            sa.text("UPDATE course SET owner_id = :oid WHERE owner_id IS NULL"),
            {"oid": legacy_id},
        )

    with op.batch_alter_table("course") as batch:
        batch.alter_column("owner_id", nullable=False)
        batch.create_foreign_key(
            "fk_course_owner_id_user", "user", ["owner_id"], ["id"]
        )
        batch.create_index("ix_course_owner_id", ["owner_id"])


def downgrade() -> None:
    with op.batch_alter_table("course") as batch:
        batch.drop_index("ix_course_owner_id")
        batch.drop_constraint("fk_course_owner_id_user", type_="foreignkey")
        batch.drop_column("owner_id")
    op.drop_index("ix_usersession_user_id", table_name="usersession")
    op.drop_table("usersession")
    op.drop_index("ix_user_email", table_name="user")
    op.drop_table("user")
