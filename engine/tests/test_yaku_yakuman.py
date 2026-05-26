"""Yakuman / double-yakuman tests (docs/rules.md §8.5-§8.7)."""

from __future__ import annotations

from tests.yaku_util import has, judge, kan, yakuman_units


def test_kokushi_single() -> None:
    res = judge("1m 9m 1p 9p 1s 9s 东 南 西 北 白 发 中 中", "1m", tsumo=True)
    assert has(res, "kokushi")
    assert yakuman_units(res) == 1


def test_kokushi_juusanmen_double() -> None:
    # Winning on the pairing tile -> 13-sided wait -> double yakuman.
    res = judge("1m 9m 1p 9p 1s 9s 东 南 西 北 白 发 中 中", "中", tsumo=True)
    assert has(res, "kokushi_13")
    assert yakuman_units(res) == 2


def test_suuankou_single_tsumo() -> None:
    # Four concealed triplets, tsumo, shanpon wait -> single suuankou.
    res = judge("1m 1m 1m 3p 3p 3p 7s 7s 7s 9m 9m 9m 5s 5s", "9m", tsumo=True)
    assert has(res, "suuankou")
    assert yakuman_units(res) == 1


def test_suuankou_tanki_double_on_ron() -> None:
    # Tanki wait on the pair -> all four triplets already concealed -> double, ron ok.
    res = judge("1m 1m 1m 3p 3p 3p 7s 7s 7s 东 东 东 5s 5s", "5s", tsumo=False)
    assert has(res, "suuankou_tanki")
    assert yakuman_units(res) == 2


def test_suuankou_broken_by_ron_shanpon() -> None:
    # Ron completing a triplet via shanpon -> that triplet open -> only sanankou.
    res = judge("1m 1m 1m 3p 3p 3p 7s 7s 7s 9m 9m 9m 5s 5s", "9m", tsumo=False)
    assert not has(res, "suuankou")
    assert has(res, "sanankou")


def test_daisangen() -> None:
    res = judge("白 白 白 发 发 发 中 中 中 2m 3m 4m 5s 5s", "2m")
    assert has(res, "daisangen")
    assert yakuman_units(res) == 1


def test_shousuushii() -> None:
    res = judge("东 东 东 南 南 南 西 西 西 北 北 2m 3m 4m", "2m")
    assert has(res, "shousuushii")
    assert yakuman_units(res) == 1


def test_daisuushii_double() -> None:
    # Four wind triplets + tsumo also makes suuankou, so units stack >= 2.
    res = judge("东 东 东 南 南 南 西 西 西 北 北 北 5m 5m", "5m", tsumo=True)
    assert has(res, "daisuushii")
    assert yakuman_units(res) >= 2


def test_tsuuiisou_standard() -> None:
    res = judge("东 东 东 南 南 南 西 西 西 白 白 白 发 发", "东", tsumo=True)
    assert has(res, "tsuuiisou")
    assert yakuman_units(res) >= 1


def test_tsuuiisou_chiitoi() -> None:
    res = judge("东 东 南 南 西 西 北 北 白 白 发 发 中 中", "中", tsumo=False)
    assert has(res, "tsuuiisou")


def test_ryuuiisou_with_hatsu() -> None:
    res = judge("2s 2s 2s 3s 3s 3s 4s 4s 4s 6s 6s 发 发 发", "6s", tsumo=True)
    assert has(res, "ryuuiisou")


def test_ryuuiisou_without_hatsu() -> None:
    # 发 not required (docs/rules.md §8.8).
    res = judge("2s 2s 2s 3s 3s 3s 4s 4s 4s 6s 6s 6s 8s 8s", "8s", tsumo=True)
    assert has(res, "ryuuiisou")


def test_ryuuiisou_negative_non_green() -> None:
    res = judge("2s 2s 2s 3s 3s 3s 4s 4s 4s 5s 5s 5s 8s 8s", "8s", tsumo=True)
    assert not has(res, "ryuuiisou")


def test_chinroutou() -> None:
    # All terminal triplets + tsumo also makes suuankou, so units stack >= 1.
    res = judge("1m 1m 1m 9m 9m 9m 1p 1p 1p 1s 1s 1s 9p 9p", "1m", tsumo=True)
    assert has(res, "chinroutou")
    assert yakuman_units(res) >= 1


def test_suukantsu() -> None:
    res = judge("5s 5s", "5s", melds=(kan(0), kan(10), kan(20), kan(30)))
    assert has(res, "suukantsu")
    assert yakuman_units(res) >= 1


def test_chuuren() -> None:
    # Non-pure: extra tile is not the win tile (win 2m, extra is the doubled 1m... craft impure).
    res = judge("1m 1m 1m 1m 2m 3m 4m 5m 6m 7m 8m 9m 9m 9m", "2m", tsumo=True)
    assert has(res, "chuuren")
    assert yakuman_units(res) == 1


def test_junsei_chuuren_double() -> None:
    # Pure nine-wait: removing win 5m leaves 1112345678999.
    res = judge("1m 1m 1m 2m 3m 4m 5m 6m 7m 8m 9m 9m 9m 5m", "5m", tsumo=True)
    assert has(res, "junsei_chuuren")
    assert yakuman_units(res) == 2


def test_multi_yakuman_stacks() -> None:
    # 字一色 + 大三元: all honors, three dragon triplets -> two yakuman units.
    res = judge("白 白 白 发 发 发 中 中 中 东 东 东 南 南", "东", tsumo=True)
    assert has(res, "tsuuiisou")
    assert has(res, "daisangen")
    assert yakuman_units(res) >= 2


def test_tenhou_stacks_with_suuankou() -> None:
    res = judge(
        "1m 1m 1m 3p 3p 3p 7s 7s 7s 9m 9m 9m 5s 5s", "9m", tsumo=True, is_tenhou=True
    )
    assert has(res, "tenhou")
    assert has(res, "suuankou")
    assert yakuman_units(res) == 2


def test_yakuman_cap_six() -> None:
    # Four ankan (suukantsu + suuankou-tanki) + tenhou + chiihou flags -> capped at 6.
    res = judge(
        "5s 5s",
        "5s",
        melds=(kan(0), kan(10), kan(20), kan(30)),
        tsumo=True,
        is_tenhou=True,
        is_chiihou=True,
    )
    assert yakuman_units(res) <= 6
