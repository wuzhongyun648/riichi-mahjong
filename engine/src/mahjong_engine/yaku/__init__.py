"""Yaku detection (M3).

Public API:
    judge_yaku(hand, win_tile, ctx) -> list[YakuDecomp]
    has_any_yaku(hand, win_tile, ctx) -> bool

See docs/rules.md §8 and docs/dev/m3-tasks.md.
"""

from mahjong_engine.yaku.context import WinContext, is_menzen
from mahjong_engine.yaku.judge import has_any_yaku, judge_yaku
from mahjong_engine.yaku.result import Yaku, YakuDecomp

__all__ = [
    "WinContext",
    "Yaku",
    "YakuDecomp",
    "has_any_yaku",
    "is_menzen",
    "judge_yaku",
]
