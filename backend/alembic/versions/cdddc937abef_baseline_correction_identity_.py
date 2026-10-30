from collections.abc import Sequence

from alembic import op

revision: str = "cdddc937abef"
down_revision: str | None = "f4ae5d07fe85"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("REVOKE UPDATE, DELETE ON identity_issuance_event FROM bharosa_app")


def downgrade() -> None:
    op.execute("GRANT UPDATE, DELETE ON identity_issuance_event TO bharosa_app")
