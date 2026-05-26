"""Normalize a standard decomposition + exposed melds into a uniform set
view for yaku judgement (M3).

Only the STANDARD form is normalized here.  Chiitoitsu and kokushi are
special-cased directly by the yaku evaluators, since their shape is fixed.

The winning tile is always part of the concealed portion (``hand.counts``):
a ron tile is added to the hand, a tsumo / rinshan tile is drawn into it.
So wait-type and the ron "open triplet" rule are analysed against the
concealed blocks of the decomposition, never against exposed melds.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from mahjong_engine.decompose import BlockKind, Decomposition
from mahjong_engine.hand import Hand, Meld, MeldType
from mahjong_engine.tiles import TILE_COUNT, tile_number


class SetKind(Enum):
    """Kind of a complete set within a standard hand."""

    SEQUENCE = "sequence"  # 顺子
    TRIPLET = "triplet"    # 刻子 (3 tiles)
    KAN = "kan"            # 杠子 (4 tiles, counts as a triplet for most yaku)


class WaitType(Enum):
    """How the winning tile completed the hand."""

    RYANMEN = "ryanmen"  # 两面 — two-sided run wait
    KANCHAN = "kanchan"  # 嵌张 — closed (middle) run wait
    PENCHAN = "penchan"  # 边张 — edge run wait (12_ / _89)
    SHANPON = "shanpon"  # 双碰 — completes one of two pairs into a triplet
    TANKI = "tanki"      # 单骑 — pair wait


@dataclass(frozen=True)
class TileSet:
    """A complete set (mentsu) in a normalized standard partition.

    Attributes:
        kind: SEQUENCE / TRIPLET / KAN.
        tiles: SEQUENCE = 3 ascending tiles; TRIPLET = (t, t, t);
            KAN = (t, t, t, t).
        concealed: True if the set was formed without a call.  An ankan is
            concealed; a triplet completed by ron is treated as open
            (docs/rules.md §8.8) — see ``build_standard_partition``.
        from_meld: True if the set came from an exposed meld / kan.
    """

    kind: SetKind
    tiles: tuple[int, ...]
    concealed: bool
    from_meld: bool

    @property
    def base(self) -> int:
        """Lowest tile (sequence) or the repeated tile (triplet / kan)."""
        return self.tiles[0]


@dataclass(frozen=True)
class StandardPartition:
    """A standard hand normalized for yaku judgement.

    Attributes:
        sets: Exactly four complete sets (concealed blocks + exposed melds).
        pair: The pair (雀头) tile.
        win_tile: The winning tile.
        wait_types: Every wait type the winning tile could represent in this
            decomposition (a tile may be placeable in several blocks).
        concealed_triplet_count: Number of concealed triplets + ankan, after
            the ron "open triplet" adjustment (used by 三暗刻 / 四暗刻).
        kan_count: Number of kan among the four sets (三杠子 / 四杠子).
    """

    sets: tuple[TileSet, ...]
    pair: int
    win_tile: int
    wait_types: frozenset[WaitType]
    concealed_triplet_count: int
    kan_count: int


def iter_all_tiles(hand: Hand) -> list[int]:
    """Flatten every tile in the hand (concealed counts + meld tiles).

    Useful for whole-hand scans (tanyao, honitsu, chinitsu, ...).  Kan melds
    contribute all four tiles, which is harmless for value/suit scans.
    """
    tiles = [t for t in range(TILE_COUNT) for _ in range(hand.counts[t])]
    for m in hand.melds:
        tiles.extend(m.tiles)
    return tiles


def _meld_to_set(m: Meld) -> TileSet:
    if m.type == MeldType.CHI:
        return TileSet(SetKind.SEQUENCE, tuple(sorted(m.tiles)), concealed=False, from_meld=True)
    if m.type == MeldType.PON:
        return TileSet(SetKind.TRIPLET, m.tiles, concealed=False, from_meld=True)
    # All kan variants.
    concealed = m.type == MeldType.KAN_CLOSED
    return TileSet(SetKind.KAN, m.tiles, concealed=concealed, from_meld=True)


def _sequence_wait(low: int, win: int) -> WaitType:
    """Classify a run wait given the sequence's low tile and the win tile."""
    lo = tile_number(low)
    n = tile_number(win)
    if n == lo + 1:
        return WaitType.KANCHAN
    if n == lo:
        # Win is the low end; the held partial is (lo+1, lo+2).
        return WaitType.PENCHAN if lo + 2 == 9 else WaitType.RYANMEN
    # n == lo + 2: win is the high end; the held partial is (lo, lo+1).
    return WaitType.PENCHAN if lo == 1 else WaitType.RYANMEN


def build_standard_partition(
    hand: Hand,
    decomp: Decomposition,
    win_tile: int,
    is_tsumo: bool,
) -> StandardPartition:
    """Normalize a STANDARD decomposition + ``hand.melds`` into a partition.

    Args:
        hand: The winning hand (``counts`` includes the winning tile).
        decomp: A ``DecompForm.STANDARD`` decomposition of ``hand.counts``.
        win_tile: The winning tile code.
        is_tsumo: True for self-draw (affects the ron open-triplet rule).

    Returns:
        A ``StandardPartition`` with favorable interpretations baked in
        (max concealed triplets, all achievable wait types).
    """
    pair = decomp.pair_tile
    assert pair is not None  # guaranteed for STANDARD

    concealed_sets: list[TileSet] = []
    for b in decomp.blocks:
        if b.kind == BlockKind.SHUNTSU:
            concealed_sets.append(TileSet(SetKind.SEQUENCE, b.tiles, True, False))
        elif b.kind == BlockKind.KOUTSU:
            concealed_sets.append(TileSet(SetKind.TRIPLET, b.tiles, True, False))
        # PAIR block is captured via ``pair``.

    sets = tuple(concealed_sets + [_meld_to_set(m) for m in hand.melds])

    # Win-tile placement is analysed only against concealed blocks.
    blocks_with_win = [b for b in decomp.blocks if win_tile in b.tiles]
    waits: set[WaitType] = set()
    for b in blocks_with_win:
        if b.kind == BlockKind.PAIR:
            waits.add(WaitType.TANKI)
        elif b.kind == BlockKind.KOUTSU:
            waits.add(WaitType.SHANPON)
        elif b.kind == BlockKind.SHUNTSU:
            waits.add(_sequence_wait(b.tiles[0], win_tile))

    concealed_triplets = sum(
        1 for s in sets if s.kind in (SetKind.TRIPLET, SetKind.KAN) and s.concealed
    )
    # Ron rule (docs/rules.md §8.8): a triplet completed by the ron tile is an
    # open meld.  Only reduce when the win tile cannot be placed anywhere but a
    # koutsu — otherwise the favorable placement keeps every triplet concealed.
    if not is_tsumo:
        koutsu_placements = any(b.kind == BlockKind.KOUTSU for b in blocks_with_win)
        other_placements = any(b.kind != BlockKind.KOUTSU for b in blocks_with_win)
        if koutsu_placements and not other_placements:
            concealed_triplets -= 1

    kan_count = sum(1 for s in sets if s.kind == SetKind.KAN)

    return StandardPartition(
        sets=sets,
        pair=pair,
        win_tile=win_tile,
        wait_types=frozenset(waits),
        concealed_triplet_count=concealed_triplets,
        kan_count=kan_count,
    )
