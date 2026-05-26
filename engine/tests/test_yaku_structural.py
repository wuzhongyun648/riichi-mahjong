"""Normal (1-6 han) structural yaku tests (docs/rules.md §8.1-§8.4)."""

from __future__ import annotations

from mahjong_engine.game_state import Wind
from tests.yaku_util import chi, has, judge, kan, max_han, pon


# --- tanyao -----------------------------------------------------------------
def test_tanyao_positive() -> None:
    assert has(judge("2m 3m 4m 5p 6p 7p 3s 4s 5s 6s 7s 8s 2p 2p", "2m"), "tanyao")


def test_tanyao_negative_terminal() -> None:
    assert not has(judge("1m 2m 3m 5p 6p 7p 3s 4s 5s 6s 7s 8s 2p 2p", "2m"), "tanyao")


def test_tanyao_open() -> None:
    # 食断: open tanyao is valid (§10.1).
    res = judge("2m 3m 4m 5p 6p 7p 3s 4s 5s 2p 2p", "2m", melds=(chi(19),), tsumo=False)
    assert has(res, "tanyao")


# --- pinfu ------------------------------------------------------------------
def test_pinfu_positive() -> None:
    # all sequences, simple pair, ryanmen wait on 4m (held 2m3m).
    res = judge("2m 3m 4m 5m 6m 7m 2p 3p 4p 7p 8p 9p 2s 2s", "4m")
    assert has(res, "pinfu")


def test_pinfu_negative_kanchan_wait() -> None:
    # win 2m completes 1m_3m kanchan -> not pinfu.
    res = judge("1m 3m 4m 5m 6m 2p 3p 4p 7p 8p 9p 2s 2s 2m", "2m")
    assert not has(res, "pinfu")


def test_pinfu_negative_yakuhai_pair() -> None:
    # pair is round wind (East) -> not pinfu.
    res = judge("2m 3m 4m 5m 6m 7m 2p 3p 4p 7p 8p 9p 东 东", "4m", rw=Wind.EAST)
    assert not has(res, "pinfu")


# --- iipeikou / ryanpeikou --------------------------------------------------
def test_iipeikou() -> None:
    res = judge("2m 3m 4m 2m 3m 4m 5p 6p 7p 1s 2s 3s 9s 9s", "2m")
    assert has(res, "iipeikou")


def test_iipeikou_negative_open() -> None:
    res = judge("2m 3m 4m 5p 6p 7p 1s 2s 3s 9s 9s", "2m", melds=(chi(1),), tsumo=False)
    assert not has(res, "iipeikou")


def test_ryanpeikou() -> None:
    res = judge("2m 3m 4m 2m 3m 4m 6p 7p 8p 6p 7p 8p 9s 9s", "2m")
    assert has(res, "ryanpeikou")
    assert not has(res, "iipeikou")


# --- sanshoku / ittsuu ------------------------------------------------------
def test_sanshoku_doujun() -> None:
    res = judge("2m 3m 4m 2p 3p 4p 2s 3s 4s 7m 8m 9m 5s 5s", "2m")
    assert has(res, "sanshoku")
    assert any(y.han == 2 for e in res for y in e.yaku if y.id == "sanshoku")


def test_sanshoku_kuisagari_open() -> None:
    res = judge("2m 3m 4m 2p 3p 4p 7m 8m 9m 5s 5s", "2m", melds=(chi(19),), tsumo=False)
    assert any(y.han == 1 for e in res for y in e.yaku if y.id == "sanshoku")


def test_ittsuu() -> None:
    res = judge("1m 2m 3m 4m 5m 6m 7m 8m 9m 2p 3p 4p 5s 5s", "2p")
    assert has(res, "ittsuu")


def test_ittsuu_kuisagari_open() -> None:
    res = judge("1m 2m 3m 4m 5m 6m 7m 8m 9m 5s 5s", "5m", melds=(chi(9),), tsumo=False)
    assert any(y.han == 1 for e in res for y in e.yaku if y.id == "ittsuu")


# --- chanta / junchan -------------------------------------------------------
def test_chanta() -> None:
    res = judge("1m 2m 3m 7p 8p 9p 1s 2s 3s 东 东 东 9s 9s", "2m")
    assert has(res, "chanta")
    assert not has(res, "junchan")


def test_junchan() -> None:
    res = judge("1m 2m 3m 7p 8p 9p 1s 2s 3s 9m 9m 9m 9s 9s", "2m")
    assert has(res, "junchan")
    assert not has(res, "chanta")


# --- toitoi / sanankou ------------------------------------------------------
def test_toitoi() -> None:
    res = judge("2m 2m 2m 5p 5p 5p 8s 8s 8s 3s 3s 3s 9p 9p", "2m", tsumo=False, melds=(pon(7),))
    assert has(res, "toitoi")


