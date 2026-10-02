import asyncio
import time
import uuid
from dataclasses import dataclass

from httpx2 import ASGITransport, AsyncClient, Response

from sea_battle.db.models import GameSession
from sea_battle.db.session import async_session_factory
from sea_battle.main import app

SESSION_COUNT = 5
MAX_RESPONSE_SECONDS = 1.0


@dataclass(frozen=True)
class SessionRecord:
    session_id: uuid.UUID
    fleet: list[dict[str, list[str]]]
    received_shot: str
    outgoing_shot: str


async def _request(
    client: AsyncClient,
    method: str,
    path: str,
    **kwargs: object,
) -> Response:
    started_at = time.perf_counter()
    response = await client.request(method, path, **kwargs)
    elapsed = time.perf_counter() - started_at

    assert elapsed < MAX_RESPONSE_SECONDS, (
        f"{method} {path} took {elapsed:.3f} seconds"
    )
    return response


async def _play_game(
    client: AsyncClient,
    game_index: int,
    created_ids: list[uuid.UUID],
) -> SessionRecord:
    create_response = await _request(client, "POST", "/game")
    assert create_response.status_code == 201
    create_payload = create_response.json()
    session_id = uuid.UUID(create_payload["session_id"])
    created_ids.append(session_id)

    received_shot = f"{chr(ord('A') + game_index)}10"
    opponent_response = await _request(
        client,
        "POST",
        f"/game/{session_id}/opponent-shot",
        json={"coordinate": received_shot},
    )
    assert opponent_response.status_code == 200

    shot_response = await _request(
        client,
        "POST",
        f"/game/{session_id}/shot",
    )
    assert shot_response.status_code == 200
    outgoing_shot = shot_response.json()["coordinate"]

    result_response = await _request(
        client,
        "POST",
        f"/game/{session_id}/shot/result",
        json={"result": "miss"},
    )
    assert result_response.status_code == 200

    close_response = await _request(
        client,
        "POST",
        f"/game/{session_id}/close",
    )
    assert close_response.status_code == 200

    return SessionRecord(
        session_id=session_id,
        fleet=create_payload["ships"],
        received_shot=received_shot,
        outgoing_shot=outgoing_shot,
    )


def test_parallel_games_keep_state_isolated_and_respond_within_limit() -> None:
    asyncio.run(_test_parallel_games())


async def _test_parallel_games() -> None:
    created_ids: list[uuid.UUID] = []
    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            records = await asyncio.gather(
                *(
                    _play_game(client, index, created_ids)
                    for index in range(SESSION_COUNT)
                )
            )

        assert len({record.session_id for record in records}) == SESSION_COUNT
        await _assert_sessions_are_isolated(records)
    finally:
        await _delete_games(created_ids)


async def _assert_sessions_are_isolated(
    records: list[SessionRecord],
) -> None:
    async with async_session_factory() as session:
        for record in records:
            game = await session.get(GameSession, record.session_id)

            assert game is not None
            assert game.fleet == record.fleet
            assert game.received_shots == [record.received_shot]
            assert game.outgoing_shots == [
                {"coordinate": record.outgoing_shot, "result": "miss"}
            ]
            assert game.status == "closed"
            assert game.finished_at is not None


def test_parallel_close_allows_only_one_success() -> None:
    asyncio.run(_test_parallel_close())


async def _test_parallel_close() -> None:
    created_ids: list[uuid.UUID] = []
    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            create_response = await _request(client, "POST", "/game")
            session_id = uuid.UUID(create_response.json()["session_id"])
            created_ids.append(session_id)

            responses = await asyncio.gather(
                _request(client, "POST", f"/game/{session_id}/close"),
                _request(client, "POST", f"/game/{session_id}/close"),
            )

        assert sorted(response.status_code for response in responses) == [200, 400]
    finally:
        await _delete_games(created_ids)


def test_parallel_requests_in_one_game_keep_state_consistent() -> None:
    asyncio.run(_test_parallel_requests_in_one_game())


async def _test_parallel_requests_in_one_game() -> None:
    created_ids: list[uuid.UUID] = []
    coordinates = ["A1", "B2", "C3", "D4", "E5"]
    results = ["miss", "hit"]
    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            create_response = await _request(client, "POST", "/game")
            assert create_response.status_code == 201
            session_id = uuid.UUID(create_response.json()["session_id"])
            created_ids.append(session_id)

            opponent_responses = await asyncio.gather(
                *(
                    _request(
                        client,
                        "POST",
                        f"/game/{session_id}/opponent-shot",
                        json={"coordinate": coordinate},
                    )
                    for coordinate in coordinates
                )
            )
            assert all(
                response.status_code == 200
                for response in opponent_responses
            )

            shot_responses = await asyncio.gather(
                _request(client, "POST", f"/game/{session_id}/shot"),
                _request(client, "POST", f"/game/{session_id}/shot"),
            )
            assert sorted(
                response.status_code for response in shot_responses
            ) == [200, 409]
            successful_shot = next(
                response
                for response in shot_responses
                if response.status_code == 200
            ).json()["coordinate"]

            result_responses = await asyncio.gather(
                *(
                    _request(
                        client,
                        "POST",
                        f"/game/{session_id}/shot/result",
                        json={"result": result},
                    )
                    for result in results
                )
            )

        assert sorted(
            response.status_code for response in result_responses
        ) == [200, 409]
        accepted_result = next(
            result
            for result, response in zip(results, result_responses, strict=True)
            if response.status_code == 200
        )
        await _assert_consistent_game_state(
            session_id,
            coordinates,
            successful_shot,
            accepted_result,
        )
    finally:
        await _delete_games(created_ids)


async def _assert_consistent_game_state(
    session_id: uuid.UUID,
    received_shots: list[str],
    outgoing_shot: str,
    result: str,
) -> None:
    async with async_session_factory() as session:
        game = await session.get(GameSession, session_id)

        assert game is not None
        assert len(game.received_shots) == len(received_shots)
        assert set(game.received_shots) == set(received_shots)
        assert game.pending_shot is None
        assert game.outgoing_shots == [
            {"coordinate": outgoing_shot, "result": result}
        ]


async def _delete_games(session_ids: list[uuid.UUID]) -> None:
    async with async_session_factory() as session:
        for session_id in session_ids:
            game = await session.get(GameSession, session_id)
            if game is not None:
                await session.delete(game)
        await session.commit()
