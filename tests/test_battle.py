import pytest

from sea_battle.domain.battle import resolve_opponent_shot
from sea_battle.domain.fleet import FleetValidationError


FLEET = (("A1", "A2", "A3"), ("C1",))


def test_shot_outside_fleet_is_miss() -> None:
    assert resolve_opponent_shot(FLEET, [], "J10") == "miss"


def test_first_ship_hit_is_hit() -> None:
    assert resolve_opponent_shot(FLEET, [], "A1") == "hit"


def test_last_unhit_ship_cell_is_killed() -> None:
    assert resolve_opponent_shot(FLEET, ["A1", "A2"], "A3") == "killed"


def test_single_cell_ship_is_killed_by_first_hit() -> None:
    assert resolve_opponent_shot(FLEET, [], "C1") == "killed"


def test_repeated_shot_does_not_kill_ship_twice() -> None:
    assert (
        resolve_opponent_shot(FLEET, ["A1", "A2", "A3"], "A3")
        == "hit"
    )


def test_invalid_coordinate_is_rejected() -> None:
    with pytest.raises(FleetValidationError, match="Invalid coordinate"):
        resolve_opponent_shot(FLEET, [], "K1")
