"""Golden-dataset yaku tests transcribed from MahjongRepository/mahjong.

Source: https://github.com/MahjongRepository/mahjong
  tests/hand_calculating/tests_yaku_calculation.py
  tests/hand_calculating/tests_yakuman_calculation.py

Their tile notation: per-suit digit strings (man/pin/sou) + ``honors`` digits
mapped 1-7 -> 东南西北白发中.  ``estimate_hand_value(tiles, win_tile, ...)``
returns ``result.han`` (a single yakuman = 13 han, double = 26) and
``result.yaku``.  We transcribe each full-hand case, translate to our
encoding, and reverse-verify the yaku our ``judge_yaku`` produces.

Rule mapping to 雀魂段位场 (docs/rules.md):
  * MahjongRepository default has no seat/round wind set, so honor-wind
    triplets are guests (no yakuhai).  We pick ``rw``/``sw`` per case to
    reproduce that (or to assert 役牌 where the case is about it).
  * Their yakuman han 13/26 -> our ``yakuman_units`` 1/2.
  * Cases involving dora / fu / scoring are out of M3 scope and skipped.
  * Some all-triplet yakuman hands incidentally also satisfy suuankou; for
    those we assert the *target* yaku is present rather than exact units.
"""

from __future__ import annotations

import pytest

from mahjong_engine.game_state import Wind
from mahjong_engine.hand import Hand, Meld, MeldType
from mahjong_engine.tiles import make_counts
from mahjong_engine.yaku import WinContext, judge_yaku

_HONOR = {"1": 27, "2": 28, "3": 29, "4": 30, "5": 31, "6": 32, "7": 33}
_SUIT_OFFSET = {"man": 0, "pin": 9, "sou": 18}


def _codes(man: str = "", pin: str = "", sou: str = "", honors: str = "") -> list[int]:
    out: list[int] = []
    for suit, digits in (("man", man), ("pin", pin), ("sou", sou)):
        out.extend(_SUIT_OFFSET[suit] + (int(ch) - 1) for ch in digits)
    out.extend(_HONOR[ch] for ch in honors)
    return out


def gmeld(kind: MeldType, man: str = "", pin: str = "", sou: str = "", honors: str = "") -> Meld:
    tiles = tuple(_codes(man, pin, sou, honors))
    return Meld(type=kind, tiles=tiles, called_from=1, called_tile=tiles[0])


def _hand(full: dict, melds: tuple[Meld, ...]) -> Hand:
    """Build our concealed Hand: full MR tile list minus the meld tiles."""
    counts = make_counts(_codes(**full))
    for m in melds:
        for t in m.tiles:
            counts[t] -= 1
    return Hand(counts=tuple(counts), melds=melds)


CHI, PON = MeldType.CHI, MeldType.PON
KAN_O, KAN_A, KAN_ADD = MeldType.KAN_OPEN, MeldType.KAN_CLOSED, MeldType.KAN_ADDED


