"""Tests for mahjong_engine.tiles.

Covers: predicates, string parsing/display, next_dora, make_counts.
Hypothesis property: parse_tile ∘ tile_to_str is the identity for all valid tiles.
"""

import hypothesis.strategies as st
import pytest
from hypothesis import given, settings

from mahjong_engine.tiles import (
    AKA_5M_BASE,
    AKA_5P_BASE,
    AKA_5S_BASE,
    CHUN,
    EAST,
    HAKU,
    HATSU,
    NORTH,
    SOUTH,
    TILE_COUNT,
    WEST,
    counts_to_tiles,
    is_chuuchanpai,
    is_dragon,
    is_honor,
    is_manzu,
    is_pinzu,
    is_souzu,
    is_terminal,
    is_wind,
    is_yaochuuhai,
    make_counts,
    next_dora,
    parse_tile,
    parse_tiles,
    tile_number,
    tile_suit,
    tile_to_str,
    tiles_to_str,
    validate_tile,
)

# ---------------------------------------------------------------------------
# Predicate tests
# ---------------------------------------------------------------------------


class TestPredicates:
    def test_manzu_range(self) -> None:
        assert all(is_manzu(t) for t in range(0, 9))
        assert not any(is_manzu(t) for t in range(9, 34))

    def test_pinzu_range(self) -> None:
        assert all(is_pinzu(t) for t in range(9, 18))
        assert not any(is_pinzu(t) for t in list(range(0, 9)) + list(range(18, 34)))

    def test_souzu_range(self) -> None:
        assert all(is_souzu(t) for t in range(18, 27))
        assert not any(is_souzu(t) for t in list(range(0, 18)) + list(range(27, 34)))

    def test_honor_range(self) -> None:
        assert all(is_honor(t) for t in range(27, 34))
        assert not any(is_honor(t) for t in range(0, 27))

    def test_wind_codes(self) -> None:
        assert is_wind(EAST) and is_wind(SOUTH) and is_wind(WEST) and is_wind(NORTH)
        assert not is_wind(HAKU)

    def test_dragon_codes(self) -> None:
        assert is_dragon(HAKU) and is_dragon(HATSU) and is_dragon(CHUN)
        assert not is_dragon(NORTH)

    def test_terminals(self) -> None:
        # 1m=0, 9m=8, 1p=9, 9p=17, 1s=18, 9s=26
        terminals = {0, 8, 9, 17, 18, 26}
        for t in range(34):
            assert is_terminal(t) == (t in terminals), f"Failed for tile {t}"

    def test_yaochuuhai_includes_honors_and_terminals(self) -> None:
        for t in range(34):
            assert is_yaochuuhai(t) == (is_terminal(t) or is_honor(t))

    def test_chuuchanpai_complement(self) -> None:
        for t in range(34):
            assert is_chuuchanpai(t) != is_yaochuuhai(t)


# ---------------------------------------------------------------------------
# String conversion tests
# ---------------------------------------------------------------------------


class TestTileToStr:
    def test_manzu_display(self) -> None:
        assert tile_to_str(0) == "1m"
        assert tile_to_str(8) == "9m"

    def test_pinzu_display(self) -> None:
        assert tile_to_str(9) == "1p"
        assert tile_to_str(17) == "9p"

    def test_souzu_display(self) -> None:
        assert tile_to_str(18) == "1s"
        assert tile_to_str(26) == "9s"

    def test_honor_display(self) -> None:
        expected = {27: "东", 28: "南", 29: "西", 30: "北", 31: "白", 32: "发", 33: "中"}
        for code, name in expected.items():
            assert tile_to_str(code) == name

    def test_aka_five_display(self) -> None:
        assert tile_to_str(AKA_5M_BASE, is_aka=True) == "赤5m"
        assert tile_to_str(AKA_5P_BASE, is_aka=True) == "赤5p"
        assert tile_to_str(AKA_5S_BASE, is_aka=True) == "赤5s"

    def test_aka_non_five_raises(self) -> None:
        with pytest.raises(ValueError):
            tile_to_str(0, is_aka=True)

    def test_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError):
            tile_to_str(34)
        with pytest.raises(ValueError):
            tile_to_str(-1)


class TestParseTile:
    def test_manzu_parse(self) -> None:
        assert parse_tile("1m") == (0, False)
        assert parse_tile("9m") == (8, False)

    def test_pinzu_parse(self) -> None:
        assert parse_tile("1p") == (9, False)
        assert parse_tile("9p") == (17, False)

    def test_souzu_parse(self) -> None:
        assert parse_tile("1s") == (18, False)
        assert parse_tile("9s") == (26, False)

    def test_honor_parse(self) -> None:
        assert parse_tile("东") == (27, False)
        assert parse_tile("南") == (28, False)
        assert parse_tile("西") == (29, False)
        assert parse_tile("北") == (30, False)
        assert parse_tile("白") == (31, False)
        assert parse_tile("发") == (32, False)
        assert parse_tile("中") == (33, False)

    def test_aka_five_parse(self) -> None:
        assert parse_tile("赤5m") == (AKA_5M_BASE, True)
        assert parse_tile("赤5p") == (AKA_5P_BASE, True)
        assert parse_tile("赤5s") == (AKA_5S_BASE, True)

    def test_whitespace_stripped(self) -> None:
        assert parse_tile("  1m  ") == (0, False)

    def test_invalid_strings(self) -> None:
        for bad in ("0m", "10p", "Xm", "", "赤6m", "foo"):
            with pytest.raises(ValueError):
                parse_tile(bad)

    def test_parse_tiles_sequence(self) -> None:
        result = parse_tiles("1m 赤5p 东")
        assert result == [(0, False), (AKA_5P_BASE, True), (27, False)]

    def test_tiles_to_str(self) -> None:
        tiles = [(0, False), (AKA_5P_BASE, True), (27, False)]
        assert tiles_to_str(tiles) == "1m 赤5p 东"


