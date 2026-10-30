from collections.abc import Sequence

from alembic import op

revision: str = "f48d588d67a7"
down_revision: str | None = "bd00445ce2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("REVOKE TRUNCATE ON identity_issuance_event FROM bharosa_app")


def downgrade() -> None:
    op.execute("GRANT TRUNCATE ON identity_issuance_event TO bharosa_app")
