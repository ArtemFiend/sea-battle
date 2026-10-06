import asyncio
import random
import uuid
from dataclasses import dataclass, field
from typing import Awaitable, TypeVar

from sea_battle.arena.service import (
    GameService,
    ServiceProtocolError,
    StartedGame,
)
from sea_battle.domain.battle import resolve_opponent_shot
from sea_battle.domain.fleet import (
    Fleet,
    FleetValidationError,
    parse_coordinate,
    validate_fleet,
)

T = TypeVar("T")


@dataclass(frozen=True)
class Player:
    name: str
    service: GameService


@dataclass(frozen=True)
class MatchResult:
    first_player: str
    second_player: str
    winner: str | None
    loser: str | None
    reason: str
    turns: int
    detail: str | None = None


@dataclass
class _GameState:
    session_id: uuid.UUID
    fleet: Fleet
    received_shots: set[str] = field(default_factory=set)
    outgoing_shots: set[str] = field(default_factory=set)


class _PlayerFault(RuntimeError):
    def __init__(
        self,
        player_index: int,
        reason: str,
        detail: str,
        *,
        state: _GameState | None = None,
    ) -> None:
        super().__init__(detail)
        self.player_index = player_index
        self.reason = reason
        self.detail = detail
        self.state = state


class Arena:
    def __init__(
        self,
        *,
        timeout: float = 1.0,
        max_turns: int = 1000,
        rng: random.Random | None = None,
    ) -> None:
        self.timeout = timeout
        self.max_turns = max_turns
        self._rng = rng or random.Random()

    async def play_match(
        self,
        first: Player,
        second: Player,
        *,
        starting_player: int | None = None,
    ) -> MatchResult:
        players = (first, second)
        states: list[_GameState | None] = [None, None]
        turns = 0

        start_results = await asyncio.gather(
            self._start_player(0, first),
            self._start_player(1, second),
            return_exceptions=True,
        )
        faults: list[_PlayerFault] = []
        for index, result in enumerate(start_results):
            if isinstance(result, _PlayerFault):
                faults.append(result)
                states[index] = result.state
            else:
                states[index] = result

        try:
            if faults:
                if len(faults) == 2:
                    return MatchResult(
                        first.name,
                        second.name,
                        None,
                        None,
                        "both_failed",
                        turns,
                        "; ".join(fault.detail for fault in faults),
                    )
                return self._fault_result(players, faults[0], turns)

            active_index = (
                starting_player
                if starting_player is not None
                else self._rng.randrange(2)
            )
            if active_index not in {0, 1}:
                raise ValueError("starting_player must be 0 or 1")

            for turns in range(1, self.max_turns + 1):
                defending_index = 1 - active_index
                attacker_state = states[active_index]
                defender_state = states[defending_index]
                assert attacker_state is not None
                assert defender_state is not None

                try:
                    coordinate = await self._call(
                        active_index,
                        players[active_index].service.make_shot(
                            attacker_state.session_id
                        ),
                    )
                    try:
                        parse_coordinate(coordinate)
                    except FleetValidationError as error:
                        raise _PlayerFault(
                            active_index,
                            "invalid_shot",
                            str(error),
                        ) from error

                    repeated = coordinate in attacker_state.outgoing_shots
                    expected_result = resolve_opponent_shot(
                        defender_state.fleet,
                        defender_state.received_shots,
                        coordinate,
                    )
                    actual_result = await self._call(
                        defending_index,
                        players[defending_index].service.process_opponent_shot(
                            defender_state.session_id,
                            coordinate,
                        ),
                    )
                    if actual_result != expected_result:
                        raise _PlayerFault(
                            defending_index,
                            "dishonest",
                            f"{coordinate}: expected {expected_result}, "
                            f"got {actual_result}",
                        )

                    await self._call(
                        active_index,
                        players[active_index].service.accept_shot_result(
                            attacker_state.session_id,
                            actual_result,
                        ),
                    )
                except _PlayerFault as fault:
                    return self._fault_result(players, fault, turns)

                attacker_state.outgoing_shots.add(coordinate)
                defender_state.received_shots.add(coordinate)
                occupied = {
                    cell
                    for ship in defender_state.fleet
                    for cell in ship
                }
                if occupied <= defender_state.received_shots:
                    return MatchResult(
                        first.name,
                        second.name,
                        players[active_index].name,
                        players[defending_index].name,
                        "fleet_destroyed",
                        turns,
                    )

                if repeated or actual_result == "miss":
                    active_index = defending_index

            return MatchResult(
                first.name,
                second.name,
                None,
                None,
                "turn_limit",
                turns,
                f"Match exceeded {self.max_turns} turns",
            )
        finally:
            await asyncio.gather(
                *(
                    self._safe_close(players[index], state)
                    for index, state in enumerate(states)
                    if state is not None
                )
            )

    async def _start_player(
        self,
        player_index: int,
        player: Player,
    ) -> _GameState:
        started: StartedGame = await self._call(
            player_index,
            player.service.start_game(),
        )
        state = _GameState(started.session_id, started.fleet)
        try:
            validate_fleet(started.fleet)
        except FleetValidationError as error:
            raise _PlayerFault(
                player_index,
                "invalid_fleet",
                str(error),
                state=state,
            ) from error
        return state

    async def _call(
        self,
        player_index: int,
        operation: Awaitable[T],
    ) -> T:
        try:
            return await asyncio.wait_for(operation, timeout=self.timeout)
        except TimeoutError as error:
            raise _PlayerFault(
                player_index,
                "timeout",
                f"Service did not respond within {self.timeout} seconds",
            ) from error
        except ServiceProtocolError as error:
            raise _PlayerFault(
                player_index,
                "invalid_response",
                str(error),
            ) from error
        except _PlayerFault:
            raise
        except Exception as error:
            raise _PlayerFault(
                player_index,
                "service_error",
                str(error),
            ) from error

    async def _safe_close(
        self,
        player: Player,
        state: _GameState,
    ) -> None:
        try:
            await asyncio.wait_for(
                player.service.close_game(state.session_id),
                timeout=self.timeout,
            )
        except Exception:
            return

    @staticmethod
    def _fault_result(
        players: tuple[Player, Player],
        fault: _PlayerFault,
        turns: int,
    ) -> MatchResult:
        winner_index = 1 - fault.player_index
        return MatchResult(
            players[0].name,
            players[1].name,
            players[winner_index].name,
            players[fault.player_index].name,
            fault.reason,
            turns,
            fault.detail,
        )
