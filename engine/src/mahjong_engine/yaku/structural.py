"""Normal (1-6 han) structural yaku (docs/rules.md §8.1-§8.4).

Two groups of evaluators:

  * Whole-hand scans (tanyao / honitsu / chinitsu / honroutou) inspect every
    tile and apply to both standard and chiitoitsu hands.
  * Standard-shape yaku operate on a ``StandardPartition`` (pinfu, iipeikou,
    sanshoku, ...).

Kuisagari (副露降番) is applied via the ``menzen`` flag.  Dora / aka are not
yaku and are excluded here (docs/rules.md §8.8).
"""

from __future__ import annotations

from collections import Counter

from mahjong_engine.hand import Hand
from mahjong_engine.tiles import (
    is_dragon,
    is_honor,
    is_terminal,
    is_yaochuuhai,
    tile_number,
    tile_suit,
)
from mahjong_engine.yaku.context import WinContext, is_menzen
from mahjong_engine.yaku.partition import (
    SetKind,
    StandardPartition,
    TileSet,
    WaitType,
    iter_all_tiles,
)
from mahjong_engine.yaku.result import Yaku

# Dragon tile codes and wind tile base (docs/tile-encoding.md).
_DRAGONS: tuple[int, ...] = (31, 32, 33)
_WIND_BASE: int = 27


# ---------------------------------------------------------------------------
# Whole-hand scans (shared by standard + chiitoitsu)
# ---------------------------------------------------------------------------


def is_tanyao(hand: Hand) -> bool:
    """断幺九: no terminal or honor tile anywhere (食断 enabled, §10.1)."""
    return all(not is_yaochuuhai(t) for t in iter_all_tiles(hand))


def is_honroutou(hand: Hand) -> bool:
    """混老头: every tile is a terminal or honor (§8.2)."""
    return all(is_yaochuuhai(t) for t in iter_all_tiles(hand))


def _suit_profile(hand: Hand) -> tuple[set[str], bool]:
    """Return (set of suited suits present, whether any honor is present)."""
    suits: set[str] = set()
    has_honor = False
    for t in iter_all_tiles(hand):
        if is_honor(t):
            has_honor = True
        else:
            suits.add(tile_suit(t))
    return suits, has_honor


def flush_yaku(hand: Hand, menzen: bool) -> Yaku | None:
    """清一色 (6/5) or 混一色 (3/2) — mutually exclusive (§8.3, §8.4)."""
    suits, has_honor = _suit_profile(hand)
    if len(suits) != 1:
        return None
    if has_honor:
        return Yaku("honitsu", "混一色", 3 if menzen else 2)
    return Yaku("chinitsu", "清一色", 6 if menzen else 5)


# ---------------------------------------------------------------------------
# Standard-shape helpers
# ---------------------------------------------------------------------------


def _sequences(sets: tuple[TileSet, ...]) -> list[TileSet]:
    return [s for s in sets if s.kind == SetKind.SEQUENCE]


def _triplets(sets: tuple[TileSet, ...]) -> list[TileSet]:
    return [s for s in sets if s.kind in (SetKind.TRIPLET, SetKind.KAN)]


def _set_has_yaochuu(s: TileSet) -> bool:
    if s.kind == SetKind.SEQUENCE:
        return tile_number(s.base) in (1, 7)  # 123 holds 1, 789 holds 9
    return is_yaochuuhai(s.base)


def _set_has_terminal(s: TileSet) -> bool:
    if s.kind == SetKind.SEQUENCE:
        return tile_number(s.base) in (1, 7)
    return is_terminal(s.base)


# ---------------------------------------------------------------------------
# Individual standard-shape yaku
# ---------------------------------------------------------------------------


def pinfu(part: StandardPartition, hand: Hand, ctx: WinContext) -> Yaku | None:
    """平和: menzen, all sequences, non-value pair, ryanmen wait (§8.1)."""
    if not is_menzen(hand):
        return None
    if any(s.kind != SetKind.SEQUENCE for s in part.sets):
        return None
    round_tile = _WIND_BASE + ctx.round_wind.value
    seat_tile = _WIND_BASE + ctx.seat_wind.value
    if is_dragon(part.pair) or part.pair in (round_tile, seat_tile):
        return None
    if WaitType.RYANMEN not in part.wait_types:
        return None
    return Yaku("pinfu", "平和", 1)


