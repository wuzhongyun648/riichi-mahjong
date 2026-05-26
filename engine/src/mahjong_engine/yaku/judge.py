"""Top-level yaku judgement entry point (M3).

``judge_yaku`` enumerates every winning decomposition of a hand (via M2's
``all_decompositions``), evaluates structural + situational yaku for each,
and returns one ``YakuDecomp`` per yaku-bearing decomposition.

Tier homogeneity (docs/rules.md §8.8): a true yakuman beats all normal yaku.
So if any decomposition is a yakuman, only yakuman entries are returned and
their normal yaku are dropped; otherwise all entries are normal.  M4 scoring
then picks the highest-scoring entry once fu is known (CLAUDE.md 架构纪律 §5).

Dora / aka / ura and the 13-han kazoe-yakuman determination belong to M4
(docs/rules.md §8.8) and are not handled here.
"""

from __future__ import annotations

from mahjong_engine.decompose import DecompForm, Decomposition, all_decompositions
from mahjong_engine.hand import Hand
from mahjong_engine.tiles import TILE_COUNT, validate_tile
from mahjong_engine.yaku import structural, yakuman
from mahjong_engine.yaku.context import WinContext
from mahjong_engine.yaku.partition import build_standard_partition
from mahjong_engine.yaku.result import Yaku, YakuDecomp
from mahjong_engine.yaku.situational import situational_normal, situational_yakuman

_MAX_YAKUMAN_UNITS = 6  # docs/rules.md §8.7


def _combine(
    decomp_form_normal: list[Yaku],
    decomp_form_yakuman: list[Yaku],
    sit_normal: list[Yaku],
    sit_yakuman: list[Yaku],
    decomp: Decomposition,
) -> YakuDecomp | None:
    """Merge per-decomposition + situational yaku into one entry.

    Returns ``None`` for a yakuless (non-winning) decomposition.
    """
    all_yakuman = decomp_form_yakuman + sit_yakuman
    if all_yakuman:
        units = min(_MAX_YAKUMAN_UNITS, sum(y.yakuman_units for y in all_yakuman))
        return YakuDecomp(
            yaku=tuple(all_yakuman),
            han=0,
            yakuman_units=units,
            decomposition=decomp,
        )
    normal = decomp_form_normal + sit_normal
    if not normal:
        return None
    return YakuDecomp(
        yaku=tuple(normal),
        han=sum(y.han for y in normal),
        yakuman_units=0,
        decomposition=decomp,
    )


def judge_yaku(hand: Hand, win_tile: int, ctx: WinContext) -> list[YakuDecomp]:
    """Judge all yaku for a winning hand.

    Args:
        hand: The winning hand — ``hand.counts`` includes the winning tile,
            ``hand.melds`` holds the exposed melds / concealed kans.
        win_tile: The winning tile code (0-33).
        ctx: Situational context (winds, tsumo/ron, riichi, ...).

    Returns:
        A tier-homogeneous list (all yakuman, or all normal) with one entry
        per yaku-bearing decomposition.  Empty if the hand is complete but
        yakuless (役なし — cannot win).

    Raises:
        ValueError: If ``win_tile`` is out of range / not in the hand, or the
            hand is not a complete winning shape.
    """
    validate_tile(win_tile)
    if len(hand.counts) != TILE_COUNT:
        raise ValueError(f"counts must have length {TILE_COUNT}, got {len(hand.counts)}")
    if hand.counts[win_tile] < 1:
        raise ValueError(f"win_tile {win_tile} is not present in the hand")

    decomps = all_decompositions(hand.counts)
    if not decomps:
        raise ValueError("hand is not a complete winning shape")

    sit_normal = situational_normal(hand, ctx)
    sit_yakuman = situational_yakuman(ctx)

    results: list[YakuDecomp] = []
    for decomp in decomps:
        if decomp.form == DecompForm.STANDARD:
            part = build_standard_partition(hand, decomp, win_tile, ctx.is_tsumo)
            form_normal = structural.standard_normal_yaku(part, hand, ctx)
            form_yakuman = yakuman.standard_yakuman(part, hand, win_tile)
        elif decomp.form == DecompForm.CHIITOITSU:
            form_normal = structural.chiitoitsu_normal_yaku(hand)
            form_yakuman = yakuman.chiitoitsu_yakuman(hand)
        else:  # KOKUSHI — yakuman only
            form_normal = []
            form_yakuman = [yakuman.kokushi(decomp, win_tile)]

        entry = _combine(form_normal, form_yakuman, sit_normal, sit_yakuman, decomp)
        if entry is not None:
            results.append(entry)

    # Tier homogeneity: yakuman beats normal yaku entirely.
    if any(e.is_yakuman for e in results):
        results = [e for e in results if e.is_yakuman]
    return results


def has_any_yaku(hand: Hand, win_tile: int, ctx: WinContext) -> bool:
    """Return True if the hand has at least one yaku (i.e. can legally win).

    Convenience wrapper for M5 ron-validity / furiten checks.
    """
    return bool(judge_yaku(hand, win_tile, ctx))
