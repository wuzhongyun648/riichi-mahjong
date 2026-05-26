"""Situational yaku tests (docs/rules.md §4, §6, §8.1, §8.5)."""

from __future__ import annotations

from mahjong_engine.game_state import Wind
from tests.yaku_util import has, judge, yakuman_units

# A plain closed hand completed by a tanki wait on 9s (no structural yaku of
# its own besides menzen tsumo): 234m 567m 234p 678p + 9s9s.
CLOSED = "2m 3m 4m 5m 6m 7m 2p 3p 4p 6p 7p 8p 9s 9s"
WIN = "9s"


def test_riichi() -> None:
    assert has(judge(CLOSED, WIN, tsumo=False, is_riichi=True), "riichi")


def test_no_riichi_without_flag() -> None:
    assert not has(judge(CLOSED, WIN, tsumo=False), "riichi")


def test_double_riichi_replaces_riichi() -> None:
    res = judge(CLOSED, WIN, tsumo=False, is_double_riichi=True)
    assert has(res, "double_riichi")
    assert not has(res, "riichi")


def test_ippatsu() -> None:
    assert has(judge(CLOSED, WIN, tsumo=False, is_riichi=True, is_ippatsu=True), "ippatsu")


def test_menzen_tsumo() -> None:
    assert has(judge(CLOSED, WIN, tsumo=True), "menzen_tsumo")


def test_no_menzen_tsumo_on_ron() -> None:
    assert not has(judge(CLOSED, WIN, tsumo=False), "menzen_tsumo")


def test_no_menzen_tsumo_when_open() -> None:
    from tests.yaku_util import pon

    # Open hand (pon of 中) — tsumo must NOT grant menzen tsumo.
    res = judge("2m 3m 4m 5m 6m 7m 2p 3p 4p 9s 9s", WIN, melds=(pon(33),), tsumo=True)
    assert not has(res, "menzen_tsumo")


def test_riichi_requires_menzen() -> None:
    from tests.yaku_util import pon

    res = judge(
        "2m 3m 4m 5m 6m 7m 2p 3p 4p 9s 9s", WIN, melds=(pon(33),), tsumo=False, is_riichi=True
    )
    assert not has(res, "riichi")


def test_haitei() -> None:
    assert has(judge(CLOSED, WIN, tsumo=True, is_haitei=True), "haitei")


def test_houtei() -> None:
    assert has(judge(CLOSED, WIN, tsumo=False, is_houtei=True), "houtei")


def test_rinshan() -> None:
    assert has(judge(CLOSED, WIN, tsumo=True, is_rinshan=True), "rinshan")


def test_chankan() -> None:
    assert has(judge(CLOSED, WIN, tsumo=False, is_chankan=True), "chankan")


def test_tenhou_is_yakuman() -> None:
    res = judge(CLOSED, WIN, tsumo=True, is_tenhou=True)
    assert has(res, "tenhou")
    assert yakuman_units(res) >= 1


def test_chiihou_is_yakuman() -> None:
    res = judge(CLOSED, WIN, tsumo=True, sw=Wind.SOUTH, is_chiihou=True)
    assert has(res, "chiihou")
    assert yakuman_units(res) >= 1
