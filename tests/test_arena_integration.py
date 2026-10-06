import asyncio
import random

from httpx2 import ASGITransport

from sea_battle.arena import Arena, HTTPGameService, Player
from sea_battle.main import app


def test_two_http_services_play_complete_match() -> None:
    async def exercise() -> None:
        async with (
            HTTPGameService(
                "http://first.test",
                transport=ASGITransport(app=app),
            ) as first,
            HTTPGameService(
                "http://second.test",
                transport=ASGITransport(app=app),
            ) as second,
        ):
            result = await Arena(rng=random.Random(0)).play_match(
                Player("first", first),
                Player("second", second),
            )

        assert result.winner in {"first", "second"}
        assert result.loser in {"first", "second"}
        assert result.winner != result.loser
        assert result.reason == "fleet_destroyed"

    asyncio.run(exercise())
