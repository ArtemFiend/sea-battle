from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations

from sea_battle.arena.match import Arena, MatchResult, Player


@dataclass(frozen=True)
class Standing:
    player: str
    played: int
    wins: int
    losses: int
    draws: int
    points: int


@dataclass(frozen=True)
class TournamentResult:
    matches: tuple[MatchResult, ...]
    standings: tuple[Standing, ...]


class Tournament:
    """Run one match for every unordered pair of players."""

    def __init__(self, arena: Arena, *, points_per_win: int = 1) -> None:
        if points_per_win < 1:
            raise ValueError("points_per_win must be positive")
        self._arena = arena
        self._points_per_win = points_per_win

    async def run(self, players: Sequence[Player]) -> TournamentResult:
        if len(players) < 2:
            raise ValueError("A tournament needs at least two players")

        names = [player.name for player in players]
        if len(set(names)) != len(names):
            raise ValueError("Player names must be unique")

        matches = [
            await self._arena.play_match(first, second)
            for first, second in combinations(players, 2)
        ]
        return TournamentResult(
            matches=tuple(matches),
            standings=self._build_standings(names, matches),
        )

    def _build_standings(
        self,
        names: Sequence[str],
        matches: Sequence[MatchResult],
    ) -> tuple[Standing, ...]:
        stats = {
            name: {"played": 0, "wins": 0, "losses": 0, "draws": 0}
            for name in names
        }
        for match in matches:
            stats[match.first_player]["played"] += 1
            stats[match.second_player]["played"] += 1
            if match.winner is None:
                stats[match.first_player]["draws"] += 1
                stats[match.second_player]["draws"] += 1
                continue
            stats[match.winner]["wins"] += 1
            assert match.loser is not None
            stats[match.loser]["losses"] += 1

        standings = tuple(
            Standing(
                player=name,
                played=values["played"],
                wins=values["wins"],
                losses=values["losses"],
                draws=values["draws"],
                points=values["wins"] * self._points_per_win,
            )
            for name, values in stats.items()
        )
        return tuple(
            sorted(
                standings,
                key=lambda item: (-item.points, -item.wins, item.player),
            )
        )


def format_tournament_result(result: TournamentResult) -> str:
    lines = ["Matches:"]
    for match in result.matches:
        outcome = match.winner or "draw"
        lines.append(
            f"- {match.first_player} vs {match.second_player}: "
            f"{outcome} ({match.reason}, {match.turns} turns)"
        )

    lines.extend(
        [
            "",
            "Standings:",
            "#  Player                 P  W  L  D  Pts",
        ]
    )
    for position, standing in enumerate(result.standings, start=1):
        lines.append(
            f"{position:<2} {standing.player:<22} "
            f"{standing.played:<2} {standing.wins:<2} "
            f"{standing.losses:<2} {standing.draws:<2} "
            f"{standing.points}"
        )
    return "\n".join(lines)
