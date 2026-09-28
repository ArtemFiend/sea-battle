import random

import pytest

from sea_battle.domain.strategy import (
    NoAvailableShotsError,
    choose_shot,
    update_targeting,
)


def test_choose_shot_never_repeats_coordinates() -> None:
    rng = random.Random(42)
    fired: list[str] = []

    for _ in range(100):
        coordinate, _ = choose_shot(fired, [], rng)
        assert coordinate not in fired
        fired.append(coordinate)

    with pytest.raises(NoAvailableShotsError):
        choose_shot(fired, [], rng)


def test_choose_shot_prioritises_target_queue() -> None:
    coordinate, remaining = choose_shot(["A1"], ["A1", "B1", "B1", "A2"])

    assert coordinate == "B1"
    assert remaining == ["A2"]


def test_hit_targets_neighbouring_cells() -> None:
    hits, queue = update_targeting("E5", "hit", [], [], ["E5"])

    assert hits == ["E5"]
    assert set(queue) == {"D5", "F5", "E4", "E6"}


def test_second_hit_continues_along_ship_line() -> None:
    hits, queue = update_targeting(
        "E6",
        "hit",
        ["E5"],
        ["D5", "F5", "E4"],
        ["E5", "E6"],
    )

    assert hits == ["E5", "E6"]
    assert queue == ["E4", "E7"]


def test_miss_preserves_remaining_targets() -> None:
    hits, queue = update_targeting(
        "D5",
        "miss",
        ["E5"],
        ["F5", "E4", "E6"],
        ["E5", "D5"],
    )

    assert hits == ["E5"]
    assert queue == ["F5", "E4", "E6"]


def test_killed_clears_targeting_state() -> None:
    hits, queue = update_targeting(
        "E6",
        "killed",
        ["E5"],
        ["E4", "E7"],
        ["E5", "E6"],
    )

    assert hits == []
    assert queue == []
