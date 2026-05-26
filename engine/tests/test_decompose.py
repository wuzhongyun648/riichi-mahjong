"""Tests for mahjong_engine.decompose.

Covers all three winning forms (standard / chiitoitsu / kokushi),
multi-decomposition hands, edge cases, and hypothesis round-trip properties.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mahjong_engine.decompose import (
    Block,
    BlockKind,
    DecompForm,
    all_decompositions,
    chiitoitsu_decomposition,
    is_complete_hand,
    kokushi_decomposition,
    standard_decompositions,
)
from mahjong_engine.hand import Hand
from mahjong_engine.tiles import TILE_COUNT, is_yaochuuhai, parse_tiles

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def counts_of(s: str) -> tuple[int, ...]:
    """Build a counts tuple from a space-separated tile string."""
    return Hand.from_str(s).counts


def blocks_tile_total(blocks: tuple[Block, ...]) -> int:
    return sum(len(b.tiles) for b in blocks)


def blocks_counts(blocks: tuple[Block, ...]) -> list[int]:
    out = [0] * TILE_COUNT
    for b in blocks:
        for t in b.tiles:
            out[t] += 1
    return out


# ---------------------------------------------------------------------------
# Standard form
# ---------------------------------------------------------------------------


class TestStandardDecomposition:
    def test_basic_four_sequences_plus_pair(self) -> None:
        # 123m 456p 789s 12s3s 5m5m → 14 tiles
        # actually: 1m 2m 3m 4p 5p 6p 7s 8s 9s 1s 2s 3s 5m 5m
        counts = counts_of("1m 2m 3m 4p 5p 6p 7s 8s 9s 1s 2s 3s 5m 5m")
        decomps = standard_decompositions(counts)
        assert len(decomps) == 1
        d = decomps[0]
        assert d.form is DecompForm.STANDARD
        assert d.pair_tile == 4  # 5m
        # Block tile-total equals sum(counts) = 14
        assert blocks_tile_total(d.blocks) == 14
        # Blocks reconstruct the original counts.
        assert blocks_counts(d.blocks) == list(counts)
        # Exactly 4 mentsu + 1 pair.
        kinds = [b.kind for b in d.blocks]
        assert kinds.count(BlockKind.PAIR) == 1
        mentsu = kinds.count(BlockKind.SHUNTSU) + kinds.count(BlockKind.KOUTSU)
        assert mentsu == 4

    def test_four_triplets_plus_pair(self) -> None:
        # 111m 222m 333m 444m 5m5m — counts[0..3]=3 each, counts[4]=2.
        # This hand has multiple valid factorings, including:
        #   (a) 4 koutsu (111/222/333/444) + 5m5m pair
        #   (b) 111m + 3 × 234m + 5m5m pair
        #   (c) 3 × 123m + 444m + 5m5m pair
        #   (d) 111m + 234m + 2 × 345m + 2m2m pair (pair on 2m)
        counts = counts_of("1m 1m 1m 2m 2m 2m 3m 3m 3m 4m 4m 4m 5m 5m")
        decomps = standard_decompositions(counts)
        assert len(decomps) == 4
        # Every decomposition reconstructs the input counts.
        for d in decomps:
            assert blocks_counts(d.blocks) == list(counts)
            assert blocks_tile_total(d.blocks) == 14
            assert len(d.blocks) == 5  # 4 mentsu + 1 pair
        # The "4 koutsu + 5m5m pair" decomposition must be present.
        four_koutsu = (BlockKind.KOUTSU,) * 4 + (BlockKind.PAIR,)
        kind_signatures = {
            tuple(sorted((b.kind for b in d.blocks), key=lambda k: k.value))
            for d in decomps
        }
        assert tuple(sorted(four_koutsu, key=lambda k: k.value)) in kind_signatures

    def test_multiple_decompositions(self) -> None:
        # counts[1]=4, counts[2]=4, counts[3]=4, counts[4]=2  (2m,3m,4m each 4; 5m pair)
        # Valid decompositions:
        #   (a) 4 × 234m + 5m5m pair       (pair on 5m)
        #   (b) 222m + 333m + 444m + 234m + 5m5m pair  (pair on 5m)
        #   (c) 2 × 234m + 2 × 345m + 2m2m pair        (pair on 2m)
        counts = counts_of(
            "2m 2m 2m 2m 3m 3m 3m 3m 4m 4m 4m 4m 5m 5m"
        )
        decomps = standard_decompositions(counts)
        assert len(decomps) == 3
        # Reconstruction invariant.
        for d in decomps:
            assert blocks_counts(d.blocks) == list(counts)
        # Two decompositions pair on 5m, one on 2m.
        pair_tiles = sorted(d.pair_tile for d in decomps)
        assert pair_tiles == [1, 4, 4]
        # Distinguish forms by mentsu kinds.
        mentsu_kinds_sets = {
            tuple(sorted(b.kind.value for b in d.blocks if b.kind is not BlockKind.PAIR))
            for d in decomps
        }
        assert ("shuntsu",) * 4 in mentsu_kinds_sets  # form (a)
        assert ("koutsu", "koutsu", "koutsu", "shuntsu") in mentsu_kinds_sets  # form (b)

    def test_honor_triplet_decomp(self) -> None:
        # 123m 456p 789s 东东东 5m5m
        counts = counts_of("1m 2m 3m 4p 5p 6p 7s 8s 9s 东 东 东 5m 5m")
        decomps = standard_decompositions(counts)
        assert len(decomps) == 1
        d = decomps[0]
        koutsu = [b for b in d.blocks if b.kind is BlockKind.KOUTSU]
        assert len(koutsu) == 1
        assert koutsu[0].tiles == (27, 27, 27)

    def test_honor_pair_jantai(self) -> None:
        # Pair on honors, four mentsu in suits.
        counts = counts_of("1m 2m 3m 4m 5m 6m 1p 2p 3p 7s 8s 9s 中 中")
        decomps = standard_decompositions(counts)
        assert len(decomps) == 1
        assert decomps[0].pair_tile == 33

    def test_no_decomposition(self) -> None:
        # Random 14-tile garbage that doesn't decompose.
        counts = counts_of("1m 2m 4m 5m 7m 8m 1p 3p 5p 7p 9p 1s 3s 5s")
        assert standard_decompositions(counts) == []

    def test_sum_not_mod3_eq_2(self) -> None:
        # 13 tiles → no standard decomposition possible.
        counts = counts_of("1m 2m 3m 4p 5p 6p 7s 8s 9s 东 东 东 5m")
        assert standard_decompositions(counts) == []

    def test_partial_hand_after_chi_meld(self) -> None:
        # After one meld, concealed counts has 11 tiles total: 1 head + 3 mentsu.
        # Concealed: 4p5p6p 7s8s9s 东东东 5m5m → 11 tiles
        counts = counts_of("4p 5p 6p 7s 8s 9s 东 东 东 5m 5m")
        decomps = standard_decompositions(counts)
        assert len(decomps) == 1
        d = decomps[0]
        # 3 mentsu + 1 pair
        assert len(d.blocks) == 4
        assert d.pair_tile == 4

    def test_partial_hand_three_melds(self) -> None:
        # 3 melds taken → concealed has 5 tiles = 1 mentsu + 1 pair.
        counts = counts_of("1m 2m 3m 5m 5m")
        decomps = standard_decompositions(counts)
        assert len(decomps) == 1
        d = decomps[0]
        assert len(d.blocks) == 2
        assert d.pair_tile == 4

    def test_four_melds_only_pair(self) -> None:
        # 4 melds → concealed has just the head (2 tiles).
        counts = counts_of("5m 5m")
        decomps = standard_decompositions(counts)
        assert len(decomps) == 1
        d = decomps[0]
        assert len(d.blocks) == 1
        assert d.blocks[0].kind is BlockKind.PAIR
        assert d.pair_tile == 4

    def test_input_validation(self) -> None:
        with pytest.raises(ValueError):
            standard_decompositions([0] * 33)  # wrong length
        bad = [0] * TILE_COUNT
        bad[0] = 5
        with pytest.raises(ValueError):
            standard_decompositions(bad)


# ---------------------------------------------------------------------------
# Chiitoitsu
# ---------------------------------------------------------------------------


class TestChiitoitsuDecomposition:
    def test_valid_chiitoi(self) -> None:
        counts = counts_of("1m 1m 2m 2m 3p 3p 4p 4p 5s 5s 6s 6s 中 中")
        d = chiitoitsu_decomposition(counts)
        assert d is not None
        assert d.form is DecompForm.CHIITOITSU
        assert d.pair_tile is None
        assert len(d.blocks) == 7
        assert all(b.kind is BlockKind.PAIR_CHIITOI for b in d.blocks)
        # 7 distinct pair tiles, ascending.
        pair_tiles = [b.tiles[0] for b in d.blocks]
        assert pair_tiles == sorted(pair_tiles)
        assert len(set(pair_tiles)) == 7

    def test_invalid_sum(self) -> None:
        counts = counts_of("1m 1m 2m 2m 3p 3p 4p 4p 5s 5s 6s 6s")  # 12 tiles
        assert chiitoitsu_decomposition(counts) is None

    def test_four_of_a_kind_is_not_chiitoi(self) -> None:
        # 4×1m + 6 pairs = 14 tiles total; but 4-of-a-kind is not 2 pairs.
        # Construct: 1m1m1m1m + 6 distinct pairs.
        counts = counts_of("1m 1m 1m 1m 2m 2m 3p 3p 4p 4p 5s 5s 6s 6s")
        assert chiitoitsu_decomposition(counts) is None

    def test_triplet_is_not_chiitoi(self) -> None:
        # 3×1m + ... → not chiitoi (counts[0] == 3, neither 0 nor 2).
        counts = counts_of("1m 1m 1m 2m 2m 3p 3p 4p 4p 5s 5s 6s 6s 中")
        assert chiitoitsu_decomposition(counts) is None

    def test_six_pairs_one_single_is_not_chiitoi(self) -> None:
        # 13 tiles, 6 pairs + 1 single → tenpai but not yet chiitoi.
        counts = counts_of("1m 1m 2m 2m 3p 3p 4p 4p 5s 5s 6s 6s 中")
        assert chiitoitsu_decomposition(counts) is None


# ---------------------------------------------------------------------------
# Kokushi
# ---------------------------------------------------------------------------


class TestKokushiDecomposition:
    def test_valid_kokushi_with_pair_on_haku(self) -> None:
        counts = counts_of("1m 9m 1p 9p 1s 9s 东 南 西 北 白 白 发 中")
        d = kokushi_decomposition(counts)
        assert d is not None
        assert d.form is DecompForm.KOKUSHI
        assert d.pair_tile == 31  # 白
        assert len(d.blocks) == 1
        assert d.blocks[0].kind is BlockKind.PAIR
        assert d.blocks[0].tiles == (31, 31)

    def test_valid_kokushi_with_pair_on_1m(self) -> None:
        counts = counts_of("1m 1m 9m 1p 9p 1s 9s 东 南 西 北 白 发 中")
        d = kokushi_decomposition(counts)
        assert d is not None
        assert d.pair_tile == 0

    def test_invalid_missing_yaochuu(self) -> None:
        # Missing 中, doubled 白 — not all 13 yaochuu present.
        counts = counts_of("1m 9m 1p 9p 1s 9s 东 南 西 北 白 白 白 发")
        assert kokushi_decomposition(counts) is None

    def test_invalid_extra_middle_tile(self) -> None:
        counts = counts_of("1m 9m 1p 9p 1s 9s 东 南 西 北 白 发 中 5m")
        assert kokushi_decomposition(counts) is None

    def test_invalid_sum(self) -> None:
        # 13 tiles only — kokushi requires 14.
        counts = counts_of("1m 9m 1p 9p 1s 9s 东 南 西 北 白 发 中")
        assert kokushi_decomposition(counts) is None

    def test_invalid_two_pairs(self) -> None:
        # Two yaochuu pairs ⇒ 15 tiles or duplicates beyond 1 → impossible at 14.
        counts = counts_of("1m 1m 9m 9m 1p 9p 1s 9s 东 南 西 北 白 发")  # 14 但少中
        assert kokushi_decomposition(counts) is None


# ---------------------------------------------------------------------------
# all_decompositions / is_complete_hand
# ---------------------------------------------------------------------------


class TestAllDecompositions:
    def test_chiitoi_collected(self) -> None:
        counts = counts_of("1m 1m 2m 2m 3p 3p 4p 4p 5s 5s 6s 6s 中 中")
        ds = all_decompositions(counts)
        forms = {d.form for d in ds}
        assert DecompForm.CHIITOITSU in forms

    def test_kokushi_collected(self) -> None:
        counts = counts_of("1m 1m 9m 1p 9p 1s 9s 东 南 西 北 白 发 中")
        ds = all_decompositions(counts)
        forms = {d.form for d in ds}
        assert DecompForm.KOKUSHI in forms

    def test_is_complete_hand_standard(self) -> None:
        counts = counts_of("1m 2m 3m 4p 5p 6p 7s 8s 9s 东 东 东 5m 5m")
        assert is_complete_hand(counts, n_melds=0) is True

    def test_is_complete_hand_chiitoi_requires_no_melds(self) -> None:
        counts = counts_of("1m 1m 2m 2m 3p 3p 4p 4p 5s 5s 6s 6s 中 中")
        assert is_complete_hand(counts, n_melds=0) is True
        # Chiitoi with melds is illegal — but counts here is 14 so the
        # mismatch makes standard fail too, so it returns False overall.
        assert is_complete_hand(counts, n_melds=1) is False

    def test_is_complete_hand_kokushi_requires_no_melds(self) -> None:
        counts = counts_of("1m 1m 9m 1p 9p 1s 9s 东 南 西 北 白 发 中")
        assert is_complete_hand(counts, n_melds=0) is True
        assert is_complete_hand(counts, n_melds=1) is False


# ---------------------------------------------------------------------------
# Hypothesis: synthesise winning hands and verify round-trip
# ---------------------------------------------------------------------------


# Generate a sequence-only standard hand:
#   pick a suit s ∈ {m,p,s}, build counts[s_base..s_base+8] from 4 random
#   sequence starts, then a random pair.
# Verify that standard_decompositions(counts) returns a decomposition whose
# blocks sum back to counts.


@st.composite
def standard_hand_counts(draw: st.DrawFn) -> tuple[int, ...]:
    counts = [0] * TILE_COUNT
    # 4 mentsu, each either a sequence (suited only) or a triplet (any tile).
    for _ in range(4):
        kind = draw(st.sampled_from(["seq", "trip"]))
        if kind == "seq":
            suit_base = draw(st.sampled_from([0, 9, 18]))
            start = draw(st.integers(min_value=0, max_value=6))
            for o in range(3):
                if counts[suit_base + start + o] >= 4:
                    # back off to triplet path
                    kind = "trip"
                    break
            if kind == "seq":
                for o in range(3):
                    counts[suit_base + start + o] += 1
                continue
        # triplet path
        t = draw(st.integers(min_value=0, max_value=33))
        if counts[t] > 1:
            # can't add 3 more without exceeding 4 — back off
            # pick a fresh tile
            for cand in range(34):
                if counts[cand] == 0:
                    t = cand
                    break
        counts[t] += 3
    # head
    for _ in range(50):
        h = draw(st.integers(min_value=0, max_value=33))
        if counts[h] <= 2:
            counts[h] += 2
            break
    if sum(counts) != 14:
        # bail: skip via filter
        return tuple()  # caller will check
    return tuple(counts)


@settings(max_examples=200, deadline=2000)
@given(standard_hand_counts())
def test_synthetic_winning_hand_decomposes(counts: tuple[int, ...]) -> None:
    if sum(counts) != 14:
        return
    decomps = standard_decompositions(counts)
    assert decomps, f"expected at least one decomposition for counts={counts}"
    for d in decomps:
        # Reconstructed counts equal the input.
        assert blocks_counts(d.blocks) == list(counts)
        # 4 mentsu + 1 pair.
        kinds = [b.kind for b in d.blocks]
        assert kinds.count(BlockKind.PAIR) == 1
        assert len(d.blocks) == 5


@st.composite
def chiitoi_counts(draw: st.DrawFn) -> tuple[int, ...]:
    tiles = draw(
        st.sets(st.integers(min_value=0, max_value=33), min_size=7, max_size=7)
    )
    counts = [0] * TILE_COUNT
    for t in tiles:
        counts[t] = 2
    return tuple(counts)


@settings(max_examples=100, deadline=2000)
@given(chiitoi_counts())
def test_synthetic_chiitoi_round_trip(counts: tuple[int, ...]) -> None:
    d = chiitoitsu_decomposition(counts)
    assert d is not None
    assert blocks_counts(d.blocks) == list(counts)


@st.composite
def kokushi_counts(draw: st.DrawFn) -> tuple[int, ...]:
    yaochuu = tuple(t for t in range(34) if is_yaochuuhai(t))
    pair = draw(st.sampled_from(yaochuu))
    counts = [0] * TILE_COUNT
    for t in yaochuu:
        counts[t] = 1
    counts[pair] = 2
    return tuple(counts)


@settings(max_examples=20, deadline=2000)
@given(kokushi_counts())
def test_synthetic_kokushi_round_trip(counts: tuple[int, ...]) -> None:
    d = kokushi_decomposition(counts)
    assert d is not None
    assert d.form is DecompForm.KOKUSHI
    assert counts[d.pair_tile] == 2  # type: ignore[index]


# ---------------------------------------------------------------------------
# Parse helpers regression
# ---------------------------------------------------------------------------


def test_parse_tiles_helper_consistent() -> None:
    # Just makes sure the test helper itself doesn't drift from the
    # encoding contract.
    parsed = parse_tiles("1m 9m 东 中")
    assert [code for code, _ in parsed] == [0, 8, 27, 33]

# ---------------------------------------------------------------------------
# M2 Guide Demo Tests
# ---------------------------------------------------------------------------

def test_m2_guide_demo_decompose() -> None:
    from mahjong_engine.tiles import make_counts, parse_tiles, tile_to_str
    def to_counts(s):
        return make_counts([t for t,_ in parse_tiles(s)])
    
    # 1. 标准型多分解
    counts = to_counts('1m 1m 1m 2m 3m 4m 2m 3m 4m 2m 3m 4m 5m 5m')
    decomps = standard_decompositions(counts)
    assert len(decomps) == 4
    
    # 2. 七対子
    counts = to_counts('1m 1m 3m 3m 5p 5p 7p 7p 1s 1s 3s 3s 东 东')
    chiitoi = chiitoitsu_decomposition(counts)
    assert chiitoi is not None
    assert chiitoi.form.name == 'CHIITOITSU'
    
    # 3. 国士無双
    counts = to_counts('1m 9m 1p 9p 1s 9s 东 南 西 北 白 发 中 中')
    kokushi = kokushi_decomposition(counts)
    assert kokushi is not None
    assert kokushi.form.name == 'KOKUSHI'
    assert tile_to_str(kokushi.pair_tile) == '中'
    
    # 4. is_complete_hand
    assert is_complete_hand(to_counts('1m 1m 1m 2m 3m 4m 5p 5p 5p 6p 7p 8p 东 东')) is True
    assert is_complete_hand(to_counts('1m 1m 3m 3m 5p 5p 7p 7p 1s 1s 3s 3s 东 东')) is True
    assert is_complete_hand(to_counts('1m 2m 3m 4m 5m 6m 7m 6p 7p 8p 1s 1s 1s')) is False
