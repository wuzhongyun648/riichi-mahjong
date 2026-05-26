"""Property tests for M3 yaku judgement.

Hands are assembled from four random mentsu + a pair so they are complete by
construction; we then assert structural invariants of ``judge_yaku`` rather
than specific yaku.
"""

from __future__ import annotations

import hypothesis.strategies as st
from hypothesis import assume, given, settings

from mahjong_engine.game_state import Wind
from mahjong_engine.hand import Hand
from mahjong_engine.yaku import WinContext, has_any_yaku, judge_yaku

_SUIT_BASES = (0, 9, 18)  # manzu / pinzu / souzu starts


@st.composite
def winning_counts(draw: st.DrawFn) -> tuple[int, ...]:
    """A 14-tile standard winning hand as a counts[34] tuple."""
    counts = [0] * 34
    counts[draw(st.integers(0, 33))] += 2  # pair
    for _ in range(4):
        if draw(st.booleans()):  # triplet
            counts[draw(st.integers(0, 33))] += 3
        else:  # sequence
            low = draw(st.sampled_from(_SUIT_BASES)) + draw(st.integers(0, 6))
            counts[low] += 1
            counts[low + 1] += 1
            counts[low + 2] += 1
    assume(all(c <= 4 for c in counts))
    return tuple(counts)


@given(winning_counts())
@settings(max_examples=300)
def test_judge_invariants(counts: tuple[int, ...]) -> None:
    hand = Hand(counts=counts)
    win = next(i for i, c in enumerate(counts) if c > 0)

    for tsumo in (True, False):
        ctx = WinContext(round_wind=Wind.EAST, seat_wind=Wind.SOUTH, is_tsumo=tsumo)
        res = judge_yaku(hand, win, ctx)

        # Tier homogeneity: never mix yakuman and normal entries.
        assert len({e.is_yakuman for e in res}) <= 1

        for e in res:
            if e.is_yakuman:
                assert e.han == 0
                assert all(y.yakuman_units > 0 for y in e.yaku)
                assert 1 <= e.yakuman_units <= 6
            else:
                assert e.yakuman_units == 0
                assert all(y.yakuman_units == 0 for y in e.yaku)
                assert e.han == sum(y.han for y in e.yaku)
                assert e.has_yaku

        assert has_any_yaku(hand, win, ctx) == bool(res)


@given(winning_counts())
@settings(max_examples=200)
def test_closed_tsumo_always_has_yaku(counts: tuple[int, ...]) -> None:
    # A fully concealed self-draw always has at least 门前清自摸和.
    hand = Hand(counts=counts)
    win = next(i for i, c in enumerate(counts) if c > 0)
    ctx = WinContext(round_wind=Wind.EAST, seat_wind=Wind.SOUTH, is_tsumo=True)
    assert judge_yaku(hand, win, ctx)
