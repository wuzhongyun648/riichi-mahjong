"""Shared helpers for M3 yaku tests."""

from __future__ import annotations

from mahjong_engine.game_state import Wind
from mahjong_engine.hand import Hand, Meld, MeldType
from mahjong_engine.tiles import parse_tile
from mahjong_engine.yaku import WinContext, judge_yaku
from mahjong_engine.yaku.result import YakuDecomp


def judge(
    hand_str: str,
    win: str,
    *,
    melds: tuple[Meld, ...] = (),
    rw: Wind = Wind.EAST,
    sw: Wind = Wind.SOUTH,
    tsumo: bool = True,
    **flags: bool,
) -> list[YakuDecomp]:
    """Build a hand + context and run judge_yaku."""
    hand = Hand.from_str(hand_str, melds=melds)
    win_tile = parse_tile(win)[0]
    ctx = WinContext(round_wind=rw, seat_wind=sw, is_tsumo=tsumo, **flags)
    return judge_yaku(hand, win_tile, ctx)


def has(res: list[YakuDecomp], yaku_id: str) -> bool:
    """True if any decomposition contains the given yaku id."""
    return any(yaku_id in {y.id for y in e.yaku} for e in res)


def max_han(res: list[YakuDecomp]) -> int:
    """Highest normal-yaku han across decompositions (0 if none/yakuman)."""
    return max((e.han for e in res if not e.is_yakuman), default=0)


def yakuman_units(res: list[YakuDecomp]) -> int:
    """Highest yakuman units across decompositions (0 if not a yakuman)."""
    return max((e.yakuman_units for e in res), default=0)


def kan(tile: int, *, closed: bool = True) -> Meld:
    """Build a kan meld of one tile."""
    return Meld(
        type=MeldType.KAN_CLOSED if closed else MeldType.KAN_OPEN,
        tiles=(tile, tile, tile, tile),
        called_from=None if closed else 1,
        called_tile=None if closed else tile,
    )


def chi(low: int, called_from: int = 3) -> Meld:
    """Build a chi meld (low, low+1, low+2)."""
    return Meld(
        type=MeldType.CHI,
        tiles=(low, low + 1, low + 2),
        called_from=called_from,
        called_tile=low,
    )


def pon(tile: int, called_from: int = 1) -> Meld:
    """Build a pon meld of one tile."""
    return Meld(
        type=MeldType.PON,
        tiles=(tile, tile, tile),
        called_from=called_from,
        called_tile=tile,
    )