# ---------------------------------------------------------------------------
# Round-trip property test
# ---------------------------------------------------------------------------


@given(st.integers(min_value=0, max_value=33))
def test_round_trip_normal_tiles(tile: int) -> None:
    """tile_to_str then parse_tile recovers the original code."""
    s = tile_to_str(tile)
    code, is_aka = parse_tile(s)
    assert code == tile
    assert is_aka is False


@given(st.sampled_from([AKA_5M_BASE, AKA_5P_BASE, AKA_5S_BASE]))
def test_round_trip_aka_tiles(tile: int) -> None:
    """Aka-five round-trip."""
    s = tile_to_str(tile, is_aka=True)
    code, is_aka = parse_tile(s)
    assert code == tile
    assert is_aka is True


# ---------------------------------------------------------------------------
# next_dora tests
# ---------------------------------------------------------------------------


class TestNextDora:
    def test_manzu_wrap(self) -> None:
        assert next_dora(0) == 1   # 1m → 2m
        assert next_dora(8) == 0   # 9m → 1m

    def test_pinzu_wrap(self) -> None:
        assert next_dora(9) == 10  # 1p → 2p
        assert next_dora(17) == 9  # 9p → 1p

    def test_souzu_wrap(self) -> None:
        assert next_dora(18) == 19
        assert next_dora(26) == 18

    def test_wind_cycle(self) -> None:
        # East→South→West→North→East
        assert next_dora(EAST) == SOUTH
        assert next_dora(SOUTH) == WEST
        assert next_dora(WEST) == NORTH
        assert next_dora(NORTH) == EAST

    def test_dragon_cycle(self) -> None:
        # Haku→Hatsu→Chun→Haku
        assert next_dora(HAKU) == HATSU
        assert next_dora(HATSU) == CHUN
        assert next_dora(CHUN) == HAKU

    def test_mid_manzu(self) -> None:
        assert next_dora(4) == 5   # 5m → 6m


# ---------------------------------------------------------------------------
# make_counts / counts_to_tiles
# ---------------------------------------------------------------------------


class TestMakeCounts:
    def test_simple(self) -> None:
        counts = make_counts([0, 0, 9])
        assert counts[0] == 2
        assert counts[9] == 1
        assert sum(counts) == 3

    def test_empty(self) -> None:
        assert make_counts([]) == [0] * TILE_COUNT

    def test_over_four_raises(self) -> None:
        with pytest.raises(ValueError):
            make_counts([0, 0, 0, 0, 0])  # five 1m

    def test_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError):
            make_counts([34])

    def test_round_trip_with_counts_to_tiles(self) -> None:
        tiles_in = [0, 0, 9, 27]
        counts = make_counts(tiles_in)
        tiles_out = counts_to_tiles(counts)
        assert sorted(tiles_out) == sorted(tiles_in)


@given(st.lists(st.integers(0, 33), min_size=0, max_size=14))
@settings(max_examples=200)
def test_make_counts_sum_preserved(tiles: list[int]) -> None:
    """make_counts preserves total tile count when no tile exceeds 4."""
    from collections import Counter
    c = Counter(tiles)
    if any(v > 4 for v in c.values()):
        with pytest.raises(ValueError):
            make_counts(tiles)
    else:
        counts = make_counts(tiles)
        assert sum(counts) == len(tiles)


# ---------------------------------------------------------------------------
# validate_tile
# ---------------------------------------------------------------------------


class TestValidateTile:
    def test_valid_range(self) -> None:
        for t in range(34):
            validate_tile(t)  # should not raise

    def test_out_of_range(self) -> None:
        for bad in (-1, 34, 100):
            with pytest.raises(ValueError):
                validate_tile(bad)

# ---------------------------------------------------------------------------
# M1 Guide Demo Tests
# ---------------------------------------------------------------------------

def test_m1_guide_demo_tiles() -> None:
    # 1. 单牌 / 多牌字符串解析
    assert parse_tile('5m') == (4, False)
    assert parse_tile('赤5m') == (4, True)
    assert parse_tile('东') == (27, False)
    ts = parse_tiles('1m 2m 3m 赤5p 东 东')
    assert ts == [(0, False), (1, False), (2, False), (13, True), (27, False), (27, False)]

    # 2. 反向：tile → string
    assert tile_to_str(4) == '5m'
    assert tile_to_str(4, True) == '赤5m'
    assert tiles_to_str(ts) == '1m 2m 3m 赤5p 东 东'

    # 3. 判定函数
    assert is_honor(0) is False and is_terminal(0) is True and is_yaochuuhai(0) is True
    assert is_honor(27) is True and is_wind(27) is True and is_dragon(27) is False
    assert is_honor(31) is True and is_wind(31) is False and is_dragon(31) is True

    # 4. 数字 / 花色
    assert tile_number(13) == 5
    assert tile_suit(13) == 'p'

    # 5. 宝牌指示推算
    assert next_dora(0) == 1
    assert next_dora(8) == 0
    assert next_dora(17) == 9
    assert next_dora(30) == 27
    assert next_dora(33) == 31

    # 6. counts 互转
    counts = make_counts([0, 0, 1, 2, 27, 27])
    assert counts[:4] == [2, 1, 1, 0]
    assert counts[27] == 2
    assert counts_to_tiles(counts) == [0, 0, 1, 2, 27, 27]
