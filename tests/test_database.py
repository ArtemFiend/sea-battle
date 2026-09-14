import asyncio
import uuid

from sea_battle.db.models import GameSession
from sea_battle.db.session import async_session_factory


def test_game_session_is_saved_in_database() -> None:
    asyncio.run(_test_game_session_is_saved_in_database())


async def _test_game_session_is_saved_in_database() -> None:
    game_id = uuid.uuid4()

    try:
        async with async_session_factory() as session:
            session.add(GameSession(id=game_id, status="active"))
            await session.commit()

        async with async_session_factory() as session:
            saved_game = await session.get(GameSession, game_id)

            assert saved_game is not None
            assert saved_game.id == game_id
            assert saved_game.status == "active"
            assert saved_game.created_at is not None
            assert saved_game.finished_at is None
    finally:
        async with async_session_factory() as session:
            saved_game = await session.get(GameSession, game_id)
            if saved_game is not None:
                await session.delete(saved_game)
                await session.commit()
