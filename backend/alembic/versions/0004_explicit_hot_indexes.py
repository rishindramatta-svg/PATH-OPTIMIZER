"""Create composite indexes on pre-existing tables."""

from sqlalchemy import inspect

from alembic import op

revision = "0004_hot_indexes"
down_revision = "0003_shared"
branch_labels = None
depends_on = None


def upgrade():
    indexes = {
        table: {item["name"] for item in inspect(op.get_bind()).get_indexes(table)}
        for table in ("interactions", "mastery", "path_steps", "course_enrollments")
    }
    if "ix_interactions_user_created" not in indexes["interactions"]:
        op.create_index("ix_interactions_user_created", "interactions", ["user_id", "created_at"])
    if "ix_mastery_user_concept" not in indexes["mastery"]:
        op.create_index(
            "ix_mastery_user_concept",
            "mastery",
            ["user_id", "concept_slug"],
            unique=True,
        )
    if "ix_path_steps_user_position" not in indexes["path_steps"]:
        op.create_index("ix_path_steps_user_position", "path_steps", ["user_id", "position"])
    if "ix_course_enrollments_user_course_role" not in indexes["course_enrollments"]:
        op.create_index(
            "ix_course_enrollments_user_course_role",
            "course_enrollments",
            ["user_id", "course_id", "role"],
            unique=True,
        )


def downgrade():
    pass
