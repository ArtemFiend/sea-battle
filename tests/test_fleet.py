import random

import pytest

from sea_battle.domain.fleet import (
    FLEET_SHIP_LENGTHS,
    Fleet,
    FleetValidationError,
    generate_fleet,
    validate_fleet,
)


VALID_FLEET: Fleet = (
    ("A1", "B1", "C1", "D1"),
    ("F1", "F2", "F3"),
    ("H1", "H2", "H3"),
    ("A4", "B4"),
    ("D5", "D6"),
    ("G5", "H5"),
    ("J1",),
    ("J4",),
    ("B8",),
    ("F9",),
)


def replace_ship(fleet: Fleet, index: int, ship: tuple[str, ...]) -> Fleet:
    ships = list(fleet)
    ships[index] = ship
    return tuple(ships)


def test_valid_fleet_is_accepted() -> None:
    validate_fleet(VALID_FLEET)


def test_generated_fleet_has_required_composition() -> None:
    fleet = generate_fleet(random.Random(42))

    assert tuple(sorted(map(len, fleet), reverse=True)) == FLEET_SHIP_LENGTHS
    assert sum(map(len, fleet)) == 20
    validate_fleet(fleet)


@pytest.mark.parametrize("seed", range(20))
def test_generated_fleets_are_valid(seed: int) -> None:
    validate_fleet(generate_fleet(random.Random(seed)))


def test_wrong_fleet_composition_is_rejected() -> None:
    with pytest.raises(FleetValidationError, match="exactly 10 ships"):
        validate_fleet(VALID_FLEET[:-1])


def test_wrong_ship_lengths_are_rejected() -> None:
    fleet = replace_ship(VALID_FLEET, 7, ("J4", "J5"))

    with pytest.raises(FleetValidationError, match="ships with lengths"):
        validate_fleet(fleet)


def test_bent_ship_is_rejected() -> None:
    fleet = replace_ship(VALID_FLEET, 0, ("A1", "B1", "C1", "C2"))

    with pytest.raises(FleetValidationError, match="horizontal or vertical"):
        validate_fleet(fleet)


def test_ship_with_gap_is_rejected() -> None:
    fleet = replace_ship(VALID_FLEET, 0, ("A1", "B1", "C1", "E1"))

    with pytest.raises(FleetValidationError, match="must not contain gaps"):
        validate_fleet(fleet)


def test_ships_touching_by_side_are_rejected() -> None:
    fleet = replace_ship(VALID_FLEET, 7, ("I5",))

    with pytest.raises(FleetValidationError, match="must not touch"):
        validate_fleet(fleet)


def test_ships_touching_by_corner_are_rejected() -> None:
    fleet = replace_ship(VALID_FLEET, 7, ("I4",))

    with pytest.raises(FleetValidationError, match="must not touch"):
        validate_fleet(fleet)


@pytest.mark.parametrize("coordinate", ["A0", "A11", "K1", "a1", "A01"])
def test_out_of_bounds_or_malformed_coordinate_is_rejected(
    coordinate: str,
) -> None:
    fleet = replace_ship(VALID_FLEET, 7, (coordinate,))

    with pytest.raises(FleetValidationError, match="Invalid coordinate"):
        validate_fleet(fleet)


def test_overlapping_ships_are_rejected() -> None:
    fleet = replace_ship(VALID_FLEET, 7, ("J1",))

    with pytest.raises(FleetValidationError, match="must not overlap"):
        validate_fleet(fleet)


def test_duplicate_cells_inside_ship_are_rejected() -> None:
    fleet = replace_ship(VALID_FLEET, 0, ("A1", "B1", "C1", "C1"))

    with pytest.raises(FleetValidationError, match="duplicate cells"):
        validate_fleet(fleet)
