import asyncio
import random
import uuid

from sea_battle.arena import Arena, Player, Tournament
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


class DishonestService(HonestService):
    async def process_opponent_shot(
        self,
        session_id: uuid.UUID,
        coordinate: str,
    ) -> ShotResult:
        return "miss"


class SlowService(HonestService):
    async def make_shot(self, session_id: uuid.UUID) -> str:
        await asyncio.sleep(0.05)
        return await super().make_shot(session_id)


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


def test_repeated_shot_is_allowed_but_passes_turn() -> None:
    fleet = generate_fleet(random.Random(5))
    target = fleet[0][0]
    first_service = HonestService(fleet, [target])
    second_service = HonestService(fleet, _cells(fleet))

    result = asyncio.run(
        Arena().play_match(
            Player("first", first_service),
            Player("second", second_service),
            starting_player=0,
        )
    )

    assert result.winner == "second"
    assert first_service.make_shot_calls == 2


def test_invalid_fleet_gives_victory_to_opponent() -> None:
    valid_fleet = generate_fleet(random.Random(6))
    invalid_service = HonestService(valid_fleet[:-1], ["A1"])
    valid_service = HonestService(valid_fleet, _cells(valid_fleet))

    result = asyncio.run(
        Arena().play_match(
            Player("invalid", invalid_service),
            Player("valid", valid_service),
        )
    )

    assert result.winner == "valid"
    assert result.reason == "invalid_fleet"
    assert len(invalid_service.closed_sessions) == 1


def test_dishonest_result_gives_victory_to_opponent() -> None:
    first_fleet = generate_fleet(random.Random(7))
    second_fleet = generate_fleet(random.Random(8))
    honest_service = HonestService(first_fleet, [_cells(second_fleet)[0]])
    dishonest_service = DishonestService(second_fleet, ["A1"])

    result = asyncio.run(
        Arena().play_match(
            Player("honest", honest_service),
            Player("dishonest", dishonest_service),
            starting_player=0,
        )
    )

    assert result.winner == "honest"
    assert result.reason == "dishonest"


def test_timeout_gives_victory_to_opponent() -> None:
    fleet = generate_fleet(random.Random(9))
    slow_service = SlowService(fleet, _cells(fleet))
    responsive_service = HonestService(fleet, _cells(fleet))

    result = asyncio.run(
        Arena(timeout=0.01).play_match(
            Player("slow", slow_service),
            Player("responsive", responsive_service),
            starting_player=0,
        )
    )

    assert result.winner == "responsive"
    assert result.reason == "timeout"


def test_round_robin_plays_each_pair_once() -> None:
    fleet = generate_fleet(random.Random(10))
    players = [
        Player(name, HonestService(fleet, _cells(fleet)))
        for name in ("alpha", "bravo", "charlie")
    ]

    result = asyncio.run(Tournament(Arena()).run(players))

    assert len(result.matches) == 3
    assert {
        frozenset((match.first_player, match.second_player))
        for match in result.matches
    } == {
        frozenset(("alpha", "bravo")),
        frozenset(("alpha", "charlie")),
        frozenset(("bravo", "charlie")),
    }
    assert all(standing.played == 2 for standing in result.standings)
    assert sum(standing.wins for standing in result.standings) == 3
    assert sum(standing.points for standing in result.standings) == 3
