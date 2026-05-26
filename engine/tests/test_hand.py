"""Tests for mahjong_engine.hand.

Covers: Hand construction, add_tile/remove_tile, aka tracking, Meld validation.
Hypothesis property: add then remove returns original hand.
"""

import hypothesis.strategies as st
import pytest
from hypothesis import given, settings

from mahjong_engine.hand import Hand, Meld, MeldType
from mahjong_engine.tiles import (
    AKA_5M_BASE,
    AKA_5P_BASE,
    AKA_5S_BASE,
    TILE_COUNT,
)

# ---------------------------------------------------------------------------
# Hand basics
# ---------------------------------------------------------------------------


class TestHandEmpty:
    def test_empty_hand_zero_tiles(self) -> None:
        h = Hand.empty()
        assert h.tile_count == 0
        assert h.meld_count == 0
        assert h.aka_count == 0
        assert len(h.counts) == TILE_COUNT
        assert all(c == 0 for c in h.counts)

    def test_from_str_simple(self) -> None:
        h = Hand.from_str("1m 2m 3m")
        assert h.counts[0] == 1  # 1m
        assert h.counts[1] == 1  # 2m
        assert h.counts[2] == 1  # 3m
        assert h.tile_count == 3

    def test_from_str_with_honors(self) -> None:
        h = Hand.from_str("东 东 东")
        assert h.counts[27] == 3

    def test_from_str_with_aka(self) -> None:
        h = Hand.from_str("赤5m 赤5p 赤5s")
        assert h.aka_5m is True
        assert h.aka_5p is True
        assert h.aka_5s is True
        assert h.counts[AKA_5M_BASE] == 1
        assert h.counts[AKA_5P_BASE] == 1
        assert h.counts[AKA_5S_BASE] == 1


class TestAddTile:
    def test_add_increases_count(self) -> None:
        h = Hand.empty().add_tile(0)
        assert h.counts[0] == 1

    def test_add_aka_sets_flag(self) -> None:
        h = Hand.empty().add_tile(AKA_5M_BASE, is_aka=True)
        assert h.aka_5m is True
        assert h.counts[AKA_5M_BASE] == 1

    def test_add_non_aka_five_does_not_set_flag(self) -> None:
        h = Hand.empty().add_tile(AKA_5M_BASE, is_aka=False)
        assert h.aka_5m is False

    def test_add_five_copies_raises(self) -> None:
        h = Hand.from_str("1m 1m 1m 1m")
        with pytest.raises(ValueError):
            h.add_tile(0)

    def test_add_aka_to_non_five_raises(self) -> None:
        with pytest.raises(ValueError):
            Hand.empty().add_tile(0, is_aka=True)

    def test_add_preserves_immutability(self) -> None:
        h1 = Hand.empty()
        h2 = h1.add_tile(0)
        assert h1.counts[0] == 0   # original unchanged
        assert h2.counts[0] == 1


class TestRemoveTile:
    def test_remove_decreases_count(self) -> None:
        h = Hand.from_str("1m 1m").remove_tile(0)
        assert h.counts[0] == 1

    def test_remove_absent_raises(self) -> None:
        with pytest.raises(ValueError):
            Hand.empty().remove_tile(0)

    def test_remove_aka_clears_flag(self) -> None:
        h = Hand.empty().add_tile(AKA_5M_BASE, is_aka=True)
        h2 = h.remove_tile(AKA_5M_BASE, remove_aka=True)
        assert h2.aka_5m is False

    def test_remove_without_aka_keeps_flag(self) -> None:
        # Two 5m in hand (one aka, one normal); removing without remove_aka=True
        # should preserve the flag (we don't know which one was removed)
        h = Hand.from_str("5m").add_tile(AKA_5M_BASE, is_aka=True)
        h2 = h.remove_tile(AKA_5M_BASE, remove_aka=False)
        assert h2.aka_5m is True  # still holds one 5m, flag preserved


# ---------------------------------------------------------------------------
# Property: add then remove is identity
# ---------------------------------------------------------------------------


@given(
    st.integers(min_value=0, max_value=33),
    st.integers(min_value=0, max_value=12),
)
@settings(max_examples=300)
def test_add_then_remove_identity(tile: int, n_existing: int) -> None:
    """Adding then removing the same tile restores the original hand."""
    # Build a hand with n_existing tiles of other codes to have some context
    base_hand = Hand.empty()
    # Use tile 0 as filler if tile != 0, else use tile 1
    filler = 1 if tile == 0 else 0
    for _ in range(min(n_existing, 4)):
        base_hand = base_hand.add_tile(filler)

    # Only proceed if there's room for the target tile
    if base_hand.counts[tile] >= 4:
        return

    h_added = base_hand.add_tile(tile)
    h_restored = h_added.remove_tile(tile)
    assert h_restored.counts == base_hand.counts


