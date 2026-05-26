"""Tenpai detection, shanten count, and winning-tile enumeration.

The shanten value is the minimum number of tile swaps needed to reach a
complete hand.  Conventions:

    shanten == -1  →  hand is already complete (和牌).
    shanten ==  0  →  hand is tenpai (one tile away).
    shanten ==  n  →  n-shanten (n + 1 tile swaps away from completion).

Input contract:

    ``sum(counts) + 3 * n_melds`` must be 13 (post-discard / waiting phase)
    or 14 (post-draw / completion phase).  ``is_tenpai`` and
    ``winning_tiles`` further require the 13-tile phase (``% 3 == 1``)
    since they describe a waiting hand.

Algorithm:

    Standard shanten: depth-first enumeration of (mentsu, taatsu, has_pair)
    configurations over the 34-tile count vector, applying the classical
    Hori formula::

        shanten = 8 - 2 · m_total - min(t, 4 - m_total) - (1 if has_pair else 0)

    where ``m_total = m_concealed + n_melds`` and ``t`` is the number of
    taatsu (partial sets: pairs treated as 双碰, ryanmen/penchan/kanchan
    proto-runs).

    Chiitoitsu shanten (n_melds == 0 only)::

        6 - pairs + max(0, 7 - unique_kinds)

    Kokushi shanten (n_melds == 0 only)::

        13 - distinct_yaochuu - (1 if any yaochuu pair else 0)

    Final shanten = min(standard, chiitoitsu, kokushi).

References:
    - https://github.com/MahjongRepository/mahjong/blob/master/mahjong/shanten.py
    - Tomohxx, "Mahjong Algorithm Book"
      (https://tomohxx.github.io/mahjong-algorithm-book/).
"""

from __future__ import annotations

from collections.abc import Sequence

from mahjong_engine.decompose import is_complete_hand
from mahjong_engine.hand import Meld
from mahjong_engine.tiles import HONOR_START, TILE_COUNT, is_yaochuuhai

_YAOCHUU_TILES: tuple[int, ...] = tuple(t for t in range(TILE_COUNT) if is_yaochuuhai(t))
_INF: int = 99


# ---------------------------------------------------------------------------
# Standard-form shanten
# ---------------------------------------------------------------------------


def _standard_shanten(counts: Sequence[int], n_melds: int) -> int:
    """Minimum shanten under the standard 4-mentsu + 1-head form.

    Uses depth-first search over the 34-tile count vector to enumerate
    every reachable ``(m, t, has_pair)`` triple, then applies the Hori
    formula and returns the minimum.
    """
    work = list(counts)
    best = [_INF]
    
    four_copies_mask = 0
    number_jidahai = 0
    for i, c in enumerate(counts):
        if c == 4:
            four_copies_mask |= (1 << i)
            if i >= HONOR_START:
                number_jidahai += 1
                
    if number_jidahai > 0 and (sum(counts) + 3 * n_melds) % 3 == 2:
        number_jidahai -= 1

    def evaluate(m: int, t: int, has_pair: bool, isolated_mask: int) -> None:
        m_total = m + n_melds
        cap = max(0, 4 - m_total)
        t_eff = min(t, cap)
        s = 8 - 2 * m_total - t_eff - (1 if has_pair else 0)
        
        if not has_pair and isolated_mask and (isolated_mask & ~four_copies_mask) == 0:
            s += 1
            
        if s != -1 and s < number_jidahai:
            s = number_jidahai
            
        if s < best[0]:
            best[0] = s

    def dfs(idx: int, m: int, t: int, has_pair: bool, isolated_mask: int) -> None:
        # Advance to the next non-zero position.
        while idx < TILE_COUNT and work[idx] == 0:
            idx += 1
        if idx == TILE_COUNT:
            evaluate(m, t, has_pair, isolated_mask)
            return

        # Cap: at most 4 mentsu + 1 head; further mentsu/taatsu are wasted.
        if m + n_melds + t >= 5:
            evaluate(m, t, has_pair, isolated_mask)
            return

        c = work[idx]
        is_suited = idx < HONOR_START
        in_pos = (idx % 9) if is_suited else -1

        # 1. Triplet (koutsu).
        if c >= 3:
            work[idx] -= 3
            dfs(idx, m + 1, t, has_pair, isolated_mask)
            work[idx] += 3

        # 2. Sequence (suited only, positions 0..6 within a suit).
        if is_suited and in_pos <= 6 and c >= 1 and work[idx + 1] >= 1 and work[idx + 2] >= 1:
            work[idx] -= 1
            work[idx + 1] -= 1
            work[idx + 2] -= 1
            dfs(idx, m + 1, t, has_pair, isolated_mask)
            work[idx] += 1
            work[idx + 1] += 1
            work[idx + 2] += 1

        # 3. Pair allocated as the jantou (only one allowed).
        if c >= 2 and not has_pair:
            work[idx] -= 2
            dfs(idx, m, t, True, isolated_mask)
            work[idx] += 2

        # 4. Pair as a taatsu (双碰).
        if c >= 2 and counts[idx] < 4:
            work[idx] -= 2
            dfs(idx, m, t + 1, has_pair, isolated_mask)
            work[idx] += 2

        # 5. Ryanmen / penchan partial run (idx, idx+1).
        if is_suited and in_pos <= 7 and c >= 1 and work[idx + 1] >= 1:
            work[idx] -= 1
            work[idx + 1] -= 1
            dfs(idx, m, t + 1, has_pair, isolated_mask)
            work[idx] += 1
            work[idx + 1] += 1

        # 6. Kanchan partial run (idx, idx+2).
        if is_suited and in_pos <= 6 and c >= 1 and work[idx + 2] >= 1:
            work[idx] -= 1
            work[idx + 2] -= 1
            dfs(idx, m, t + 1, has_pair, isolated_mask)
            work[idx] += 1
            work[idx + 2] += 1

        # 7. Drop one tile as isolated and continue.
        work[idx] -= 1
        dfs(idx, m, t, has_pair, isolated_mask | (1 << idx))
        work[idx] += 1

    dfs(0, 0, 0, False, 0)
    return best[0]


