import asyncio
import random
import uuid

from sea_battle.arena import Arena, Player
from sea_battle.arena.service import StartedGame
from sea_battle.domain.battle import ShotResult, resolve_opponent_shot
from sea_battle.domain.fleet import Fleet, generate_fleet


class HonestService:
    def __init__(
        self,
        fleet: Fleet,
        shots: list[str],
    ) -> None:
        self.fleet = fleet
        self.shots = shots
        self.sessions: dict[uuid.UUID, dict[str, object]] = {}
        self.closed_sessions: set[uuid.UUID] = set()
        self.make_shot_calls = 0

    async def start_game(self) -> StartedGame:
        session_id = uuid.uuid4()
        self.sessions[session_id] = {
            "received": [],
            "shot_index": 0,
            "results": [],
        }
        return StartedGame(session_id, self.fleet)

    async def make_shot(self, session_id: uuid.UUID) -> str:
        session = self.sessions[session_id]
        index = session["shot_index"]
        assert isinstance(index, int)
        coordinate = self.shots[index % len(self.shots)]
        session["shot_index"] = index + 1
        self.make_shot_calls += 1
        return coordinate

    async def accept_shot_result(
        self,
        session_id: uuid.UUID,
        result: ShotResult,
    ) -> None:
        results = self.sessions[session_id]["results"]
        assert isinstance(results, list)
        results.append(result)

    async def process_opponent_shot(
        self,
        session_id: uuid.UUID,
        coordinate: str,
    ) -> ShotResult:
        received = self.sessions[session_id]["received"]
        assert isinstance(received, list)
        result = resolve_opponent_shot(self.fleet, received, coordinate)
        if coordinate not in received:
            received.append(coordinate)
        return result

    async def close_game(self, session_id: uuid.UUID) -> None:
        self.closed_sessions.add(session_id)


def _cells(fleet: Fleet) -> list[str]:
    return [coordinate for ship in fleet for coordinate in ship]


def _all_board_coordinates() -> list[str]:
    return [
        f"{column}{row}"
        for column in "ABCDEFGHIJ"
        for row in range(1, 11)
    ]


def test_arena_plays_full_match_and_closes_both_sessions() -> None:
    first_fleet = generate_fleet(random.Random(1))
    second_fleet = generate_fleet(random.Random(2))
    first_service = HonestService(first_fleet, _cells(second_fleet))
    second_service = HonestService(second_fleet, _all_board_coordinates())
    arena = Arena()

    result = asyncio.run(
        arena.play_match(
            Player("first", first_service),
            Player("second", second_service),
            starting_player=0,
        )
    )

    assert result.winner == "first"
    assert result.loser == "second"
    assert result.reason == "fleet_destroyed"
    assert result.turns == 20
    assert len(first_service.closed_sessions) == 1
    assert len(second_service.closed_sessions) == 1


def test_miss_passes_turn_to_other_player() -> None:
    first_fleet = generate_fleet(random.Random(3))
    second_fleet = generate_fleet(random.Random(4))
    occupied_by_second = set(_cells(second_fleet))
    first_miss = next(
        coordinate
        for coordinate in _all_board_coordinates()
        if coordinate not in occupied_by_second
    )
    first_service = HonestService(first_fleet, [first_miss])
    second_service = HonestService(second_fleet, _cells(first_fleet))
    arena = Arena()

    result = asyncio.run(
        arena.play_match(
            Player("first", first_service),
            Player("second", second_service),
            starting_player=0,
        )
    )

    assert result.winner == "second"
    assert first_service.make_shot_calls == 1
    assert second_service.make_shot_calls == 20
