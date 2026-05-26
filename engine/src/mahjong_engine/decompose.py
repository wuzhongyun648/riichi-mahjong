"""Hand decomposition: enumerate all valid winning factorings of a hand.

Three winning forms are supported (docs/rules.md §8):

  1. Standard:    4 mentsu (sequences/triplets) + 1 jantou (head)
  2. Chiitoitsu:  7 distinct pairs (14 tiles, no exposed melds)
  3. Kokushi:     13 yaochuuhai + 1 duplicate (14 tiles, no exposed melds)

All functions take a concealed-hand ``counts`` array of length 34 (see
``docs/tile-encoding.md``).  Exposed melds are NOT considered here — the
caller (typically ``tenpai.shanten`` or M3 yaku code) is responsible for
combining the returned ``Decomposition`` with ``Hand.melds``.

Algorithm (standard form):
    Enumerate every possible jantou tile ``i`` with ``counts[i] >= 2``.
    After removing the pair, decompose each suit (manzu/pinzu/souzu) and
    the honor segment independently via DFS:
        - Suited: try triplet at the leftmost non-zero, or sequence
                  (idx, idx+1, idx+2); recurse.
        - Honors: triplets only (no sequences across honors).
    The Cartesian product of per-segment decompositions gives every
    complete factoring.  Duplicates from different DFS orders are
    deduplicated via a canonical block-set key.

Complexity:
    For realistic 14-tile hands the search yields well under 100 leaf
    decompositions; with 34 possible jantou positions the total work is
    a few thousand DFS nodes — comfortably sub-millisecond in CPython.

References:
    - MahjongRepository/mahjong (Agari / Shanten):
      https://github.com/MahjongRepository/mahjong/blob/master/mahjong/agari.py
    - Takizawa, "Efficiency of Mahjong Hand Evaluation" (2004).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from itertools import product

from mahjong_engine.tiles import (
    HONOR_END,
    HONOR_START,
    TILE_COUNT,
    is_yaochuuhai,
)

# ---------------------------------------------------------------------------
# Block / Decomposition data structures
# ---------------------------------------------------------------------------


class BlockKind(Enum):
    """Kind of an atomic block in a hand decomposition."""

    SHUNTSU = "shuntsu"            # 顺子 (sequence)
    KOUTSU = "koutsu"              # 刻子 (triplet)
    PAIR = "pair"                  # 雀头 in standard / kokushi
    PAIR_CHIITOI = "pair_chiitoi"  # one of the seven pairs in chiitoitsu


@dataclass(frozen=True)
class Block:
    """An atomic block within a complete hand decomposition.

    Attributes:
        kind: SHUNTSU, KOUTSU, PAIR, or PAIR_CHIITOI.
        tiles: Tile codes belonging to this block.
            - SHUNTSU: three strictly consecutive same-suit tiles (a, a+1, a+2).
            - KOUTSU:  three copies of the same tile (a, a, a).
            - PAIR / PAIR_CHIITOI: two copies of the same tile (a, a).
    """

    kind: BlockKind
    tiles: tuple[int, ...]


class DecompForm(Enum):
    """Top-level winning form of a decomposition."""

    STANDARD = "standard"
    CHIITOITSU = "chiitoitsu"
    KOKUSHI = "kokushi"


@dataclass(frozen=True)
class Decomposition:
    """A single complete factoring of a hand's concealed portion.

    For ``form == STANDARD`` the ``blocks`` tuple contains exactly
    ``(4 - n_melds)`` mentsu blocks followed by one PAIR block.

    For ``form == CHIITOITSU`` the tuple contains exactly 7
    ``PAIR_CHIITOI`` blocks and ``pair_tile`` is ``None``.

    For ``form == KOKUSHI`` the tuple contains exactly one ``PAIR`` block
    (the duplicated yaochuu) and ``pair_tile`` is set to that tile.  The
    twelve singleton yaochuuhai are NOT listed as blocks — the
    ``KOKUSHI`` form implicitly fixes them.
    """

    form: DecompForm
    blocks: tuple[Block, ...]
    pair_tile: int | None


# ---------------------------------------------------------------------------
# Per-segment DFS for the standard form
# ---------------------------------------------------------------------------

# Manzu / pinzu / souzu as three independent suited ranges.  Honors are
# handled separately by ``_honor_full_decomp`` since they cannot form
# sequences.
_SUIT_RANGES: tuple[tuple[int, int], ...] = (
    (0, 8),    # manzu  1m-9m
    (9, 17),   # pinzu  1p-9p
    (18, 26),  # souzu  1s-9s
)


def _suit_full_decomp(
    work: list[int],
    start: int,
    end: int,
    idx: int,
) -> list[tuple[Block, ...]]:
    """All full mentsu decompositions of a suited range [start, end].

    Returns a list of mentsu tuples (each Block is SHUNTSU or KOUTSU).
    Empty if the range cannot be fully decomposed.

    The ``work`` array is mutated during recursion and restored on backtrack.
    """
    # Skip leading zeros.
    while idx <= end and work[idx] == 0:
        idx += 1
    if idx > end:
        return [()]

    out: list[tuple[Block, ...]] = []

    # Branch 1: take a triplet at idx.
    if work[idx] >= 3:
        work[idx] -= 3
        for sub in _suit_full_decomp(work, start, end, idx):
            out.append((Block(BlockKind.KOUTSU, (idx, idx, idx)), *sub))
        work[idx] += 3

    # Branch 2: take a sequence (idx, idx+1, idx+2).
    if idx + 2 <= end and work[idx] >= 1 and work[idx + 1] >= 1 and work[idx + 2] >= 1:
        work[idx] -= 1
        work[idx + 1] -= 1
        work[idx + 2] -= 1
        for sub in _suit_full_decomp(work, start, end, idx):
            out.append((Block(BlockKind.SHUNTSU, (idx, idx + 1, idx + 2)), *sub))
        work[idx] += 1
        work[idx + 1] += 1
        work[idx + 2] += 1

    return out


def _honor_full_decomp(work: list[int]) -> tuple[Block, ...] | None:
    """Honors only form koutsu — every honor count must be 0 or 3."""
    blocks: list[Block] = []
    for t in range(HONOR_START, HONOR_END + 1):
        c = work[t]
        if c == 0:
            continue
        if c == 3:
            blocks.append(Block(BlockKind.KOUTSU, (t, t, t)))
        else:
            return None
    return tuple(blocks)


# ---------------------------------------------------------------------------
# Public API: standard
# ---------------------------------------------------------------------------


def _validate_counts(counts: Sequence[int]) -> None:
    if len(counts) != TILE_COUNT:
        raise ValueError(f"counts must have length {TILE_COUNT}, got {len(counts)}")
    for i, c in enumerate(counts):
        if not 0 <= c <= 4:
            raise ValueError(f"counts[{i}] = {c} out of range 0..4")


def standard_decompositions(counts: Sequence[int]) -> list[Decomposition]:
    """Enumerate every (n mentsu + 1 pair) decomposition of ``counts``.

    The number of mentsu is determined by ``sum(counts)``: a valid
    decomposable hand must satisfy ``sum(counts) % 3 == 2`` and yields
    ``(sum(counts) - 2) // 3`` mentsu plus one pair.

    Exposed melds (副露) are tracked separately on ``Hand.melds`` and are
    NOT included in the returned blocks.  The caller is responsible for
    counting expected mentsu accordingly.

    Args:
        counts: Length-34 concealed-hand count array.

    Returns:
        List of all distinct decompositions.  Empty if the hand cannot
        form a standard winning shape.

    Raises:
        ValueError: If ``counts`` has the wrong length or invalid values.
    """
    _validate_counts(counts)
    s = sum(counts)
    if s % 3 != 2:
        return []
    expected_mentsu = (s - 2) // 3

    work = list(counts)
    results: list[Decomposition] = []
    seen_keys: set[tuple[int, tuple[tuple[str, tuple[int, ...]], ...]]] = set()

    for pair_tile in range(TILE_COUNT):
        if work[pair_tile] < 2:
            continue
        work[pair_tile] -= 2

        honor_blocks = _honor_full_decomp(work)
        if honor_blocks is None:
            work[pair_tile] += 2
            continue

        suit_decomps: list[list[tuple[Block, ...]]] = []
        for lo, hi in _SUIT_RANGES:
            decomps = _suit_full_decomp(work, lo, hi, lo)
            if not decomps:
                suit_decomps = []
                break
            suit_decomps.append(decomps)

        if suit_decomps:
            for combo in product(*suit_decomps):
                all_blocks: list[Block] = list(honor_blocks)
                for sub in combo:
                    all_blocks.extend(sub)
                if len(all_blocks) != expected_mentsu:
                    continue
                pair_block = Block(BlockKind.PAIR, (pair_tile, pair_tile))
                key = (
                    pair_tile,
                    tuple(sorted((b.kind.value, tuple(b.tiles)) for b in all_blocks)),
                )
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                results.append(
                    Decomposition(
                        form=DecompForm.STANDARD,
                        blocks=tuple([*all_blocks, pair_block]),
                        pair_tile=pair_tile,
                    )
                )

        work[pair_tile] += 2

    return results


# ---------------------------------------------------------------------------
# Public API: chiitoitsu
# ---------------------------------------------------------------------------


def chiitoitsu_decomposition(counts: Sequence[int]) -> Decomposition | None:
    """Return a chiitoitsu decomposition iff the hand is a complete 七对子.

    Requires exactly 14 tiles forming seven *distinct* pairs.  Four-of-a-kind
    counts as a single pair (not two) — such a hand is NOT chiitoitsu.

    Args:
        counts: Length-34 concealed-hand count array.

    Returns:
        ``Decomposition`` with ``form=CHIITOITSU`` and 7 ``PAIR_CHIITOI``
        blocks in ascending tile order, or ``None``.

    Raises:
        ValueError: If ``counts`` has the wrong length or invalid values.
    """
    _validate_counts(counts)
    if sum(counts) != 14:
        return None
    pairs: list[int] = []
    for t in range(TILE_COUNT):
        c = counts[t]
        if c == 0:
            continue
        if c == 2:
            pairs.append(t)
        else:
            return None
    if len(pairs) != 7:
        return None
    blocks = tuple(Block(BlockKind.PAIR_CHIITOI, (t, t)) for t in pairs)
    return Decomposition(form=DecompForm.CHIITOITSU, blocks=blocks, pair_tile=None)


# ---------------------------------------------------------------------------
# Public API: kokushi
# ---------------------------------------------------------------------------

_YAOCHUU_TILES: tuple[int, ...] = tuple(t for t in range(TILE_COUNT) if is_yaochuuhai(t))
# Sanity: exactly 13 yaochuuhai tiles (1m, 9m, 1p, 9p, 1s, 9s, 27..33).
assert len(_YAOCHUU_TILES) == 13


def kokushi_decomposition(counts: Sequence[int]) -> Decomposition | None:
    """Return a kokushi musou decomposition for a complete 14-tile hand.

    Requires all 13 yaochuuhai with one of them doubled and no other tiles.
    Distinguishing 国士十三面 vs 普通国士 is NOT done here — it depends on
    the winning tile and is decided by M3 yaku judgement.

    Args:
        counts: Length-34 concealed-hand count array.

    Returns:
        ``Decomposition`` with ``form=KOKUSHI`` and a single PAIR block for
        the duplicated yaochuu, or ``None``.

    Raises:
        ValueError: If ``counts`` has the wrong length or invalid values.
    """
    _validate_counts(counts)
    if sum(counts) != 14:
        return None
    pair_tile: int | None = None
    yaochuu_set = set(_YAOCHUU_TILES)
    for t in range(TILE_COUNT):
        c = counts[t]
        if t in yaochuu_set:
            if c == 1:
                continue
            if c == 2:
                if pair_tile is not None:
                    return None
                pair_tile = t
            else:
                return None
        else:
            if c != 0:
                return None
    if pair_tile is None:
        return None
    return Decomposition(
        form=DecompForm.KOKUSHI,
        blocks=(Block(BlockKind.PAIR, (pair_tile, pair_tile)),),
        pair_tile=pair_tile,
    )


# ---------------------------------------------------------------------------
# Public API: union
# ---------------------------------------------------------------------------


def all_decompositions(counts: Sequence[int]) -> list[Decomposition]:
    """Return every complete-hand decomposition across all three forms.

    Useful for M3 yaku judgement, which evaluates each decomposition and
    picks the highest-scoring one (see CLAUDE.md "架构纪律 §5").
    """
    out: list[Decomposition] = list(standard_decompositions(counts))
    chi = chiitoitsu_decomposition(counts)
    if chi is not None:
        out.append(chi)
    kok = kokushi_decomposition(counts)
    if kok is not None:
        out.append(kok)
    return out


def is_complete_hand(counts: Sequence[int], n_melds: int = 0) -> bool:
    """Return True iff ``counts`` (combined with ``n_melds`` exposed melds)
    is a complete winning hand under any of the three forms.

    Chiitoitsu / kokushi require ``n_melds == 0``.
    """
    if standard_decompositions(counts):
        return True
    if n_melds == 0:
        if chiitoitsu_decomposition(counts) is not None:
            return True
        if kokushi_decomposition(counts) is not None:
            return True
    return False
