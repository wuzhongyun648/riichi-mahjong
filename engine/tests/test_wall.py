"""Tests for mahjong_engine.wall.

Covers: tile count, aka injection, dead wall, dora indicators, seed
reproducibility, and live_remaining arithmetic.

Hypothesis property: any seed produces a valid wall with correct invariants.
"""

from collections import Counter

import hypothesis.strategies as st
import pytest
from hypothesis import given, settings

from mahjong_engine.tiles import (
    AKA_5M_BASE,
    AKA_5P_BASE,
    AKA_5S_BASE,
    TILE_COUNT,
    next_dora,
)
from mahjong_engine.wall import (
    DEAD_WALL_SIZE,
    INITIAL_DORA_REVEALED,
    MAX_KAN,
    TOTAL_TILES,
    WallState,
    WallTile,
    build_wall,
)

# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------


class TestBuildWall:
    def setup_method(self) -> None:
        self.wall = build_wall(seed=42)

    def test_total_tile_count(self) -> None:
        assert len(self.wall.tiles) == TOTAL_TILES

    def test_each_tile_appears_four_times(self) -> None:
        counts = Counter(wt.code for wt in self.wall.tiles)
        for code in range(TILE_COUNT):
            assert counts[code] == 4, f"Tile {code} appears {counts[code]} times"

    def test_exactly_three_aka_tiles(self) -> None:
        aka_tiles = [wt for wt in self.wall.tiles if wt.is_aka]
        assert len(aka_tiles) == 3

    def test_aka_tiles_are_fives(self) -> None:
        aka_codes = {wt.code for wt in self.wall.tiles if wt.is_aka}
        assert aka_codes == {AKA_5M_BASE, AKA_5P_BASE, AKA_5S_BASE}

    def test_one_aka_per_five_type(self) -> None:
        for five_code in (AKA_5M_BASE, AKA_5P_BASE, AKA_5S_BASE):
            aka_count = sum(1 for wt in self.wall.tiles if wt.code == five_code and wt.is_aka)
            assert aka_count == 1, f"Expected 1 aka for code {five_code}"

    def test_initial_live_pos_zero(self) -> None:
        assert self.wall.live_pos == 0

    def test_initial_rinshan_drawn_zero(self) -> None:
        assert self.wall.rinshan_drawn == 0

    def test_initial_dora_revealed(self) -> None:
        assert self.wall.dora_revealed == INITIAL_DORA_REVEALED


class TestWallDeadWall:
    def setup_method(self) -> None:
        self.wall = build_wall(seed=1)

    def test_dead_wall_size(self) -> None:
        assert len(self.wall.dead_wall) == DEAD_WALL_SIZE

    def test_live_remaining_at_start(self) -> None:
        # 136 - 14 = 122
        assert self.wall.live_remaining == TOTAL_TILES - DEAD_WALL_SIZE

    def test_dora_indicators_count(self) -> None:
        assert len(self.wall.dora_indicators) == INITIAL_DORA_REVEALED

    def test_ura_indicators_count(self) -> None:
        assert len(self.wall.ura_indicators) == INITIAL_DORA_REVEALED

    def test_active_dora_tiles_count(self) -> None:
        assert len(self.wall.active_dora_tiles) == INITIAL_DORA_REVEALED

    def test_active_dora_is_next_of_indicator(self) -> None:
        for indicator_tile, dora_tile in zip(
            self.wall.dora_indicators, self.wall.active_dora_tiles, strict=True
        ):
            assert dora_tile == next_dora(indicator_tile.code)


class TestWallPeek:
    def setup_method(self) -> None:
        self.wall = build_wall(seed=7)

    def test_peek_live_returns_first_tile(self) -> None:
        wt = self.wall.peek_live()
        assert isinstance(wt, WallTile)
        assert 0 <= wt.code <= 33

    def test_peek_rinshan_returns_tile(self) -> None:
        wt = self.wall.peek_rinshan()
        assert isinstance(wt, WallTile)
        assert 0 <= wt.code <= 33

    def test_peek_live_exhausted_raises(self) -> None:
        # Manually set live_pos past the live wall
        wall = WallState(
            tiles=self.wall.tiles,
            live_pos=TOTAL_TILES - DEAD_WALL_SIZE,  # all live tiles consumed
            rinshan_drawn=0,
            dora_revealed=1,
        )
        with pytest.raises(IndexError):
            wall.peek_live()

    def test_peek_rinshan_exhausted_raises(self) -> None:
        wall = WallState(
            tiles=self.wall.tiles,
            live_pos=0,
            rinshan_drawn=MAX_KAN,
            dora_revealed=1,
        )
        with pytest.raises(IndexError):
            wall.peek_rinshan()