def test_sanankou_tsumo() -> None:
    res = judge("1m 1m 1m 3p 3p 3p 7s 7s 7s 2p 3p 4p 9m 9m", "1m", tsumo=True)
    assert has(res, "sanankou")


def test_sanankou_broken_by_ron_into_triplet() -> None:
    # ron on 1m, which only fits the 1m triplet -> that triplet is open.
    res = judge("1m 1m 1m 3p 3p 3p 7s 7s 7s 2p 3p 4p 9m 9m", "1m", tsumo=False)
    assert not has(res, "sanankou")


def test_sanankou_kept_when_ron_into_sequence() -> None:
    # ron on 2p sits in the 2p3p4p sequence -> all three triplets stay concealed.
    res = judge("1m 1m 1m 3p 3p 3p 7s 7s 7s 2p 3p 4p 9m 9m", "2p", tsumo=False)
    assert has(res, "sanankou")


# --- kan-based --------------------------------------------------------------
def test_sankantsu() -> None:
    res = judge("7m 8m 9m 5s 5s", "7m", melds=(kan(0), kan(10), kan(20)))
    assert has(res, "sankantsu")


# --- sanshoku doukou / shousangen ------------------------------------------
def test_sanshoku_doukou() -> None:
    res = judge("3m 3m 3m 3p 3p 3p 3s 3s 3s 7m 8m 9m 5s 5s", "3m", tsumo=False, melds=(pon(2),))
    assert has(res, "sanshoku_doukou")


def test_shousangen() -> None:
    res = judge("白 白 白 发 发 发 中 中 2m 3m 4m 5s 6s 7s", "中")
    assert has(res, "shousangen")
    # Two dragon triplets each give a yakuhai (2 han) on top of shousangen (2).
    assert has(res, "yakuhai_haku")
    assert has(res, "yakuhai_hatsu")


# --- honroutou --------------------------------------------------------------
def test_honroutou() -> None:
    # Open pon(1m) keeps it out of suuankou; all-yaochuu triplets -> honroutou + toitoi.
    res = judge("9p 9p 9p 东 东 东 9s 9s 9s 中 中", "中", tsumo=False, melds=(pon(0),))
    assert has(res, "honroutou")
    assert has(res, "toitoi")


def test_honroutou_chiitoi() -> None:
    res = judge("1m 1m 9m 9m 1p 1p 9p 9p 1s 1s 9s 9s 东 东", "东", tsumo=False)
    assert has(res, "honroutou")
    assert has(res, "chiitoitsu")


# --- honitsu / chinitsu -----------------------------------------------------
def test_honitsu_closed() -> None:
    res = judge("1m 1m 1m 2m 3m 4m 5m 6m 7m 东 东 东 9m 9m", "2m", rw=Wind.SOUTH)
    assert any(y.id == "honitsu" and y.han == 3 for e in res for y in e.yaku)


def test_chinitsu_closed() -> None:
    res = judge("1m 1m 1m 2m 3m 4m 5m 6m 7m 8m 8m 8m 9m 9m", "2m")
    assert any(y.id == "chinitsu" and y.han == 6 for e in res for y in e.yaku)


def test_chinitsu_open_kuisagari() -> None:
    res = judge("1m 1m 1m 5m 6m 7m 8m 8m 8m 9m 9m", "5m", melds=(chi(1),), tsumo=False)
    assert any(y.id == "chinitsu" and y.han == 5 for e in res for y in e.yaku)


# --- yakuhai ----------------------------------------------------------------
def test_yakuhai_dragon() -> None:
    res = judge("中 中 中 2m 3m 4m 5p 6p 7p 1s 2s 3s 9s 9s", "2m")
    assert has(res, "yakuhai_chun")


def test_yakuhai_round_and_seat_distinct() -> None:
    # East round, South seat: 东 triplet = round wind only; 南 triplet = seat only.
    res = judge("东 东 东 南 南 南 2m 3m 4m 5p 6p 7p 9s 9s", "2m", rw=Wind.EAST, sw=Wind.SOUTH)
    assert has(res, "yakuhai_round")
    assert has(res, "yakuhai_seat")


def test_double_wind_counts_two_han() -> None:
    # East round + East seat: the 东 triplet counts both round and seat (2 han, §8.8).
    res = judge("东 东 东 2m 3m 4m 5p 6p 7p 1s 2s 3s 9s 9s", "2m", rw=Wind.EAST, sw=Wind.EAST)
    assert has(res, "yakuhai_round")
    assert has(res, "yakuhai_seat")


