"""Add columns introduced after the initial local SQLite schema."""

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision = "0002_legacy"
down_revision = "0001_current"
branch_labels = None
depends_on = None


def upgrade():
    inspector = inspect(op.get_bind())
    additions = {
        "interactions": [
            ("anomaly_reason", sa.String(255), ""),
            ("session_id", sa.String(36), ""),
            ("review_status", sa.String(24), "pending"),
            ("mastery_after", sa.Float(), 0.2),
        ],
        "misconceptions": [
            ("evidence_count", sa.Integer(), 1),
            ("last_seen_at", sa.DateTime(), None),
        ],
    }
    for table, cols in additions.items():
        existing = {col["name"] for col in inspector.get_columns(table)}
        for name, type_, default in cols:
            if name not in existing:
                server_default = sa.text(repr(default)) if default is not None else None
                op.add_column(
                    table,
                    sa.Column(
                        name,
                        type_,
                        nullable=name == "last_seen_at",
                        server_default=server_default,
                    ),
                )
    # Use a dialect-portable server expression for rows upgraded from the old schema.
    op.execute("UPDATE misconceptions SET last_seen_at = CURRENT_TIMESTAMP WHERE last_seen_at IS NULL")


def downgrade():
    pass
