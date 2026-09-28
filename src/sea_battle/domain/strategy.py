import random
from collections.abc import Collection, Sequence

from sea_battle.domain.battle import ShotResult
from sea_battle.domain.fleet import (
    BOARD_SIZE,
    Cell,
    Coordinate,
    format_coordinate,
    parse_coordinate,
)


class NoAvailableShotsError(RuntimeError):
    """Raised when every board coordinate has already been fired at."""


def _on_board(cell: Cell) -> bool:
    column, row = cell
    return 1 <= column <= BOARD_SIZE and 1 <= row <= BOARD_SIZE


def _coordinates(cells: Sequence[Cell]) -> list[Coordinate]:
    return [format_coordinate(cell) for cell in cells if _on_board(cell)]


def choose_shot(
    previous_shots: Collection[Coordinate],
    target_queue: Sequence[Coordinate],
    rng: random.Random | None = None,
) -> tuple[Coordinate, list[Coordinate]]:
    """Choose an untried coordinate, prioritising cells around a hit."""

    fired = set(previous_shots)
    remaining_targets: list[Coordinate] = []
    for coordinate in target_queue:
        parse_coordinate(coordinate)
        if coordinate not in fired and coordinate not in remaining_targets:
            remaining_targets.append(coordinate)

    if remaining_targets:
        return remaining_targets[0], remaining_targets[1:]

    available = [
        format_coordinate((column, row))
        for column in range(1, BOARD_SIZE + 1)
        for row in range(1, BOARD_SIZE + 1)
        if format_coordinate((column, row)) not in fired
    ]
    if not available:
        raise NoAvailableShotsError("No coordinates available for a shot")

    random_source = rng or random.Random()
    return random_source.choice(available), []


def update_targeting(
    coordinate: Coordinate,
    result: ShotResult,
    target_hits: Sequence[Coordinate],
    target_queue: Sequence[Coordinate],
    fired_shots: Collection[Coordinate],
) -> tuple[list[Coordinate], list[Coordinate]]:
    """Update pursuit state after receiving the result of a shot."""

    parse_coordinate(coordinate)
    if result == "miss":
        return list(target_hits), list(target_queue)
    if result == "killed":
        return [], []

    hits = list(dict.fromkeys([*target_hits, coordinate]))
    hit_cells = [parse_coordinate(hit) for hit in hits]

    if len(hit_cells) == 1:
        column, row = hit_cells[0]
        candidate_cells = [
            (column - 1, row),
            (column + 1, row),
            (column, row - 1),
            (column, row + 1),
        ]
    elif len({column for column, _ in hit_cells}) == 1:
        column = hit_cells[0][0]
        rows = [row for _, row in hit_cells]
        candidate_cells = [(column, min(rows) - 1), (column, max(rows) + 1)]
    elif len({row for _, row in hit_cells}) == 1:
        row = hit_cells[0][1]
        columns = [column for column, _ in hit_cells]
        candidate_cells = [(min(columns) - 1, row), (max(columns) + 1, row)]
    else:
        column, row = parse_coordinate(coordinate)
        candidate_cells = [
            (column - 1, row),
            (column + 1, row),
            (column, row - 1),
            (column, row + 1),
        ]

    fired = set(fired_shots)
    queue = [
        candidate
        for candidate in _coordinates(candidate_cells)
        if candidate not in fired
    ]
    return hits, queue
