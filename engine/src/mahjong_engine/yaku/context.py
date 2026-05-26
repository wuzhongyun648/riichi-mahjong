"""Win context and the menzen (门清) predicate for yaku judgement (M3).

The situational flags below cannot be derived from the hand alone — they
come from the game flow (M5) and are supplied by the caller.  M3 trusts
them as given (docs/rules.md §4, §6).
"""

from __future__ import annotations

from dataclasses import dataclass

from mahjong_engine.game_state import Wind
from mahjong_engine.hand import Hand, MeldType


@dataclass(frozen=True)
class WinContext:
    """Situational context for a single win.

    Attributes:
        round_wind: Current round wind (场风).
        seat_wind: Winner's seat wind (自风).
        is_tsumo: True for self-draw, False for ron.
        is_riichi: Winner had declared riichi (立直).
        is_double_riichi: Winner had declared double riichi (双立直); takes
            the place of ``is_riichi`` and is worth 2 han (docs/rules.md §4.1).
        is_ippatsu: Win within one go-around of an un-interrupted riichi (一发).
        is_haitei: Self-draw of the last live tile (海底摸月).
        is_houtei: Ron on the final discard (河底捞鱼).
        is_rinshan: Self-draw off a kan replacement tile (岭上开花).
        is_chankan: Ron robbing an added kan (抢杠).
        is_tenhou: Dealer wins on the dealt 14 tiles (天和) — yakuman.
        is_chiihou: Non-dealer wins on the first self-draw (地和) — yakuman.
    """

    round_wind: Wind
    seat_wind: Wind
    is_tsumo: bool
    is_riichi: bool = False
    is_double_riichi: bool = False
    is_ippatsu: bool = False
    is_haitei: bool = False
    is_houtei: bool = False
    is_rinshan: bool = False
    is_chankan: bool = False
    is_tenhou: bool = False
    is_chiihou: bool = False


def is_menzen(hand: Hand) -> bool:
    """Return True if the hand is concealed (门清).

    A concealed kan (暗杠 / KAN_CLOSED) keeps the hand concealed; any chi,
    pon, open kan, or added kan breaks it (docs/rules.md §8.8).
    """
    return all(m.type == MeldType.KAN_CLOSED for m in hand.melds)
