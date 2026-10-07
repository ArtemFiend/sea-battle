import asyncio

import pytest
from httpx2 import MockTransport, Request, Response

from sea_battle.arena.service import HTTPGameService, ServiceProtocolError


def test_http_adapter_rejects_wrong_status_code() -> None:
    transport = MockTransport(lambda _request: Response(500))

    async def exercise() -> None:
        async with HTTPGameService(
            "http://service.test",
            transport=transport,
        ) as service:
            with pytest.raises(ServiceProtocolError, match="returned 500"):
                await service.start_game()

    asyncio.run(exercise())


def test_http_adapter_rejects_malformed_game_response() -> None:
    def response(_request: Request) -> Response:
        return Response(
            201,
            json={"session_id": 123, "ships": "not-a-list"},
        )

    async def exercise() -> None:
        async with HTTPGameService(
            "http://service.test",
            transport=MockTransport(response),
        ) as service:
            with pytest.raises(
                ServiceProtocolError,
                match="Invalid response from POST /game",
            ):
                await service.start_game()

    asyncio.run(exercise())
