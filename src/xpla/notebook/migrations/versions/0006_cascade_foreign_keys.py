"""Add ON DELETE CASCADE to all foreign keys.

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-10
"""

from typing import Sequence, Union

# pylint: disable=no-member
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite requires batch_alter_table to modify foreign key constraints.
    # Each block recreates the table with ON DELETE CASCADE.

    with op.batch_alter_table("usersession") as batch_op:
        batch_op.drop_constraint("fk_usersession_user_id_user", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_usersession_user_id_user",
            "user",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("course") as batch_op:
        batch_op.drop_constraint("fk_course_owner_id_user", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_course_owner_id_user",
            "user",
            ["owner_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("page") as batch_op:
        batch_op.drop_constraint("fk_page_course_id_course", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_page_course_id_course",
            "course",
            ["course_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("pageactivity") as batch_op:
        batch_op.drop_constraint("fk_pageactivity_page_id_page", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_pageactivity_page_id_page",
            "page",
            ["page_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("courseactivity") as batch_op:
        batch_op.drop_constraint(
            "fk_courseactivity_course_id_course", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_courseactivity_course_id_course",
            "course",
            ["course_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    with op.batch_alter_table("courseactivity") as batch_op:
        batch_op.drop_constraint(
            "fk_courseactivity_course_id_course", type_="foreignkey"
        )
        batch_op.create_foreign_key(
            "fk_courseactivity_course_id_course", "course", ["course_id"], ["id"]
        )

    with op.batch_alter_table("pageactivity") as batch_op:
        batch_op.drop_constraint("fk_pageactivity_page_id_page", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_pageactivity_page_id_page", "page", ["page_id"], ["id"]
        )

    with op.batch_alter_table("page") as batch_op:
        batch_op.drop_constraint("fk_page_course_id_course", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_page_course_id_course", "course", ["course_id"], ["id"]
        )

    with op.batch_alter_table("course") as batch_op:
        batch_op.drop_constraint("fk_course_owner_id_user", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_course_owner_id_user", "user", ["owner_id"], ["id"]
        )

    with op.batch_alter_table("usersession") as batch_op:
        batch_op.drop_constraint("fk_usersession_user_id_user", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_usersession_user_id_user", "user", ["user_id"], ["id"]
        )