# ---------------------------------------------------------------------------
# Chiitoitsu / kokushi shanten
# ---------------------------------------------------------------------------


def _chiitoi_shanten(counts: Sequence[int]) -> int:
    """Chiitoitsu shanten: ``6 - pairs + max(0, 7 - unique_kinds)``.

    Caller must guarantee no exposed melds (chiitoi is only valid in a
    fully concealed hand).
    """
    pairs = 0
    unique = 0
    for c in counts:
        if c >= 1:
            unique += 1
        if c >= 2:
            pairs += 1
    return 6 - pairs + max(0, 7 - unique)


def _kokushi_shanten(counts: Sequence[int]) -> int:
    """Kokushi musou shanten:
    ``13 - distinct_yaochuu - (1 if any yaochuu pair else 0)``.

    Caller must guarantee no exposed melds (kokushi requires a fully
    concealed hand).
    """
    distinct = 0
    has_pair = False
    for t in _YAOCHUU_TILES:
        c = counts[t]
        if c >= 1:
            distinct += 1
        if c >= 2:
            has_pair = True
    return 13 - distinct - (1 if has_pair else 0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _check_input(counts: Sequence[int], melds: tuple[Meld, ...]) -> int:
    """Validate length and tile-count budget, return ``n_melds``."""
    if len(counts) != TILE_COUNT:
        raise ValueError(f"counts must have length {TILE_COUNT}, got {len(counts)}")
    for i, c in enumerate(counts):
        if not 0 <= c <= 4:
            raise ValueError(f"counts[{i}] = {c} out of range 0..4")
    n_melds = len(melds)
    total = sum(counts) + 3 * n_melds
    if total not in (13, 14):
        raise ValueError(
            f"hand has {total} tiles (counts + 3*melds), expected 13 or 14"
        )
    return n_melds


def shanten(counts: Sequence[int], melds: tuple[Meld, ...] = ()) -> int:
    """Compute the shanten count of a concealed hand.

    Accepts both the 13-tile (post-discard / waiting) and 14-tile
    (post-draw / completion) phases.

    Args:
        counts: Length-34 concealed-hand count array.
        melds: Tuple of exposed melds (副露 + 暗杠).  Chiitoi/kokushi
            shanten branches are disabled when ``melds`` is non-empty.

    Returns:
        ``-1`` if complete (only possible in the 14-tile phase);
        ``0`` if tenpai; positive integer for the number of swaps needed.

    Raises:
        ValueError: On invalid ``counts`` length or tile budget.
    """
    n_melds = _check_input(counts, melds)
    s_std = _standard_shanten(counts, n_melds)
    if n_melds == 0:
        s_chi = _chiitoi_shanten(counts)
        s_kok = _kokushi_shanten(counts)
        return min(s_std, s_chi, s_kok)
    return s_std


def is_tenpai(counts: Sequence[int], melds: tuple[Meld, ...] = ()) -> bool:
    """Return True iff the hand is tenpai (one tile away from completion).

    Requires the 13-tile (post-discard) phase: ``sum(counts) + 3*len(melds)
    == 13``.

    Raises:
        ValueError: If the hand is not in the 13-tile phase or otherwise
            invalid.
    """
    n_melds = _check_input(counts, melds)
    if sum(counts) + 3 * n_melds != 13:
        raise ValueError(
            "is_tenpai requires a post-discard hand "
            "(sum(counts) + 3*len(melds) == 13)"
        )
    return shanten(counts, melds) == 0


def winning_tiles(counts: Sequence[int], melds: tuple[Meld, ...] = ()) -> list[int]:
    """Return all tiles that would complete the hand, in ascending order.

    Requires the 13-tile (post-discard) phase.  Returns ``[]`` if the hand
    is not tenpai.

    Args:
        counts: Length-34 concealed-hand count array.
        melds: Tuple of exposed melds.

    Returns:
        Sorted list of tile codes ``t`` such that adding one copy of ``t``
        to ``counts`` produces a complete winning hand.

    Raises:
        ValueError: If the hand is not in the 13-tile phase or otherwise
            invalid.
    """
    n_melds = _check_input(counts, melds)
    if sum(counts) + 3 * n_melds != 13:
        raise ValueError(
            "winning_tiles requires a post-discard hand "
            "(sum(counts) + 3*len(melds) == 13)"
        )

    # Cheap early exit: if not tenpai, nothing waits.
    if _standard_shanten(counts, n_melds) > 0 and (
        n_melds > 0
        or (_chiitoi_shanten(counts) > 0 and _kokushi_shanten(counts) > 0)
    ):
        return []

    work = list(counts)
    waits: list[int] = []
    for t in range(TILE_COUNT):
        if work[t] >= 4:
            continue
        work[t] += 1
        if is_complete_hand(work, n_melds):
            waits.append(t)
        work[t] -= 1
    return waits