# ---------------------------------------------------------------------------
# Seed reproducibility
# ---------------------------------------------------------------------------


class TestSeedReproducibility:
    def test_same_seed_same_wall(self) -> None:
        w1 = build_wall(seed=99)
        w2 = build_wall(seed=99)
        assert w1.tiles == w2.tiles

    def test_different_seeds_different_walls(self) -> None:
        w1 = build_wall(seed=1)
        w2 = build_wall(seed=2)
        # Extremely unlikely to be identical after shuffle
        assert w1.tiles != w2.tiles

    def test_none_seed_produces_valid_wall(self) -> None:
        w = build_wall(seed=None)
        assert len(w.tiles) == TOTAL_TILES


# ---------------------------------------------------------------------------
# Unsupported mode
# ---------------------------------------------------------------------------


def test_unsupported_mode_raises() -> None:
    with pytest.raises(NotImplementedError):
        build_wall(mode="sanma")


# ---------------------------------------------------------------------------
# WallState validation
# ---------------------------------------------------------------------------


class TestWallStateValidation:
    def test_wrong_tile_count_raises(self) -> None:
        good_wall = build_wall(seed=0)
        with pytest.raises(ValueError):
            WallState(tiles=good_wall.tiles[:100], live_pos=0, rinshan_drawn=0, dora_revealed=1)

    def test_bad_rinshan_drawn_raises(self) -> None:
        good_wall = build_wall(seed=0)
        with pytest.raises(ValueError):
            WallState(tiles=good_wall.tiles, live_pos=0, rinshan_drawn=5, dora_revealed=1)

    def test_bad_dora_revealed_raises(self) -> None:
        good_wall = build_wall(seed=0)
        with pytest.raises(ValueError):
            WallState(tiles=good_wall.tiles, live_pos=0, rinshan_drawn=0, dora_revealed=0)


# ---------------------------------------------------------------------------
# Hypothesis property tests
# ---------------------------------------------------------------------------


@given(st.integers(min_value=0, max_value=2**31 - 1))
@settings(max_examples=100)
def test_any_seed_produces_valid_wall(seed: int) -> None:
    """For any seed, build_wall produces exactly 136 tiles with correct counts."""
    wall = build_wall(seed=seed)

    assert len(wall.tiles) == TOTAL_TILES

    counts = Counter(wt.code for wt in wall.tiles)
    for code in range(TILE_COUNT):
        assert counts[code] == 4

    aka_tiles = [wt for wt in wall.tiles if wt.is_aka]
    assert len(aka_tiles) == 3
    assert {wt.code for wt in aka_tiles} == {AKA_5M_BASE, AKA_5P_BASE, AKA_5S_BASE}

    assert wall.live_remaining == TOTAL_TILES - DEAD_WALL_SIZE
    assert len(wall.dead_wall) == DEAD_WALL_SIZE

# ---------------------------------------------------------------------------
# M1 Guide Demo Tests
# ---------------------------------------------------------------------------

def test_m1_guide_demo_wall() -> None:
    from mahjong_engine.tiles import tile_to_str
    w = build_wall(mode='yonma', seed=42)
    assert len(w.tiles) == 136
    assert w.live_remaining == 122
    assert len(w.dead_wall) == 14
    assert w.dora_revealed == 1
    ind = w.dora_indicators[0]
    assert tile_to_str(ind.code, ind.is_aka) == '8m'
    assert [tile_to_str(t) for t in w.active_dora_tiles] == ['9m']
    assert tile_to_str(w.peek_live().code, w.peek_live().is_aka) == '6m'