# ---------------------------------------------------------------------------
# Meld tests
# ---------------------------------------------------------------------------


class TestMeld:
    def test_chi_meld(self) -> None:
        m = Meld(
            type=MeldType.CHI,
            tiles=(0, 1, 2),
            called_from=3,
            called_tile=0,
        )
        assert len(m.tiles) == 3
        assert len(m.aka_flags) == 3
        assert all(f is False for f in m.aka_flags)

    def test_kan_requires_four_tiles(self) -> None:
        with pytest.raises(ValueError):
            Meld(type=MeldType.KAN_OPEN, tiles=(0, 0, 0), called_from=1, called_tile=0)

    def test_chi_with_three_tiles_ok(self) -> None:
        m = Meld(type=MeldType.CHI, tiles=(0, 1, 2), called_from=3, called_tile=2)
        assert m.type == MeldType.CHI

    def test_aka_flags_default_false(self) -> None:
        m = Meld(type=MeldType.PON, tiles=(27, 27, 27), called_from=2, called_tile=27)
        assert m.aka_flags == (False, False, False)

    def test_aka_flags_custom(self) -> None:
        m = Meld(
            type=MeldType.CHI,
            tiles=(3, 4, 5),
            called_from=3,
            called_tile=5,
            aka_flags=(False, True, False),
        )
        assert m.aka_flags[1] is True

    def test_aka_flags_wrong_length_raises(self) -> None:
        with pytest.raises(ValueError):
            Meld(
                type=MeldType.CHI,
                tiles=(0, 1, 2),
                called_from=3,
                called_tile=0,
                aka_flags=(False, False),  # too short
            )

    def test_closed_kan_no_called_from(self) -> None:
        m = Meld(
            type=MeldType.KAN_CLOSED,
            tiles=(0, 0, 0, 0),
            called_from=None,
            called_tile=None,
        )
        assert m.called_from is None

    def test_meld_appended_to_hand(self) -> None:
        meld = Meld(type=MeldType.PON, tiles=(27, 27, 27), called_from=1, called_tile=27)
        h = Hand.empty().add_meld(meld)
        assert h.meld_count == 1

    def test_invalid_tile_in_meld_raises(self) -> None:
        with pytest.raises(ValueError):
            Meld(type=MeldType.PON, tiles=(34, 34, 34), called_from=1, called_tile=34)


# ---------------------------------------------------------------------------
# from_tile_list
# ---------------------------------------------------------------------------


class TestFromTileList:
    def test_round_trip(self) -> None:
        tiles = [(0, False), (1, False), (AKA_5P_BASE, True)]
        h = Hand.from_tile_list(tiles)
        assert h.counts[0] == 1
        assert h.counts[1] == 1
        assert h.counts[AKA_5P_BASE] == 1
        assert h.aka_5p is True

    def test_with_melds(self) -> None:
        meld = Meld(type=MeldType.PON, tiles=(27, 27, 27), called_from=1, called_tile=27)
        h = Hand.from_tile_list([(0, False)], melds=(meld,))
        assert h.meld_count == 1
        assert h.tile_count == 1

# ---------------------------------------------------------------------------
# M1 Guide Demo Tests
# ---------------------------------------------------------------------------

def test_m1_guide_demo_hand() -> None:
    from mahjong_engine.tiles import tile_to_str
    # 1. 直接从字符串构造 13 张手
    h = Hand.from_str('1m 2m 3m 赤5p 7p 8p 9p 1s 2s 3s 东 东 东')
    assert h.tile_count == 13
    assert h.aka_count == 1
    assert h.aka_5p is True
    assert h.meld_count == 0

    # 2. 增删
    h2 = h.add_tile(8)   # +9m
    assert h2.tile_count == 14
    h3 = h2.remove_tile(0)
    assert h3.tile_count == 13

    # 3. 副露
    chi = Meld(type=MeldType.CHI, tiles=(0, 1, 2), called_from=3, called_tile=0)
    assert [tile_to_str(t) for t in chi.tiles] == ['1m', '2m', '3m']
    assert chi.type.value == 'chi'
    h_with_chi = Hand.empty().add_meld(chi)
    assert h_with_chi.meld_count == 1
