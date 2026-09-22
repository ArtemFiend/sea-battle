"""add received shots

Revision ID: d8b3f91a4620
Revises: c7a9d4e2f681
Create Date: 2026-09-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d8b3f91a4620"
down_revision: str | Sequence[str] | None = "c7a9d4e2f681"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "game_sessions",
        sa.Column(
            "received_shots",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.alter_column("game_sessions", "received_shots", server_default=None)


def downgrade() -> None:
    op.drop_column("game_sessions", "received_shots")
