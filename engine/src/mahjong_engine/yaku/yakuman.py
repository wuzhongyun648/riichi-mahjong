"""Yakuman and double-yakuman detection (docs/rules.md §8.5-§8.7).

Each evaluator returns the yakuman it found (if any).  ``judge_yaku``
sums their units, caps at 6, and drops all normal yaku when any yakuman is
present (§8.7, §8.8).
"""

from __future__ import annotations

from mahjong_engine.decompose import Decomposition
from mahjong_engine.hand import Hand
from mahjong_engine.tiles import (
    MAN_START,
    PIN_START,
    SOU_START,
    is_honor,
    is_terminal,
    tile_number,
    tile_suit,
)
from mahjong_engine.yaku.context import is_menzen
from mahjong_engine.yaku.partition import (
    SetKind,
    StandardPartition,
    WaitType,
    iter_all_tiles,
)
from mahjong_engine.yaku.result import Yaku

_DRAGONS: tuple[int, ...] = (31, 32, 33)
_WINDS: tuple[int, ...] = (27, 28, 29, 30)
# Green tiles for 绿一色: 2s/3s/4s/6s/8s + 发 (docs/rules.md §8.8 — 发 not required).
_GREEN: frozenset[int] = frozenset({19, 20, 21, 23, 25, 32})


# ---------------------------------------------------------------------------
# Whole-hand scans (apply to standard + chiitoitsu where shape allows)
# ---------------------------------------------------------------------------


def tsuuiisou(hand: Hand) -> Yaku | None:
    """字一色: every tile is an honor (§8.5)."""
    if all(is_honor(t) for t in iter_all_tiles(hand)):
        return Yaku("tsuuiisou", "字一色", 0, yakuman_units=1)
    return None


def ryuuiisou(hand: Hand) -> Yaku | None:
    """绿一色: every tile is green (§8.5, 发 not required per §8.8)."""
    if all(t in _GREEN for t in iter_all_tiles(hand)):
        return Yaku("ryuuiisou", "绿一色", 0, yakuman_units=1)
    return None


def chinroutou(hand: Hand) -> Yaku | None:
    """清老头: every tile is a terminal (1/9, no honors) (§8.5)."""
    if all(is_terminal(t) for t in iter_all_tiles(hand)):
        return Yaku("chinroutou", "清老头", 0, yakuman_units=1)
    return None


# ---------------------------------------------------------------------------
# Standard-shape yakuman
# ---------------------------------------------------------------------------


def _triplet_bases(part: StandardPartition) -> list[int]:
    return [s.base for s in part.sets if s.kind in (SetKind.TRIPLET, SetKind.KAN)]


def suuankou(part: StandardPartition) -> Yaku | None:
    """四暗刻 (§8.5) / 四暗刻单骑 (双役满, §8.6).

    Requires four concealed triplets.  The ron open-triplet rule is already
    applied in ``concealed_triplet_count`` (so a ron shanpon yields only three
    and never fires here); a tanki ron keeps all four concealed → double.
    """
    if part.concealed_triplet_count != 4:
        return None
    if WaitType.TANKI in part.wait_types:
        return Yaku("suuankou_tanki", "四暗刻单骑", 0, yakuman_units=2)
    return Yaku("suuankou", "四暗刻", 0, yakuman_units=1)


def daisangen(part: StandardPartition) -> Yaku | None:
    """大三元: triplets of all three dragons (§8.5)."""
    if sum(1 for b in _triplet_bases(part) if b in _DRAGONS) == 3:
        return Yaku("daisangen", "大三元", 0, yakuman_units=1)
    return None


def suushii(part: StandardPartition) -> Yaku | None:
    """小四喜 (§8.5) / 大四喜 (双役满, §8.6)."""
    wind_triplets = sum(1 for b in _triplet_bases(part) if b in _WINDS)
    if wind_triplets == 4:
        return Yaku("daisuushii", "大四喜", 0, yakuman_units=2)
    if wind_triplets == 3 and part.pair in _WINDS:
        return Yaku("shousuushii", "小四喜", 0, yakuman_units=1)
    return None


def suukantsu(part: StandardPartition) -> Yaku | None:
    """四杠子: four kans (§8.5)."""
    if part.kan_count == 4:
        return Yaku("suukantsu", "四杠子", 0, yakuman_units=1)
    return None


def chuuren(hand: Hand, win_tile: int) -> Yaku | None:
    """九莲宝灯 (§8.5) / 纯正九莲宝灯 (双役满, §8.6).

    Requires a fully concealed one-suit hand matching 1112345678999 + one
    extra of the same suit.  Pure (纯正) when the 13-tile wait was the
    nine-sided 1112345678999 — i.e. removing the win tile leaves that base.
    """
    if hand.melds or not is_menzen(hand):
        return None
    suits = {tile_suit(t) for t in iter_all_tiles(hand) if not is_honor(t)}
    has_honor = any(is_honor(t) for t in iter_all_tiles(hand))
    if has_honor or len(suits) != 1:
        return None
    # Locate the suit's nine-tile window.
    suit = next(iter(suits))
    offset = {"m": MAN_START, "p": PIN_START, "s": SOU_START}[suit]
    suit_counts = [hand.counts[offset + i] for i in range(9)]
    if sum(suit_counts) != 14:
        return None
    base = [3, 1, 1, 1, 1, 1, 1, 1, 3]
    if any(suit_counts[i] < base[i] for i in range(9)):
        return None
    win_local = tile_number(win_tile) - 1
    remainder = list(suit_counts)
    remainder[win_local] -= 1
    if remainder == base:
        return Yaku("junsei_chuuren", "纯正九莲宝灯", 0, yakuman_units=2)
    return Yaku("chuuren", "九莲宝灯", 0, yakuman_units=1)


# ---------------------------------------------------------------------------
# Kokushi
# ---------------------------------------------------------------------------


def kokushi(decomp: Decomposition, win_tile: int) -> Yaku:
    """国士无双 (§8.5) / 国士无双十三面 (双役满, §8.6).

    Thirteen-sided when the winning tile is the one that pairs up — i.e. the
    13-tile wait held all thirteen yaochuu as singles.
    """
    if win_tile == decomp.pair_tile:
        return Yaku("kokushi_13", "国士无双十三面", 0, yakuman_units=2)
    return Yaku("kokushi", "国士无双", 0, yakuman_units=1)


# ---------------------------------------------------------------------------
# Aggregators
# ---------------------------------------------------------------------------


def standard_yakuman(part: StandardPartition, hand: Hand, win_tile: int) -> list[Yaku]:
    """All yakuman for a standard-form winning hand."""
    out: list[Yaku] = []
    for maybe in (
        suuankou(part),
        daisangen(part),
        suushii(part),
        suukantsu(part),
        tsuuiisou(hand),
        ryuuiisou(hand),
        chinroutou(hand),
        chuuren(hand, win_tile),
    ):
        if maybe is not None:
            out.append(maybe)
    return out


def chiitoitsu_yakuman(hand: Hand) -> list[Yaku]:
    """Yakuman reachable in seven-pairs shape (only 字一色)."""
    ts = tsuuiisou(hand)
    return [ts] if ts is not None else []
