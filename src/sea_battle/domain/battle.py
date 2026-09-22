from collections.abc import Collection, Sequence
from typing import Literal

from sea_battle.domain.fleet import Coordinate, parse_coordinate

ShotResult = Literal["miss", "hit", "killed"]


def resolve_opponent_shot(
    fleet: Sequence[Sequence[Coordinate]],
    previous_shots: Collection[Coordinate],
    coordinate: Coordinate,
) -> ShotResult:
    """Return the honest result of a shot against a fleet.

    A repeated shot is accepted, but it cannot sink the same ship twice.
    """

    parse_coordinate(coordinate)
    target_ship = next(
        (ship for ship in fleet if coordinate in ship),
        None,
    )
    if target_ship is None:
        return "miss"

    previous_hits = set(previous_shots)
    ship_cells = set(target_ship)
    if ship_cells <= previous_hits:
        return "hit"

    if ship_cells <= previous_hits | {coordinate}:
        return "killed"

    return "hit"
