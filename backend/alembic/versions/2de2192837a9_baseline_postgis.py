"""baseline: verify postgis extension is present

Revision ID: 2de2192837a9
Revises:
Create Date: 2026-08-14

"""
from typing import Sequence, Union

from alembic import op

revision: str = "2de2192837a9"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    exists = conn.exec_driver_sql(
        "SELECT 1 FROM pg_extension WHERE extname = 'postgis'"
    ).scalar()
    if not exists:
        raise RuntimeError(
            "PostGIS extension is not installed in this database. "
            "It must be created by a superuser during environment "
            "provisioning (see infra/postgres-init.sql) before running "
            "migrations."
        )


def downgrade() -> None:
    pass
