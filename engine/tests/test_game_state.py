"""Tests for mahjong_engine.game_state.

Covers: new_game() initial state invariants, dealer tile count, score,
seat winds, seed reproducibility.

Hypothesis property: any seed produces a state where all tile counts sum to 136.
"""

from collections import Counter

import hypothesis.strategies as st
from hypothesis import given, settings

from mahjong_engine.game_state import (
    INITIAL_SCORE,
    NUM_PLAYERS,
    GameMode,
    Wind,
    new_game,
)
from mahjong_engine.tiles import TILE_COUNT
from mahjong_engine.wall import DEAD_WALL_SIZE, TOTAL_TILES

# ---------------------------------------------------------------------------
# new_game() basic invariants
# ---------------------------------------------------------------------------


class TestNewGameDefaults:
    def setup_method(self) -> None:
        self.state = new_game(seed=42)

    def test_round_wind_is_east(self) -> None:
        assert self.state.round_wind == Wind.EAST

    def test_round_number_is_one(self) -> None:
        assert self.state.round_number == 1

    def test_honba_zero(self) -> None:
        assert self.state.honba == 0

    def test_riichi_sticks_zero(self) -> None:
        assert self.state.riichi_sticks == 0

    def test_turn_count_zero(self) -> None:
        assert self.state.turn_count == 0

    def test_default_mode_is_half(self) -> None:
        assert self.state.mode == GameMode.HALF

    def test_dealer_index_default(self) -> None:
        assert self.state.dealer_index == 0
        assert self.state.active_player_index == 0


class TestNewGamePlayers:
    def setup_method(self) -> None:
        self.state = new_game(seed=0, dealer_index=0)

    def test_four_players(self) -> None:
        assert len(self.state.players) == NUM_PLAYERS

    def test_dealer_has_14_tiles(self) -> None:
        dealer = self.state.players[self.state.dealer_index]
        assert dealer.hand.tile_count == 14

    def test_non_dealers_have_13_tiles(self) -> None:
        for i, player in enumerate(self.state.players):
            if i != self.state.dealer_index:
                assert player.hand.tile_count == 13, (
                    f"Seat {i} should have 13 tiles, got {player.hand.tile_count}"
                )

    def test_initial_scores(self) -> None:
        for player in self.state.players:
            assert player.score == INITIAL_SCORE

    def test_empty_rivers(self) -> None:
        for player in self.state.players:
            assert player.river == ()

    def test_no_riichi_at_start(self) -> None:
        for player in self.state.players:
            assert player.in_riichi is False
            assert player.riichi_turn is None

    def test_seat_winds(self) -> None:
        # Dealer (seat 0) = East, then South, West, North
        expected = [Wind.EAST, Wind.SOUTH, Wind.WEST, Wind.NORTH]
        for i, player in enumerate(self.state.players):
            assert player.seat_wind == expected[i], (
                f"Seat {i}: expected {expected[i]}, got {player.seat_wind}"
            )

    def test_dealer_seat_wind_east(self) -> None:
        assert self.state.players[0].seat_wind == Wind.EAST


class TestNewGameDealerOffset:
    """Test that dealer_index shifts seat winds correctly."""

    def test_dealer_at_seat_2(self) -> None:
        state = new_game(seed=5, dealer_index=2)
        assert state.players[2].seat_wind == Wind.EAST
        assert state.players[3].seat_wind == Wind.SOUTH
        assert state.players[0].seat_wind == Wind.WEST
        assert state.players[1].seat_wind == Wind.NORTH
        assert state.players[2].hand.tile_count == 14
        for i in range(NUM_PLAYERS):
            if i != 2:
                assert state.players[i].hand.tile_count == 13


# ---------------------------------------------------------------------------
# Tile count invariants
# ---------------------------------------------------------------------------