def peikou(part: StandardPartition, hand: Hand) -> Yaku | None:
    """一杯口 (1) / 二杯口 (3): identical sequences, menzen only (§8.1, §8.3)."""
    if not is_menzen(hand):
        return None
    lows = Counter(s.base for s in _sequences(part.sets))
    pairs = sum(c // 2 for c in lows.values())
    if pairs >= 2:
        return Yaku("ryanpeikou", "二杯口", 3)
    if pairs == 1:
        return Yaku("iipeikou", "一杯口", 1)
    return None


def sanshoku_doujun(part: StandardPartition, menzen: bool) -> Yaku | None:
    """三色同顺: same sequence in all three suits (§8.2, kuisagari)."""
    by_suit: dict[str, set[int]] = {"m": set(), "p": set(), "s": set()}
    for s in _sequences(part.sets):
        by_suit[tile_suit(s.base)].add(tile_number(s.base))
    common = by_suit["m"] & by_suit["p"] & by_suit["s"]
    if common:
        return Yaku("sanshoku", "三色同顺", 2 if menzen else 1)
    return None


def ittsuu(part: StandardPartition, menzen: bool) -> Yaku | None:
    """一气通贯: 123-456-789 in one suit (§8.2, kuisagari)."""
    by_suit: dict[str, set[int]] = {"m": set(), "p": set(), "s": set()}
    for s in _sequences(part.sets):
        by_suit[tile_suit(s.base)].add(tile_number(s.base))
    if any({1, 4, 7} <= nums for nums in by_suit.values()):
        return Yaku("ittsuu", "一气通贯", 2 if menzen else 1)
    return None


def chanta_junchan(part: StandardPartition, menzen: bool) -> Yaku | None:
    """混全带幺九 (2/1) / 纯全带幺九 (3/2) (§8.2, §8.3, kuisagari).

    Requires at least one sequence; otherwise the all-yaochuu shape is
    honroutou, not chanta.  Junchan (terminals only) supersedes chanta.
    """
    if not any(s.kind == SetKind.SEQUENCE for s in part.sets):
        return None
    sets_ok_yaochuu = all(_set_has_yaochuu(s) for s in part.sets) and is_yaochuuhai(part.pair)
    if not sets_ok_yaochuu:
        return None
    sets_ok_terminal = all(_set_has_terminal(s) for s in part.sets) and is_terminal(part.pair)
    if sets_ok_terminal:
        return Yaku("junchan", "纯全带幺九", 3 if menzen else 2)
    return Yaku("chanta", "混全带幺九", 2 if menzen else 1)


def toitoi(part: StandardPartition) -> Yaku | None:
    """对对和: four triplets / kans, no sequence (§8.2)."""
    if all(s.kind != SetKind.SEQUENCE for s in part.sets):
        return Yaku("toitoi", "对对和", 2)
    return None


def sanankou(part: StandardPartition) -> Yaku | None:
    """三暗刻: three concealed triplets (§8.2).

    Fires at >=3 concealed triplets; the four-triplet case is suuankou and is
    dropped by ``judge_yaku`` in favour of the yakuman.
    """
    if part.concealed_triplet_count >= 3:
        return Yaku("sanankou", "三暗刻", 2)
    return None


def sankantsu(part: StandardPartition) -> Yaku | None:
    """三杠子: three kans (§8.2)."""
    if part.kan_count == 3:
        return Yaku("sankantsu", "三杠子", 2)
    return None


def sanshoku_doukou(part: StandardPartition) -> Yaku | None:
    """三色同刻: same triplet number in all three suits (§8.2)."""
    by_suit: dict[str, set[int]] = {"m": set(), "p": set(), "s": set()}
    for s in _triplets(part.sets):
        if not is_honor(s.base):
            by_suit[tile_suit(s.base)].add(tile_number(s.base))
    if by_suit["m"] & by_suit["p"] & by_suit["s"]:
        return Yaku("sanshoku_doukou", "三色同刻", 2)
    return None


def shousangen(part: StandardPartition) -> Yaku | None:
    """小三元: two dragon triplets + a pair of the third dragon (§8.2)."""
    dragon_triplets = sum(1 for s in _triplets(part.sets) if s.base in _DRAGONS)
    if dragon_triplets == 2 and part.pair in _DRAGONS:
        return Yaku("shousangen", "小三元", 2)
    return None


def yakuhai(part: StandardPartition, ctx: WinContext) -> list[Yaku]:
    """役牌: dragon / round-wind / seat-wind triplets (§8.1).

    A 連風 triplet (round == seat) yields both yaku — 2 han total (§8.8).
    """
    round_tile = _WIND_BASE + ctx.round_wind.value
    seat_tile = _WIND_BASE + ctx.seat_wind.value
    dragon_yaku = {
        31: Yaku("yakuhai_haku", "役牌 白", 1),
        32: Yaku("yakuhai_hatsu", "役牌 发", 1),
        33: Yaku("yakuhai_chun", "役牌 中", 1),
    }
    out: list[Yaku] = []
    for s in _triplets(part.sets):
        t = s.base
        if t in dragon_yaku:
            out.append(dragon_yaku[t])
        if t == round_tile:
            out.append(Yaku("yakuhai_round", "场风", 1))
        if t == seat_tile:
            out.append(Yaku("yakuhai_seat", "自风", 1))
    return out


# ---------------------------------------------------------------------------
# Aggregators
# ---------------------------------------------------------------------------


def standard_normal_yaku(
    part: StandardPartition,
    hand: Hand,
    ctx: WinContext,
) -> list[Yaku]:
    """All normal structural yaku for a standard-form winning hand."""
    menzen = is_menzen(hand)
    out: list[Yaku] = []

    # Whole-hand scans.
    if is_tanyao(hand):
        out.append(Yaku("tanyao", "断幺九", 1))
    if is_honroutou(hand):
        out.append(Yaku("honroutou", "混老头", 2))
    flush = flush_yaku(hand, menzen)
    if flush is not None:
        out.append(flush)

    # Standard-shape yaku.
    for maybe in (
        pinfu(part, hand, ctx),
        peikou(part, hand),
        sanshoku_doujun(part, menzen),
        ittsuu(part, menzen),
        chanta_junchan(part, menzen),
        toitoi(part),
        sanankou(part),
        sankantsu(part),
        sanshoku_doukou(part),
        shousangen(part),
    ):
        if maybe is not None:
            out.append(maybe)
    out.extend(yakuhai(part, ctx))
    return out


def chiitoitsu_normal_yaku(hand: Hand) -> list[Yaku]:
    """All normal yaku for a seven-pairs winning hand (§8.2)."""
    menzen = is_menzen(hand)  # chiitoitsu is always concealed; kept for symmetry
    out: list[Yaku] = [Yaku("chiitoitsu", "七对子", 2)]
    if is_tanyao(hand):
        out.append(Yaku("tanyao", "断幺九", 1))
    if is_honroutou(hand):
        out.append(Yaku("honroutou", "混老头", 2))
    flush = flush_yaku(hand, menzen)
    if flush is not None:
        out.append(flush)
    return out
