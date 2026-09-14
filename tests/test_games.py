import asyncio
import uuid

from fastapi.testclient import TestClient

from sea_battle.db.models import GameSession
from sea_battle.db.session import async_session_factory
from sea_battle.domain.fleet import validate_fleet
from sea_battle.main import app

client = TestClient(app)


def test_create_game_returns_and_persists_valid_fleet() -> None:
    response = client.post("/game")

    assert response.status_code == 201
    payload = response.json()
    session_id = uuid.UUID(payload["session_id"])
    fleet = tuple(tuple(ship["coordinates"]) for ship in payload["ships"])
    validate_fleet(fleet)

    asyncio.run(_assert_game_is_persisted(session_id, payload["ships"]))


async def _assert_game_is_persisted(
    session_id: uuid.UUID,
    ships: list[dict[str, list[str]]],
) -> None:
    try:
        async with async_session_factory() as session:
            saved_game = await session.get(GameSession, session_id)

            assert saved_game is not None
            assert saved_game.status == "active"
            assert saved_game.fleet == ships
    finally:
        async with async_session_factory() as session:
            saved_game = await session.get(GameSession, session_id)
            if saved_game is not None:
                await session.delete(saved_game)
                await session.commit()
