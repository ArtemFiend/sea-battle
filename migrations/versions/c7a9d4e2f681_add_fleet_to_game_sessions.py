"""add fleet to game sessions

Revision ID: c7a9d4e2f681
Revises: 751f9a8a82f6
Create Date: 2026-09-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c7a9d4e2f681"
down_revision: str | Sequence[str] | None = "751f9a8a82f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "game_sessions",
        sa.Column(
            "fleet",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.alter_column("game_sessions", "fleet", server_default=None)


def downgrade() -> None:
    op.drop_column("game_sessions", "fleet")
