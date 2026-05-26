"""Tests for mahjong_engine.rng."""

from mahjong_engine.rng import shuffled


def test_m1_guide_demo_rng() -> None:
    assert shuffled([1, 2, 3, 4, 5], seed=42) == [4, 2, 3, 5, 1]
    assert shuffled([1, 2, 3, 4, 5], seed=42) == [4, 2, 3, 5, 1]
    assert shuffled([1, 2, 3, 4, 5], seed=43) == [2, 5, 4, 3, 1]
