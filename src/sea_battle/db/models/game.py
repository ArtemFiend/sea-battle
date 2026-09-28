import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from sea_battle.db.base import Base


class GameSession(Base):
    __tablename__ = "game_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
    )

    fleet: Mapped[list[dict[str, list[str]]]] = mapped_column(
        JSONB,
        nullable=False,
    )

    received_shots: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    outgoing_shots: Mapped[list[dict[str, str | None]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    pending_shot: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
    )

    target_hits: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    target_queue: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
