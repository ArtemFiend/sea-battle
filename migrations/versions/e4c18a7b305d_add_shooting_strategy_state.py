"""add shooting strategy state

Revision ID: e4c18a7b305d
Revises: d8b3f91a4620
Create Date: 2026-09-22

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e4c18a7b305d"
down_revision: str | Sequence[str] | None = "d8b3f91a4620"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for column_name in ("outgoing_shots", "target_hits", "target_queue"):
        op.add_column(
            "game_sessions",
            sa.Column(
                column_name,
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'[]'::jsonb"),
                nullable=False,
            ),
        )
        op.alter_column("game_sessions", column_name, server_default=None)

    op.add_column(
        "game_sessions",
        sa.Column("pending_shot", sa.String(length=3), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("game_sessions", "pending_shot")
    op.drop_column("game_sessions", "target_queue")
    op.drop_column("game_sessions", "target_hits")
    op.drop_column("game_sessions", "outgoing_shots")