# Each case: (id, full_tiles, win, melds, ctx_kwargs, present_yaku, max_han, units)
#   max_han / units = None means "don't assert".
_C = dict
CASES: list[tuple] = [
    # ---- normal yaku (tests_yaku_calculation.py) ----
    ("tanyao_riichi_closed", _C(man="234567", sou="234567", pin="22"), _C(man="7"), (),
     _C(is_riichi=True), ["tanyao", "pinfu", "riichi"], 3, 0),
    ("tanyao_open", _C(man="234567", sou="234567", pin="22"), _C(man="7"), (gmeld(CHI, sou="234"),),
     _C(), ["tanyao"], 1, 0),
    ("pinfu_closed", _C(sou="123456", man="123456", pin="55"), _C(man="6"), (),
     _C(), ["pinfu"], 1, 0),
    ("iipeikou", _C(sou="112233", man="333", pin="12344"), _C(man="3"), (),
     _C(), ["iipeikou"], None, 0),
    ("ryanpeikou", _C(sou="112233", man="33", pin="223344"), _C(pin="3"), (),
     _C(), ["ryanpeikou"], 3, 0),
    ("sanshoku_closed", _C(sou="123456", man="12399", pin="123"), _C(man="2"), (),
     _C(), ["sanshoku"], 2, 0),
    ("sanshoku_open", _C(sou="123456", man="12399", pin="123"), _C(man="2"),
     (gmeld(CHI, sou="123"),), _C(), ["sanshoku"], 1, 0),
    ("sanshoku_douko", _C(sou="222", man="222", pin="22245699"), _C(pin="9"),
     (gmeld(PON, sou="222"),), _C(), ["sanshoku_doukou"], 2, 0),
    ("toitoi", _C(sou="111333", man="333", pin="44555"), _C(pin="5"),
     (gmeld(PON, sou="111"), gmeld(PON, sou="333")), _C(), ["toitoi"], 2, 0),
    ("sankantsu", _C(sou="11113333", man="123", pin="446666"), _C(man="3"),
     (gmeld(KAN_ADD, sou="1111"), gmeld(KAN_O, sou="3333"), gmeld(KAN_O, pin="6666")),
     _C(), ["sankantsu"], None, 0),
    ("honroto", _C(sou="111999", man="111", honors="11222"), _C(honors="2"),
     (gmeld(PON, sou="111"),), _C(rw=Wind.WEST, sw=Wind.NORTH), ["honroutou", "toitoi"], 4, 0),
    ("sanankou_tsumo", _C(sou="123444", man="333", pin="44555"), _C(pin="5"),
     (gmeld(CHI, sou="123"),), _C(is_tsumo=True), ["sanankou"], 2, 0),
    ("shosangen", _C(sou="123", man="345", honors="55666777"), _C(honors="7"), (),
     _C(), ["shousangen", "yakuhai_hatsu", "yakuhai_chun"], 4, 0),
    ("chanta_closed", _C(sou="123", man="123789", honors="22333"), _C(honors="3"), (),
     _C(rw=Wind.EAST, sw=Wind.NORTH), ["chanta"], 2, 0),
    ("chanta_open", _C(sou="123", man="123789", honors="22333"), _C(honors="3"),
     (gmeld(CHI, sou="123"),), _C(rw=Wind.EAST, sw=Wind.NORTH), ["chanta"], 1, 0),
    ("junchan_closed", _C(sou="789", man="123789", pin="12399"), _C(man="2"), (),
     _C(), ["junchan"], 3, 0),
    ("junchan_open", _C(sou="789", man="123789", pin="12399"), _C(man="2"),
     (gmeld(CHI, sou="789"),), _C(), ["junchan"], 2, 0),
    ("honitsu_closed", _C(man="123455667", honors="11122"), _C(honors="2"), (),
     _C(rw=Wind.WEST, sw=Wind.NORTH), ["honitsu"], 3, 0),
    ("honitsu_open", _C(man="123455667", honors="11122"), _C(honors="2"),
     (gmeld(CHI, man="123"),), _C(rw=Wind.WEST, sw=Wind.NORTH), ["honitsu"], 2, 0),
    ("chinitsu_closed", _C(man="11234567677889"), _C(man="1"), (),
     _C(), ["chinitsu"], 6, 0),
    ("chinitsu_open", _C(man="11234567677889"), _C(man="1"),
     (gmeld(CHI, man="678"),), _C(), ["chinitsu"], 5, 0),
    ("ittsu_closed", _C(man="123456789", sou="123", honors="22"), _C(sou="3"), (),
     _C(rw=Wind.EAST, sw=Wind.NORTH), ["ittsuu"], 2, 0),
    ("ittsu_open", _C(man="123456789", sou="123", honors="22"), _C(sou="3"),
     (gmeld(CHI, man="123"),), _C(rw=Wind.EAST, sw=Wind.NORTH), ["ittsuu"], 1, 0),
    ("yakuhai_haku", _C(sou="234567", man="23422", honors="555"), _C(honors="5"), (),
     _C(), ["yakuhai_haku"], 1, 0),
    ("double_east", _C(sou="234567", man="23422", honors="111"), _C(honors="1"), (),
     _C(rw=Wind.EAST, sw=Wind.EAST), ["yakuhai_round", "yakuhai_seat"], 2, 0),
    ("seat_south", _C(sou="234567", man="23422", honors="222"), _C(honors="2"), (),
     _C(rw=Wind.EAST, sw=Wind.SOUTH), ["yakuhai_seat"], 1, 0),
    # ---- yakuman (tests_yakuman_calculation.py) ----
    ("tenhou", _C(sou="123444", man="234456", pin="66"), _C(sou="4"), (),
     _C(is_tsumo=True, is_tenhou=True), ["tenhou"], None, 1),
    ("chiihou", _C(sou="123444", man="234456", pin="66"), _C(sou="4"), (),
     _C(is_tsumo=True, is_chiihou=True), ["chiihou"], None, 1),
    ("daisangen", _C(sou="123", man="22", honors="555666777"), _C(honors="7"), (),
     _C(), ["daisangen"], None, 1),
    ("shosuushi", _C(sou="123", honors="11122233344"), _C(honors="4"), (),
     _C(), ["shousuushii"], None, None),
    ("daisuushi", _C(sou="22", honors="111222333444"), _C(honors="4"), (),
     _C(), ["daisuushii"], None, None),
    ("tsuisou_chiitoi", _C(honors="11223344556677"), _C(honors="7"), (),
     _C(), ["tsuuiisou"], None, 1),
    ("chinroto", _C(sou="111999", man="111999", pin="99"), _C(pin="9"), (),
     _C(is_tsumo=True), ["chinroutou"], None, None),
    ("kokushi_single", _C(sou="119", man="19", pin="19", honors="1234567"), _C(sou="9"), (),
     _C(), ["kokushi"], None, 1),
    ("kokushi_13", _C(sou="119", man="19", pin="19", honors="1234567"), _C(sou="1"), (),
     _C(), ["kokushi_13"], None, 2),
    ("ryuisou", _C(sou="22334466888", honors="666"), _C(honors="6"), (),
     _C(), ["ryuuiisou"], None, None),
    ("suuankou_tsumo", _C(sou="111444", man="333", pin="44555"), _C(pin="5"), (),
     _C(is_tsumo=True), ["suuankou"], None, None),
    ("suuankou_tanki_ron", _C(man="33344455577799"), _C(man="9"), (),
     _C(), ["suuankou_tanki"], None, 2),
    ("suukantsu", _C(sou="11113333", man="2222", pin="445555"), _C(pin="4"),
     (gmeld(KAN_O, sou="1111"), gmeld(KAN_O, sou="3333"), gmeld(KAN_O, pin="5555"),
      gmeld(KAN_O, man="2222")), _C(), ["suukantsu"], None, None),
    ("chuuren_single", _C(man="11123456789999"), _C(man="1"), (),
     _C(), ["chuuren"], None, 1),
    ("junsei_chuuren", _C(man="11122345678999"), _C(man="2"), (),
     _C(), ["junsei_chuuren"], None, 2),
]


