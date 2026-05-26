"""Situational yaku — driven by ``WinContext`` flags, not by hand shape.

These are identical across every decomposition of the same win, so
``judge_yaku`` evaluates them once and merges the result into each entry
(docs/rules.md §4, §6, §8.1, §8.5).
"""

from __future__ import annotations

from mahjong_engine.hand import Hand
from mahjong_engine.yaku.context import WinContext, is_menzen
from mahjong_engine.yaku.result import Yaku


def situational_normal(hand: Hand, ctx: WinContext) -> list[Yaku]:
    """Normal (non-yakuman) situational yaku for this win."""
    menzen = is_menzen(hand)
    out: list[Yaku] = []

    if menzen:
        if ctx.is_double_riichi:
            out.append(Yaku("double_riichi", "双立直", 2))
        elif ctx.is_riichi:
            out.append(Yaku("riichi", "立直", 1))
        if ctx.is_ippatsu:
            out.append(Yaku("ippatsu", "一发", 1))
        if ctx.is_tsumo:
            out.append(Yaku("menzen_tsumo", "门前清自摸和", 1))

    if ctx.is_haitei:
        out.append(Yaku("haitei", "海底摸月", 1))
    if ctx.is_houtei:
        out.append(Yaku("houtei", "河底捞鱼", 1))
    if ctx.is_rinshan:
        out.append(Yaku("rinshan", "岭上开花", 1))
    if ctx.is_chankan:
        out.append(Yaku("chankan", "抢杠", 1))

    return out


def situational_yakuman(ctx: WinContext) -> list[Yaku]:
    """Yakuman situational yaku (天和 / 地和)."""
    out: list[Yaku] = []
    if ctx.is_tenhou:
        out.append(Yaku("tenhou", "天和", 0, yakuman_units=1))
    if ctx.is_chiihou:
        out.append(Yaku("chiihou", "地和", 0, yakuman_units=1))
    return out