class TestTileCountInvariants:
    def setup_method(self) -> None:
        self.state = new_game(seed=100)

    def _all_tile_counts(self) -> Counter:  # type: ignore[type-arg]
        """Count all tiles across hands and the wall."""
        c: Counter = Counter()  # type: ignore[type-arg]
        for player in self.state.players:
            for code, cnt in enumerate(player.hand.counts):
                c[code] += cnt
        wall = self.state.wall
        # Remaining live wall + dead wall
        for wt in wall.tiles[wall.live_pos:]:
            c[wt.code] += 1
        return c

    def test_total_tiles_sum_to_136(self) -> None:
        c = self._all_tile_counts()
        assert sum(c.values()) == TOTAL_TILES

    def test_each_tile_code_appears_four_times(self) -> None:
        c = self._all_tile_counts()
        for code in range(TILE_COUNT):
            assert c[code] == 4, f"Code {code}: expected 4 total, got {c[code]}"

    def test_wall_live_remaining_after_deal(self) -> None:
        # Dealer draws 14, others draw 13×3 = 53 total dealt
        expected_live = TOTAL_TILES - DEAD_WALL_SIZE - 53
        assert self.state.wall.live_remaining == expected_live


# ---------------------------------------------------------------------------
# Seed reproducibility
# ---------------------------------------------------------------------------


class TestSeedReproducibility:
    def test_same_seed_same_state(self) -> None:
        s1 = new_game(seed=77)
        s2 = new_game(seed=77)
        assert s1.players[0].hand.counts == s2.players[0].hand.counts
        assert s1.wall.tiles == s2.wall.tiles

    def test_different_seeds_different_deals(self) -> None:
        s1 = new_game(seed=1)
        s2 = new_game(seed=2)
        assert s1.players[0].hand.counts != s2.players[0].hand.counts


# ---------------------------------------------------------------------------
# Hypothesis property tests
# ---------------------------------------------------------------------------


@given(
    st.integers(min_value=0, max_value=2**31 - 1),
    st.integers(min_value=0, max_value=3),
)
@settings(max_examples=100)
def test_any_seed_produces_valid_game(seed: int, dealer: int) -> None:
    """For any seed and dealer, the initial state has correct tile distribution."""
    state = new_game(seed=seed, dealer_index=dealer)

    # Dealer has 14 tiles, others have 13
    assert state.players[dealer].hand.tile_count == 14
    for i in range(NUM_PLAYERS):
        if i != dealer:
            assert state.players[i].hand.tile_count == 13

    # All tiles account for correctly
    c: Counter = Counter()  # type: ignore[type-arg]
    for player in state.players:
        for code, cnt in enumerate(player.hand.counts):
            c[code] += cnt
    for wt in state.wall.tiles[state.wall.live_pos:]:
        c[wt.code] += 1

    assert sum(c.values()) == TOTAL_TILES
    for code in range(TILE_COUNT):
        assert c[code] == 4

# ---------------------------------------------------------------------------
# M1 Guide Demo Tests
# ---------------------------------------------------------------------------

def test_m1_guide_demo_game_state() -> None:
    from mahjong_engine.tiles import tile_to_str
    gs = new_game(mode=GameMode.HALF, dealer_index=0, seed=42)
    assert gs.mode.value == 'half'
    assert gs.round_wind.name == 'EAST'
    assert gs.round_number == 1
    assert gs.honba == 0
    assert gs.riichi_sticks == 0
    assert gs.dealer_index == 0
    assert gs.active_player_index == 0
    assert gs.wall.live_remaining == 69

    assert gs.players[0].seat_wind.name == 'EAST'
    assert gs.players[0].hand.tile_count == 14
    assert gs.players[0].score == 25000

    assert gs.players[1].seat_wind.name == 'SOUTH'
    assert gs.players[1].hand.tile_count == 13

    dealer = gs.players[0].hand
    tiles = []
    for t, c in enumerate(dealer.counts):
        tiles.extend([tile_to_str(t)] * c)
    assert ' '.join(tiles) == '1m 3m 5m 6m 7p 1s 4s 7s 8s 9s 9s 发 中 中'
