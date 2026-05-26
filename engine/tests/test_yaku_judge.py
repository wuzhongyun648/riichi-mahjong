"""judge_yaku orchestration tests: list semantics, tier homogeneity, errors."""

from __future__ import annotations

import pytest

from mahjong_engine.game_state import Wind
from mahjong_engine.hand import Hand
from mahjong_engine.tiles import parse_tile
from mahjong_engine.yaku import WinContext, has_any_yaku, judge_yaku
from tests.yaku_util import chi, judge


def test_returns_one_entry_per_yaku_bearing_decomposition() -> None:
    # 112233m 445566m 99m parses as both ryanpeikou (standard) and chiitoitsu.
    res = judge("1m 2m 3m 1m 2m 3m 4m 5m 6m 4m 5m 6m 9m 9m", "9m")
    assert len(res) >= 2
    assert all(not e.is_yakuman for e in res)


def test_tier_homogeneity_yakuman_only() -> None:
    # A hand that is both 字一色 (yakuman) under standard form; every returned
    # entry must be yakuman (no normal entries leak through).
    res = judge("东 东 东 南 南 南 西 西 西 白 白 白 发 发", "东", tsumo=True)
    assert res
    assert all(e.is_yakuman for e in res)


def test_yakuless_open_hand_cannot_win() -> None:
    # Open hand (chi 123m), terminal pair, no tanyao / yakuhai / pinfu -> no yaku.
    res = judge("4p 5p 6p 7p 8p 9p 7s 8s 9s 9m 9m", "4p", melds=(chi(0),), tsumo=False)
    assert res == []


def test_has_any_yaku_matches_judge() -> None:
    hand = Hand.from_str("2m 3m 4m 5m 6m 7m 2p 3p 4p 7p 8p 9p 2s 2s")
    ctx = WinContext(round_wind=Wind.EAST, seat_wind=Wind.SOUTH, is_tsumo=True)
    win = parse_tile("4m")[0]
    assert has_any_yaku(hand, win, ctx) == bool(judge_yaku(hand, win, ctx))


def test_normal_entry_han_equals_sum() -> None:
    res = judge("2m 3m 4m 2m 3m 4m 6p 7p 8p 6p 7p 8p 9s 9s", "2m")
    for e in res:
        if not e.is_yakuman:
            assert e.han == sum(y.han for y in e.yaku)


def test_error_incomplete_hand() -> None:
    hand = Hand.from_str("1m 2m 3m 4m 5m 6m 7m 8m 9m 1p 2p 3p 5p 7p")
    ctx = WinContext(round_wind=Wind.EAST, seat_wind=Wind.SOUTH, is_tsumo=True)
    with pytest.raises(ValueError, match="complete"):
        judge_yaku(hand, parse_tile("5p")[0], ctx)


def test_error_win_tile_not_in_hand() -> None:
    hand = Hand.from_str("2m 3m 4m 5m 6m 7m 2p 3p 4p 7p 8p 9p 2s 2s")
    ctx = WinContext(round_wind=Wind.EAST, seat_wind=Wind.SOUTH, is_tsumo=True)
    with pytest.raises(ValueError, match="not present"):
        judge_yaku(hand, parse_tile("1s")[0], ctx)
