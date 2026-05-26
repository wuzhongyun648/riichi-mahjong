"""Tests for mahjong_engine.tenpai.

Covers shanten / is_tenpai / winning_tiles across standard, chiitoitsu, and
kokushi forms, with melds and without, plus hypothesis-based properties.
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from mahjong_engine.decompose import is_complete_hand
from mahjong_engine.hand import Hand, Meld, MeldType
from mahjong_engine.tenpai import (
    is_tenpai,
    shanten,
    winning_tiles,
)
from mahjong_engine.tiles import TILE_COUNT, is_yaochuuhai


def counts_of(s: str) -> tuple[int, ...]:
    return Hand.from_str(s).counts


# ---------------------------------------------------------------------------
# shanten basic
# ---------------------------------------------------------------------------


class TestShantenStandard:
    def test_complete_hand_shanten_minus1(self) -> None:
        counts = counts_of("1m 2m 3m 4p 5p 6p 7s 8s 9s 东 东 东 5m 5m")
        assert shanten(counts) == -1

    def test_tenpai_tanki(self) -> None:
        # 4 mentsu fixed + single waiting for that tile.
        # 123m + 456p + 789s + 东东东 + 白 (waits 白)
        counts = counts_of("1m 2m 3m 4p 5p 6p 7s 8s 9s 东 东 东 白")
        assert shanten(counts) == 0

    def test_tenpai_ryanmen(self) -> None:
        # 23m waits 1m or 4m, three mentsu + pair.
        counts = counts_of("2m 3m 4p 5p 6p 7p 8p 9p 1s 1s 1s 9s 9s")
        assert shanten(counts) == 0

    def test_tenpai_shanpon(self) -> None:
        # 三面子 + 两对子 (双碰): waits two koutsu candidates.
        counts = counts_of("1m 2m 3m 4p 5p 6p 7s 8s 9s 东 东 南 南")
        assert shanten(counts) == 0

    def test_tenpai_kanchan(self) -> None:
        # 1m+3m waits 2m, plus 3 mentsu + pair.
        counts = counts_of("1m 3m 4p 5p 6p 7s 8s 9s 东 东 东 9s 9s")
        assert shanten(counts) == 0

    def test_one_shanten(self) -> None:
        # 3 mentsu + pair + 2 isolated honors (no taatsu) = 1-shanten.
        # Plan: 123m / 456p / 789s / 5m5m + {东, 南} isolated → need one more
        # mentsu (2 swaps) but already have a head, so shanten = 1.
        counts = counts_of("1m 2m 3m 4p 5p 6p 7s 8s 9s 5m 5m 东 南")
        assert shanten(counts) == 1

    def test_far_from_tenpai(self) -> None:
        # 13 random isolated tiles, e.g. 1m 4m 7m 1p 4p 7p 1s 4s 7s 东 南 西 北
        counts = counts_of("1m 4m 7m 1p 4p 7p 1s 4s 7s 东 南 西 北")
        assert shanten(counts) >= 4


class TestShantenChiitoi:
    def test_chiitoi_complete(self) -> None:
        counts = counts_of("1m 1m 2m 2m 3p 3p 4p 4p 5s 5s 6s 6s 中 中")
        assert shanten(counts) == -1

    def test_chiitoi_tenpai_one_single(self) -> None:
        # 6 pairs + 1 single → waits the single.
        counts = counts_of("1m 1m 2m 2m 3p 3p 4p 4p 5s 5s 6s 6s 中")
        assert shanten(counts) == 0

    def test_chiitoi_iishanten(self) -> None:
        # 5 pairs + 3 singles → iishanten via chiitoi.
        counts = counts_of("1m 1m 2m 2m 3p 3p 4p 4p 5s 5s 6s 7s 中")
        # Pairs=5, unique=8 → 6-5+max(0,7-8)=1. Standard could be worse;
        # chiitoi wins.
        assert shanten(counts) == 1


class TestShantenKokushi:
    def test_kokushi_complete(self) -> None:
        counts = counts_of("1m 1m 9m 1p 9p 1s 9s 东 南 西 北 白 发 中")
        assert shanten(counts) == -1

    def test_kokushi_tenpai_13_way(self) -> None:
        # 13 distinct yaochuu → waits any of the 13.
        counts = counts_of("1m 9m 1p 9p 1s 9s 东 南 西 北 白 发 中")
        assert shanten(counts) == 0

    def test_kokushi_single_wait(self) -> None:
        # 12 distinct yaochuu + 1 pair → waits the missing yaochuu.
        counts = counts_of("1m 1m 9m 1p 9p 1s 9s 东 南 西 北 白 发")  # missing 中
        assert shanten(counts) == 0


# ---------------------------------------------------------------------------
# is_tenpai
# ---------------------------------------------------------------------------


class TestIsTenpai:
    def test_tenpai_true(self) -> None:
        counts = counts_of("2m 3m 4p 5p 6p 7p 8p 9p 1s 1s 1s 9s 9s")
        assert is_tenpai(counts) is True

    def test_not_tenpai(self) -> None:
        counts = counts_of("1m 4m 7m 1p 4p 7p 1s 4s 7s 东 南 西 北")
        assert is_tenpai(counts) is False

    def test_requires_13_tile_phase(self) -> None:
        # 14 tiles → not allowed for is_tenpai.
        counts = counts_of("1m 2m 3m 4p 5p 6p 7s 8s 9s 东 东 东 5m 5m")
        with pytest.raises(ValueError):
            is_tenpai(counts)


# ---------------------------------------------------------------------------
# winning_tiles
# ---------------------------------------------------------------------------


class TestWinningTiles:
    def test_tanki(self) -> None:
        # waits 白 = code 31
        counts = counts_of("1m 2m 3m 4p 5p 6p 7s 8s 9s 东 东 东 白")
        assert winning_tiles(counts) == [31]

    def test_ryanmen(self) -> None:
        # 2m3m waits 1m (0) or 4m (3).
        counts = counts_of("2m 3m 4p 5p 6p 7p 8p 9p 1s 1s 1s 9s 9s")
        assert winning_tiles(counts) == [0, 3]

    def test_kanchan(self) -> None:
        # 1m+3m waits 2m (code 1). Filler: 4p5p6p 7s8s9s 东东东 9s9s? No
        # 9s already used twice. Let me check tile budget.
        # 1m, 3m, 4p,5p,6p, 7s,8s,9s, 东,东,东, 9s, 9s — that's 9s appearing 3 times. Allowed.
        counts = counts_of("1m 3m 4p 5p 6p 7s 8s 9s 东 东 东 9s 9s")
        assert winning_tiles(counts) == [1]

    def test_penchan(self) -> None:
        # 1m2m waits 3m only (边张).
        counts = counts_of("1m 2m 4p 5p 6p 7p 8p 9p 1s 1s 1s 9s 9s")
        assert winning_tiles(counts) == [2]

    def test_shanpon(self) -> None:
        # 双碰: waits 东 (27) or 南 (28).
        counts = counts_of("1m 2m 3m 4p 5p 6p 7s 8s 9s 东 东 南 南")
        assert winning_tiles(counts) == [27, 28]

    def test_chiitoi_wait(self) -> None:
        # 6 pairs + 1 single → waits the single (中 = 33).
        counts = counts_of("1m 1m 2m 2m 3p 3p 4p 4p 5s 5s 6s 6s 中")
        waits = winning_tiles(counts)
        assert 33 in waits

    def test_kokushi_13_way(self) -> None:
        # 13 distinct yaochuu → waits all 13.
        counts = counts_of("1m 9m 1p 9p 1s 9s 东 南 西 北 白 发 中")
        waits = winning_tiles(counts)
        expected = sorted(t for t in range(34) if is_yaochuuhai(t))
        assert waits == expected

    def test_kokushi_single(self) -> None:
        # 12 distinct yaochuu + 1 pair → waits the missing 中 (33).
        counts = counts_of("1m 1m 9m 1p 9p 1s 9s 东 南 西 北 白 发")
        assert winning_tiles(counts) == [33]

    def test_no_waits_for_non_tenpai(self) -> None:
        counts = counts_of("1m 4m 7m 1p 4p 7p 1s 4s 7s 东 南 西 北")
        assert winning_tiles(counts) == []

    def test_requires_13_tile_phase(self) -> None:
        counts = counts_of("1m 2m 3m 4p 5p 6p 7s 8s 9s 东 东 东 5m 5m")
        with pytest.raises(ValueError):
            winning_tiles(counts)


# ---------------------------------------------------------------------------
# Melds
# ---------------------------------------------------------------------------


class TestWithMelds:
    @staticmethod
    def chi_123m() -> Meld:
        return Meld(
            type=MeldType.CHI,
            tiles=(0, 1, 2),
            called_from=1,
            called_tile=1,
        )

    @staticmethod
    def pon_east() -> Meld:
        return Meld(
            type=MeldType.PON,
            tiles=(27, 27, 27),
            called_from=2,
            called_tile=27,
        )

    def test_tenpai_with_one_chi(self) -> None:
        # Meld: chi 123m. Concealed: 456p 789p 111s + 9s (tanki on 9s).
        # sum(counts) = 10; total = 13.
        chi = self.chi_123m()
        counts = counts_of("4p 5p 6p 7p 8p 9p 1s 1s 1s 9s")
        assert is_tenpai(counts, melds=(chi,)) is True
        assert winning_tiles(counts, melds=(chi,)) == [26]

    def test_shanten_with_two_melds(self) -> None:
        # Two melds (chi 123m, pon 东); concealed 4p5p6p 7s8s9s 5m5m -> already 4 mentsu.
        # sum(counts) = 8; total = 14. Complete!
        chi = self.chi_123m()
        pon = self.pon_east()
        counts = counts_of("4p 5p 6p 7s 8s 9s 5m 5m")
        assert shanten(counts, melds=(chi, pon)) == -1

    def test_chiitoi_disabled_with_melds(self) -> None:
        # With melds, chiitoi / kokushi are disabled (require 门清). Shanten
        # must fall back to the standard form only.
        chi = self.chi_123m()
        # Concealed 10 tiles, no pairs and only kanchan-type proto-runs →
        # cannot reach tenpai cheaply under the standard form.
        counts = counts_of("4p 6p 8p 2s 4s 6s 8s 东 南 西")
        s = shanten(counts, melds=(chi,))
        # m_concealed = 0 (no full mentsu), best taatsu config is 3
        # non-overlapping kanchan; with the 1 chi → m_total = 1, no pair.
        # shanten = 8 - 2*1 - 3 - 0 = 3.
        assert s >= 3

    def test_input_validation_bad_tile_budget(self) -> None:
        # 12 tiles with no melds → invalid.
        bad = [0] * TILE_COUNT
        bad[0] = 12
        with pytest.raises(ValueError):
            shanten(bad, melds=())


# ---------------------------------------------------------------------------
# Hypothesis properties
# ---------------------------------------------------------------------------


@st.composite
def random_13_tile_counts(draw: st.DrawFn) -> tuple[int, ...]:
    """Sample 13 tiles uniformly from the 136-tile wall."""
    counts = [0] * TILE_COUNT
    for _ in range(13):
        for _ in range(20):
            t = draw(st.integers(min_value=0, max_value=33))
            if counts[t] < 4:
                counts[t] += 1
                break
        else:
            # Couldn't find a slot — bail out (very unlikely).
            return tuple()
    return tuple(counts)


@settings(
    max_examples=80,
    deadline=4000,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(random_13_tile_counts())
def test_shanten_in_valid_range(counts: tuple[int, ...]) -> None:
    if sum(counts) != 13:
        return
    s = shanten(counts)
    # 13-tile hand: shanten ∈ [0, 8].
    assert 0 <= s <= 8


@settings(
    max_examples=80,
    deadline=4000,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(random_13_tile_counts())
def test_winning_tiles_actually_complete(counts: tuple[int, ...]) -> None:
    if sum(counts) != 13:
        return
    waits = winning_tiles(counts)
    work = list(counts)
    for t in waits:
        assert work[t] < 4
        work[t] += 1
        assert is_complete_hand(work, n_melds=0), (
            f"winning tile {t} did not complete hand counts={counts}"
        )
        work[t] -= 1


@settings(
    max_examples=80,
    deadline=4000,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(random_13_tile_counts())
def test_tenpai_iff_winning_tiles_nonempty(counts: tuple[int, ...]) -> None:
    if sum(counts) != 13:
        return
    assert is_tenpai(counts) == bool(winning_tiles(counts))


# Synthesise a complete hand by adding a wait to a tenpai counts and verify
# shanten goes to -1.


@st.composite
def tenpai_then_complete(draw: st.DrawFn) -> tuple[tuple[int, ...], int] | None:
    counts = draw(random_13_tile_counts())
    if sum(counts) != 13:
        return None
    waits = winning_tiles(counts)
    if not waits:
        return None
    return counts, draw(st.sampled_from(waits))


@settings(
    max_examples=60,
    deadline=4000,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(tenpai_then_complete())
def test_winning_tile_makes_shanten_minus1(
    sample: tuple[tuple[int, ...], int] | None,
) -> None:
    if sample is None:
        return
    counts, wt = sample
    work = list(counts)
    work[wt] += 1
    assert shanten(tuple(work)) == -1

# ---------------------------------------------------------------------------
# M2 Guide Demo Tests
# ---------------------------------------------------------------------------

def test_m2_guide_demo_tenpai() -> None:
    from mahjong_engine.hand import Meld, MeldType
    from mahjong_engine.tiles import make_counts, parse_tiles, tile_to_str
    def to_counts(s):
        return make_counts([t for t,_ in parse_tiles(s)])
    
    def get_waits(counts, melds=()):
        w = winning_tiles(counts, melds)
        return [tile_to_str(t) for t in w]

    # 标准型听法
    c = to_counts('1m 2m 3m 4m 5m 6m 7m 6p 7p 8p 1s 1s 1s')
    assert shanten(c) == 0
    assert is_tenpai(c) is True
    assert get_waits(c) == ['1m', '4m', '7m']

    c = to_counts('1m 3m 4p 5p 6p 7p 8p 9p 1s 2s 3s 东 东')
    assert get_waits(c) == ['2m']

    c = to_counts('1m 2m 4p 5p 6p 7p 8p 9p 1s 2s 3s 东 东')
    assert get_waits(c) == ['3m']

    c = to_counts('1m 2m 3m 4m 5m 6m 7m 8m 9m 6p 7p 8p 东')
    assert get_waits(c) == ['东']

    c = to_counts('1m 2m 3m 4p 5p 6p 7s 8s 9s 5m 5m 9p 9p')
    assert get_waits(c) == ['5m', '9p']

    c = to_counts('1m 1m 1m 2m 3m 4m 5m 6m 7m 8m 9m 9m 9m')
    assert get_waits(c) == ['1m', '2m', '3m', '4m', '5m', '6m', '7m', '8m', '9m']

    # 七対子 / 国士
    c = to_counts('1m 1m 3m 3m 5p 5p 7p 7p 1s 1s 3s 3s 东')
    assert get_waits(c) == ['东']

    c = to_counts('1m 9m 1p 9p 1s 9s 东 南 西 北 白 发 发')
    assert get_waits(c) == ['中']

    c = to_counts('1m 9m 1p 9p 1s 9s 东 南 西 北 白 发 中')
    assert get_waits(c) == [
        '1m', '9m', '1p', '9p', '1s', '9s', '东', '南', '西', '北', '白', '发', '中',
    ]

    # 副露场景
    chi_123m = Meld(type=MeldType.CHI, tiles=(0,1,2), called_from=3, called_tile=0)
    pon_dong = Meld(type=MeldType.PON, tiles=(27,27,27), called_from=1, called_tile=27)
    
    c = to_counts('4m 5m 6m 7p 8p 9p 7s 8s 8s 9s')
    assert get_waits(c, (chi_123m,)) == ['8s']

    c = to_counts('1m 2m 3m 6p 7p 8p 5s')
    assert get_waits(c, (chi_123m, pon_dong)) == ['5s']

    # n-shanten
    c = to_counts('1m 2m 3m 4p 5p 6p 7s 8s 9s 5m 5m 东 南')
    assert shanten(c) == 1

    c = to_counts('1m 2m 3m 4p 5p 6p 7s 8s 东 东 南 西 北')
    assert shanten(c) == 2

    # 14 张和牌检测
    c = to_counts('1m 2m 3m 4m 5m 6m 7m 8m 9m 6p 7p 8p 东 东')
    assert shanten(c) == -1


# ---------------------------------------------------------------------------
# Additional Test Cases from MahjongRepository/mahjong
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('hand_str', 'expected_shanten'),
    [
        ('5m 6m 7m 1p 1p 1s 1s 1s 2s 3s 4s 5s 6s 7s', -1),
        ('5m 6m 7m 1p 1p 1s 1s 1s 3s 4s 5s 6s 7s 7s', 0),
        ('5m 6m 7m 1p 5p 1s 1s 1s 3s 4s 5s 6s 7s 7s', 1),
        ('1m 5m 7m 8m 1p 5p 1s 1s 1s 3s 4s 5s 6s 7s', 2),
        ('1m 3m 5m 8m 1p 3p 5p 8p 1s 1s 3s 4s 5s 6s', 3),
        ('1m 3m 5m 8m 1p 3p 5p 8p 8p 1s 5s 8s 9s 东', 4),
        ('1m 3m 5m 8m 1p 3p 5p 8p 8p 1s 5s 9s 东 南', 5),
        ('1m 3m 5m 8m 2p 5p 8p 1s 5s 8s 9s 东 南 西', 6),
        ('1s 1s 1s 2s 3s 4s 5s 6s 7s 8s 8s 9s 9s 9s', -1),
        ('1s 1s 1s 2s 2s 2s 4s 5s 6s 7s 9s 9s 9s 9s', 0),
        ('3m 5m 9m 1p 7p 1s 5s 9s 东 南 西 白 发 中', 7),
        ('东 东 东 东 南 南 南 南 西 西 西 北 北 北', 1),
        ('1m 1m 东 东 东 东 南 南 南 南 西 西 西 西', 2),
        ('2m 3m 东 东 东 东 南 南 南 南 西 西 西 西', 2),
        ('3m 3m 3m 4m 4m 4m 5m 5m 5m 1s 1s 1s 1s', 1),
        ('1p 1p 1s 1s 1s 2s 3s 4s 5s 6s 7s 中 中', 0),
        ('5m 6m 7m 1p 1s 1s 1s 3s 4s 5s 6s 7s 7s', 1),
        ('5m 6m 1s 1s 1s 3s 4s 5s 6s 7s 7s', 0),
        ('1m 2m 3m 4m 5m 6m 7m 8m 9m 东 东 东 东', 1),
        ('1m 1m 1m 1m 1p 2p 3p 1s 1s 2s 2s 3s 3s', 1),
        ('东 东 东 东 南 南 南 西 西 西 北 北 北', 1),
        ('1m 1m 东 东 东 东 南 南 南 南 西 西 西', 2),
        ('2m 3m 东 东 东 东 南 南 南 南 西 西 西', 2),
        ('东 东 东 东 南 南 南 南 西 西 西 西 北', 3),
    ]
)
def test_additional_shanten_standard(hand_str: str, expected_shanten: int) -> None:
    from mahjong_engine.tenpai import _standard_shanten
    from mahjong_engine.tiles import make_counts, parse_tiles
    counts = make_counts([t for t, _ in parse_tiles(hand_str)])
    n_melds = (14 - sum(counts)) // 3
    assert _standard_shanten(counts, n_melds) == expected_shanten

@pytest.mark.parametrize(
    ('hand_str', 'expected_shanten'),
    [
        ('7m 7m 1p 1p 4p 4p 7p 7p 1s 1s 4s 4s 7s 7s', -1),
        ('7m 6m 1p 1p 4p 4p 7p 7p 1s 1s 4s 4s 7s 7s', 0),
        ('7m 6m 1p 1p 4p 4p 7p 9p 1s 1s 4s 4s 7s 7s', 1),
        ('7m 6m 1p 4p 4p 7p 9p 1s 1s 4s 4s 7s 7s 东', 2),
        ('7m 6m 1p 3p 4p 7p 9p 1s 1s 4s 4s 7s 7s 东', 3),
        ('7m 6m 1p 3p 4p 7p 9p 1s 1s 4s 4s 6s 7s 东', 4),
        ('7m 6m 1p 3p 4p 7p 9p 1s 1s 4s 3s 6s 7s 东', 5),
        ('7m 6m 1p 3p 4p 7p 9p 1s 2s 4s 3s 6s 7s 东', 6),
        ('2m 2m 5m 5m 5p 5p 6s 6s 6s 7s 7s 8s 8s 8s', 1),
    ]
)
def test_additional_shanten_chiitoi(hand_str: str, expected_shanten: int) -> None:
    from mahjong_engine.tenpai import _chiitoi_shanten
    from mahjong_engine.tiles import make_counts, parse_tiles
    counts = make_counts([t for t, _ in parse_tiles(hand_str)])
    assert _chiitoi_shanten(counts) == expected_shanten

@pytest.mark.parametrize(
    ('hand_str', 'expected_shanten'),
    [
        ('1m 9m 1p 9p 1s 9s 东 南 西 北 白 发 中 中', -1),
        ('1m 9m 1p 9p 1s 2s 9s 东 南 西 北 白 发 中', 0),
        ('1m 9m 1p 2p 9p 1s 2s 9s 东 南 西 北 白 发', 1),
        ('1m 2m 9m 1p 2p 9p 1s 2s 9s 东 南 西 北 白', 2),
        ('1m 2m 9m 1p 2p 9p 1s 2s 3s 9s 南 西 北 白', 3),
        ('1m 2m 9m 1p 2p 3p 9p 1s 2s 3s 9s 西 北 白', 4),
        ('1m 2m 3m 9m 1p 2p 3p 9p 1s 2s 3s 9s 北 白', 5),
        ('1m 2m 3m 9m 1p 2p 3p 9p 1s 2s 3s 4s 9s 白', 6),
        ('1m 2m 3m 9m 1p 2p 3p 4p 9p 1s 2s 3s 4s 9s', 7),
    ]
)
def test_additional_shanten_kokushi(hand_str: str, expected_shanten: int) -> None:
    from mahjong_engine.tenpai import _kokushi_shanten
    from mahjong_engine.tiles import make_counts, parse_tiles
    counts = make_counts([t for t, _ in parse_tiles(hand_str)])
    assert _kokushi_shanten(counts) == expected_shanten