# --- chiitoitsu -------------------------------------------------------------
def test_chiitoitsu() -> None:
    res = judge("1m 1m 3m 3m 5p 5p 7p 7p 1s 1s 3s 3s 东 东", "东", tsumo=False)
    assert has(res, "chiitoitsu")


def test_chiitoitsu_tanyao() -> None:
    res = judge("2m 2m 4m 4m 5p 5p 7p 7p 2s 2s 4s 4s 6s 6s", "2m", tsumo=False)
    assert has(res, "chiitoitsu")
    assert has(res, "tanyao")


def test_ryanpeikou_beats_chiitoi_on_han() -> None:
    # 112233m 445566p 99s is both ryanpeikou (3) and chiitoi (2).
    res = judge("1m 1m 2m 2m 3m 3m 4p 4p 5p 5p 6p 6p 9s 9s", "9s")
    assert has(res, "ryanpeikou")
    assert has(res, "chiitoitsu")
    assert max_han(res) >= 3


# --- kuisagari (副露降番) ----------------------------------------------------
def _han_of(res: list, yaku_id: str) -> int:
    return next(y.han for e in res for y in e.yaku if y.id == yaku_id)


def test_honitsu_open_kuisagari() -> None:
    res = judge(
        "1m 1m 1m 5m 6m 7m 东 东 东 9m 9m", "5m", melds=(chi(0),), tsumo=False, rw=Wind.EAST
    )
    assert _han_of(res, "honitsu") == 2


def test_chanta_open_kuisagari() -> None:
    res = judge("7p 8p 9p 1s 2s 3s 东 东 东 9s 9s", "7p", melds=(chi(0),), tsumo=False)
    assert _han_of(res, "chanta") == 1


def test_junchan_open_kuisagari() -> None:
    res = judge("7p 8p 9p 1s 2s 3s 9m 9m 9m 9s 9s", "7p", melds=(chi(0),), tsumo=False)
    assert _han_of(res, "junchan") == 2


# --- negatives (avoid false positives) --------------------------------------
def test_ittsuu_negative_not_147() -> None:
    # 234 567 789 — not the 123/456/789 run set.
    res = judge("2m 3m 4m 5m 6m 7m 7m 8m 9m 2p 3p 4p 5s 5s", "2m")
    assert not has(res, "ittsuu")


def test_sanshoku_negative_mixed() -> None:
    # 234m / 345p / 234s — pin breaks the three-suit match.
    res = judge("2m 3m 4m 3p 4p 5p 2s 3s 4s 7m 8m 9m 5s 5s", "2m")
    assert not has(res, "sanshoku")


def test_chanta_negative_inner_set() -> None:
    # 456p has no yaochuu tile -> not chanta.
    res = judge("1m 2m 3m 4p 5p 6p 1s 2s 3s 东 东 东 9s 9s", "2m")
    assert not has(res, "chanta")
    assert not has(res, "junchan")


def test_pinfu_negative_penchan_wait() -> None:
    # 1m2m waiting 3m is penchan -> not pinfu.
    res = judge("1m 2m 4m 5m 6m 2p 3p 4p 7p 8p 9p 2s 2s 3m", "3m")
    assert not has(res, "pinfu")


def test_iipeikou_negative_distinct_sequences() -> None:
    # 234m + 345m are not identical -> no iipeikou.
    res = judge("2m 3m 4m 3m 4m 5m 5p 6p 7p 1s 2s 3s 9s 9s", "2m")
    assert not has(res, "iipeikou")


# --- ankan (暗杠) -----------------------------------------------------------
def test_sanankou_with_ankan() -> None:
    # Two ankan + one concealed triplet = three concealed triplets.
    res = judge("5p 5p 5p 9s 9s", "5p", melds=(kan(0), kan(20)), tsumo=True)
    assert has(res, "sanankou")


def test_ankan_keeps_menzen_for_riichi() -> None:
    res = judge("2m 3m 4m 5m 6m 7m 9s 9s", "4m", melds=(kan(0),), tsumo=False, is_riichi=True)
    assert has(res, "riichi")


# --- han totals (stable composites) -----------------------------------------
def test_pinfu_tanyao_tsumo_total() -> None:
    res = judge("2m 3m 4m 5m 6m 7m 3p 4p 5p 6p 7p 8p 2s 2s", "4m")
    assert max_han(res) == 3  # pinfu + tanyao + menzen tsumo


def test_shousangen_total_with_two_yakuhai() -> None:
    # shousangen(2) + 白(1) + 发(1) = 4 han (ron, so no menzen tsumo).
    res = judge("白 白 白 发 发 发 中 中 2m 3m 4m 5s 6s 7s", "中", tsumo=False)
    assert max_han(res) == 4
