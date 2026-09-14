import random
import re
from collections.abc import Sequence


BOARD_SIZE = 10
FLEET_SHIP_LENGTHS = (4, 3, 3, 2, 2, 2, 1, 1, 1, 1)

Coordinate = str
Ship = tuple[Coordinate, ...]
Fleet = tuple[Ship, ...]
Cell = tuple[int, int]

_COORDINATE_PATTERN = re.compile(r"^[A-J](10|[1-9])$")


class FleetValidationError(ValueError):
    """Raised when a fleet violates the game rules."""


def _parse_coordinate(coordinate: str) -> Cell:
    if not isinstance(coordinate, str) or not _COORDINATE_PATTERN.fullmatch(
        coordinate
    ):
        raise FleetValidationError(f"Invalid coordinate: {coordinate!r}")

    column = ord(coordinate[0]) - ord("A") + 1
    row = int(coordinate[1:])
    return column, row


def _format_coordinate(cell: Cell) -> Coordinate:
    column, row = cell
    return f"{chr(ord('A') + column - 1)}{row}"


def _validate_ship_geometry(cells: tuple[Cell, ...]) -> None:
    if len(set(cells)) != len(cells):
        raise FleetValidationError("A ship contains duplicate cells")

    columns = {column for column, _ in cells}
    rows = {row for _, row in cells}

    if len(columns) != 1 and len(rows) != 1:
        raise FleetValidationError("A ship must be horizontal or vertical")

    varying_axis = (
        sorted(row for _, row in cells)
        if len(columns) == 1
        else sorted(column for column, _ in cells)
    )
    expected_axis = list(
        range(varying_axis[0], varying_axis[0] + len(varying_axis))
    )
    if varying_axis != expected_axis:
        raise FleetValidationError("A ship must not contain gaps")


def validate_fleet(fleet: Sequence[Sequence[Coordinate]]) -> None:
    """Validate fleet composition and geometry."""

    if len(fleet) != len(FLEET_SHIP_LENGTHS):
        raise FleetValidationError("A fleet must contain exactly 10 ships")

    actual_lengths = sorted((len(ship) for ship in fleet), reverse=True)
    if actual_lengths != list(FLEET_SHIP_LENGTHS):
        raise FleetValidationError(
            "A fleet must contain ships with lengths 4, 3, 3, 2, 2, 2, "
            "1, 1, 1, 1"
        )

    parsed_ships: list[tuple[Cell, ...]] = []
    for ship in fleet:
        cells = tuple(_parse_coordinate(coordinate) for coordinate in ship)
        _validate_ship_geometry(cells)
        parsed_ships.append(cells)

    occupied_by_ship: dict[Cell, int] = {}
    for ship_index, cells in enumerate(parsed_ships):
        for cell in cells:
            if cell in occupied_by_ship:
                raise FleetValidationError("Ships must not overlap")
            occupied_by_ship[cell] = ship_index

    for (column, row), ship_index in occupied_by_ship.items():
        for column_offset in (-1, 0, 1):
            for row_offset in (-1, 0, 1):
                neighbour = column + column_offset, row + row_offset
                neighbour_ship = occupied_by_ship.get(neighbour)
                if neighbour_ship is not None and neighbour_ship != ship_index:
                    raise FleetValidationError(
                        "Ships must not touch, including diagonally"
                    )


def _all_placements(length: int) -> list[tuple[Cell, ...]]:
    placements: list[tuple[Cell, ...]] = []

    for row in range(1, BOARD_SIZE + 1):
        for start_column in range(1, BOARD_SIZE - length + 2):
            placements.append(
                tuple((start_column + offset, row) for offset in range(length))
            )

    if length > 1:
        for column in range(1, BOARD_SIZE + 1):
            for start_row in range(1, BOARD_SIZE - length + 2):
                placements.append(
                    tuple((column, start_row + offset) for offset in range(length))
                )

    return placements


def _blocked_cells(ship: tuple[Cell, ...]) -> set[Cell]:
    blocked: set[Cell] = set()
    for column, row in ship:
        for column_offset in (-1, 0, 1):
            for row_offset in (-1, 0, 1):
                neighbour = column + column_offset, row + row_offset
                if (
                    1 <= neighbour[0] <= BOARD_SIZE
                    and 1 <= neighbour[1] <= BOARD_SIZE
                ):
                    blocked.add(neighbour)
    return blocked


def generate_fleet(rng: random.Random | None = None) -> Fleet:
    """Generate a random valid fleet.

    Supplying an RNG makes generation deterministic for tests.
    """

    random_source = rng or random.Random()
    placements_by_length = {
        length: _all_placements(length) for length in set(FLEET_SHIP_LENGTHS)
    }

    def place_ship(
        ship_index: int,
        blocked: set[Cell],
        placed: list[tuple[Cell, ...]],
    ) -> list[tuple[Cell, ...]] | None:
        if ship_index == len(FLEET_SHIP_LENGTHS):
            return placed

        length = FLEET_SHIP_LENGTHS[ship_index]
        candidates = placements_by_length[length].copy()
        random_source.shuffle(candidates)

        for candidate in candidates:
            if any(cell in blocked for cell in candidate):
                continue

            result = place_ship(
                ship_index + 1,
                blocked | _blocked_cells(candidate),
                [*placed, candidate],
            )
            if result is not None:
                return result

        return None

    placed_fleet = place_ship(0, set(), [])
    if placed_fleet is None:
        raise RuntimeError("Unable to generate a valid fleet")

    fleet = tuple(
        tuple(_format_coordinate(cell) for cell in ship)
        for ship in placed_fleet
    )
    validate_fleet(fleet)
    return fleet