@pytest.mark.parametrize(("case_id", "full", "win", "melds", "ctx_kw", "present", "han", "units"),
                         CASES, ids=[c[0] for c in CASES])
def test_golden(
    case_id: str,
    full: dict,
    win: dict,
    melds: tuple[Meld, ...],
    ctx_kw: dict,
    present: list[str],
    han: int | None,
    units: int | None,
) -> None:
    hand = _hand(full, melds)
    win_tile = _codes(**win)[0]
    ctx_kw = dict(ctx_kw)
    rw = ctx_kw.pop("rw", Wind.EAST)
    sw = ctx_kw.pop("sw", Wind.SOUTH)
    ctx = WinContext(round_wind=rw, seat_wind=sw, is_tsumo=ctx_kw.pop("is_tsumo", False), **ctx_kw)

    res = judge_yaku(hand, win_tile, ctx)
    assert res, f"{case_id}: expected a winning hand with yaku"

    all_ids = {y.id for e in res for y in e.yaku}
    for yid in present:
        assert yid in all_ids, f"{case_id}: missing yaku {yid!r}; got {sorted(all_ids)}"

    if han is not None:
        got = max((e.han for e in res if not e.is_yakuman), default=0)
        assert got == han, f"{case_id}: max_han {got} != {han}"

    if units is not None:
        got_u = max((e.yakuman_units for e in res), default=0)
        assert got_u == units, f"{case_id}: yakuman_units {got_u} != {units}"
