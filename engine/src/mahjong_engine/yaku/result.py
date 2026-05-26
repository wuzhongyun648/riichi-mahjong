"""Yaku result data structures (M3).

A ``YakuDecomp`` holds the yaku judged for one specific decomposition of a
winning hand.  ``judge_yaku`` returns a *tier-homogeneous* list of these
(either all yakuman, or all normal); M4 scoring picks the highest-scoring
entry once fu is known.  See docs/rules.md §8 / §8.8 and CLAUDE.md
"架构纪律 §5".

Dora / aka / ura are NOT yaku and are never counted here — they are added
in M4 scoring (docs/rules.md §8.8).
"""

from __future__ import annotations

from dataclasses import dataclass

from mahjong_engine.decompose import Decomposition


@dataclass(frozen=True)
class Yaku:
    """A single yaku hit.

    Attributes:
        id: Stable English identifier, e.g. ``"pinfu"`` / ``"riichi"``.
        name: Display name (Chinese), e.g. ``"平和"``.
        han: Han contributed by this yaku (after kuisagari).  Always ``0``
            for yakuman entries — yakuman use ``yakuman_units`` instead.
        yakuman_units: ``0`` for a normal yaku, ``1`` for a single yakuman,
            ``2`` for a double yakuman.
    """

    id: str
    name: str
    han: int
    yakuman_units: int = 0


@dataclass(frozen=True)
class YakuDecomp:
    """Yaku judgement for one decomposition of a winning hand.

    Attributes:
        yaku: The yaku that apply to this decomposition.  Either all normal
            (``yakuman_units == 0``) or all yakuman — never mixed.
        han: Sum of normal-yaku han (excludes dora; ``0`` for yakuman).
        yakuman_units: Total yakuman units (``0`` if not a yakuman hand),
            capped at 6 (docs/rules.md §8.7).
        decomposition: The decomposition this judgement was computed for,
            kept so M4 can compute fu / pick the best-scoring decomposition.
    """

    yaku: tuple[Yaku, ...]
    han: int
    yakuman_units: int
    decomposition: Decomposition

    @property
    def is_yakuman(self) -> bool:
        """True if this is a yakuman judgement."""
        return self.yakuman_units > 0

    @property
    def has_yaku(self) -> bool:
        """True if at least one yaku applies (i.e. the hand can win)."""
        return bool(self.yaku)
