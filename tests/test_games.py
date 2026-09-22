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


def test_opponent_shots_are_resolved_and_persisted() -> None:
    create_response = client.post("/game")
    payload = create_response.json()
    session_id = uuid.UUID(payload["session_id"])
    ships = payload["ships"]
    ship = max(ships, key=lambda item: len(item["coordinates"]))
    ship_coordinates = ship["coordinates"]
    occupied = {
        coordinate
        for fleet_ship in ships
        for coordinate in fleet_ship["coordinates"]
    }
    miss_coordinate = next(
        f"{column}{row}"
        for column in "ABCDEFGHIJ"
        for row in range(1, 11)
        if f"{column}{row}" not in occupied
    )

    try:
        response = client.post(
            f"/game/{session_id}/opponent-shot",
            json={"coordinate": miss_coordinate},
        )
        assert response.status_code == 200
        assert response.json() == {"result": "miss"}

        for coordinate in ship_coordinates[:-1]:
            response = client.post(
                f"/game/{session_id}/opponent-shot",
                json={"coordinate": coordinate},
            )
            assert response.status_code == 200
            assert response.json() == {"result": "hit"}

        last_coordinate = ship_coordinates[-1]
        response = client.post(
            f"/game/{session_id}/opponent-shot",
            json={"coordinate": last_coordinate},
        )
        assert response.status_code == 200
        assert response.json() == {"result": "killed"}

        repeated_response = client.post(
            f"/game/{session_id}/opponent-shot",
            json={"coordinate": last_coordinate},
        )
        assert repeated_response.status_code == 200
        assert repeated_response.json() == {"result": "hit"}

        invalid_response = client.post(
            f"/game/{session_id}/opponent-shot",
            json={"coordinate": "K1"},
        )
        assert invalid_response.status_code == 400

        expected_shots = [miss_coordinate, *ship_coordinates]
        asyncio.run(_assert_received_shots(session_id, expected_shots))
    finally:
        asyncio.run(_delete_game(session_id))


def test_opponent_shot_returns_not_found_for_unknown_session() -> None:
    response = client.post(
        f"/game/{uuid.uuid4()}/opponent-shot",
        json={"coordinate": "A1"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Game session not found"}


def test_opponent_shot_returns_gone_for_finished_session() -> None:
    create_response = client.post("/game")
    session_id = uuid.UUID(create_response.json()["session_id"])
    asyncio.run(_set_game_status(session_id, "closed"))

    try:
        response = client.post(
            f"/game/{session_id}/opponent-shot",
            json={"coordinate": "A1"},
        )

        assert response.status_code == 410
        assert response.json() == {"detail": "Game session is finished"}
    finally:
        asyncio.run(_delete_game(session_id))


async def _assert_received_shots(
    session_id: uuid.UUID,
    expected_shots: list[str],
) -> None:
    async with async_session_factory() as session:
        saved_game = await session.get(GameSession, session_id)

        assert saved_game is not None
        assert saved_game.received_shots == expected_shots


async def _delete_game(session_id: uuid.UUID) -> None:
    async with async_session_factory() as session:
        saved_game = await session.get(GameSession, session_id)
        if saved_game is not None:
            await session.delete(saved_game)
            await session.commit()


async def _set_game_status(session_id: uuid.UUID, status: str) -> None:
    async with async_session_factory() as session:
        saved_game = await session.get(GameSession, session_id)
        assert saved_game is not None
        saved_game.status = status
        await session.commit()
