"""Create course enrollment, path steps, and cross-dialect hot indexes."""

from alembic import op
from app.models import Base

revision = "0003_shared"
down_revision = "0002_legacy"
branch_labels = None
depends_on = None


def upgrade():
    # create_all is idempotent and creates newly introduced tables/indexes on either dialect.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    pass
