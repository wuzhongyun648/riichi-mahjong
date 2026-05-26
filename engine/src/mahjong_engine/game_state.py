"""Immutable GameState snapshot for Riichi Mahjong.

All game-phase state transitions are pure functions with the signature:
    (GameState, Action) -> (GameState, list[Event])
implemented in game_engine.py (M5 scope).

This module provides only:
  - Data structures (Wind, GameMode, PlayerState, GameState)
  - Initial state construction via new_game()

References: docs/rules.md §1.1-§1.7
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from mahjong_engine.hand import Hand
from mahjong_engine.wall import WallState, build_wall

# ---------------------------------------------------------------------------
# Constants (docs/rules.md §1.2)
# ---------------------------------------------------------------------------

INITIAL_SCORE: int = 25_000
NUM_PLAYERS: int = 4


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class Wind(Enum):
    """Seat or round wind, in clockwise order starting from East."""

    EAST = 0
    SOUTH = 1
    WEST = 2
    NORTH = 3


class GameMode(Enum):
    """Supported game formats (docs/rules.md §1.1)."""

    EAST = "east"   # 東風戦: East rounds only (4 hands minimum)
    HALF = "half"   # 半荘戦: East + South rounds (8 hands minimum)


# ---------------------------------------------------------------------------
# PlayerState
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlayerState:
    """Immutable state for a single player within one round.

    Attributes:
        hand: Concealed hand tiles and melds.
        river: Discarded tile codes in order (does not include called tiles).
        score: Current point total.
        seat_wind: Player's seat wind relative to the dealer (dealer = East).
        in_riichi: True once the player has declared riichi.
        riichi_turn: Value of GameState.turn_count when riichi was declared.
        double_riichi: True if W-riichi (双立直) was declared.
    """

    hand: Hand
    river: tuple[int, ...]
    score: int
    seat_wind: Wind
    in_riichi: bool = False
    riichi_turn: int | None = None
    double_riichi: bool = False


# ---------------------------------------------------------------------------
# GameState
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GameState:
    """Complete, immutable snapshot of the current round.

    A full game (半荘/東風) consists of a sequence of rounds.  Each round
    produces a new GameState at each draw/discard action.

    Attributes:
        mode: East-only or half (east+south) game format.
        round_wind: Current round wind (East or South for half game).
        round_number: 1-4 for East rounds; 1-4 again for South rounds.
        honba: Consecutive-dealer count (本場), incremented on dealer win/draw.
        riichi_sticks: Number of 1000-pt riichi bets sitting on the table.
        dealer_index: Seat index (0-3) of the current dealer.
        active_player_index: Seat index whose turn it currently is.
        players: Tuple of NUM_PLAYERS PlayerStates, indexed by seat (0=East).
        wall: Current wall snapshot.
        turn_count: Total draw turns completed in this round (0 at start).
    """

    mode: GameMode
    round_wind: Wind
    round_number: int
    honba: int
    riichi_sticks: int
    dealer_index: int
    active_player_index: int
    players: tuple[PlayerState, ...]
    wall: WallState
    turn_count: int = 0


# ---------------------------------------------------------------------------
# Initial state construction
# ---------------------------------------------------------------------------


def _deal_initial_hands(
    wall: WallState,
    dealer_index: int,
) -> tuple[tuple[Hand, ...], WallState]:
    """Deal starting tiles: dealer receives 14, others receive 13.

    Tiles are dealt sequentially from the front of the live wall in seat order
    starting from the dealer.  (The precise deal ceremony — 4-4-4-1 rounds —
    does not affect the resulting hands and is omitted here for simplicity;
    Tenhou-log compatibility will be addressed in M6.)

    Args:
        wall: Pre-shuffled wall with live_pos == 0.
        dealer_index: Seat index of the dealer (0-3).

    Returns:
        (hands, updated_wall) where hands[i] is the Hand for seat i.
    """
    hands: list[Hand] = [Hand.empty() for _ in range(NUM_PLAYERS)]
    pos = wall.live_pos

    # Dealer gets 14 tiles (already holds first draw), others get 13
    draw_counts = [13] * NUM_PLAYERS
    draw_counts[dealer_index] = 14

    # Deal in seat order: dealer first, then clockwise
    for offset in range(NUM_PLAYERS):
        seat = (dealer_index + offset) % NUM_PLAYERS
        for _ in range(draw_counts[seat]):
            wt = wall.tiles[pos]
            hands[seat] = hands[seat].add_tile(wt.code, wt.is_aka)
            pos += 1

    updated_wall = replace(wall, live_pos=pos)
    return tuple(hands), updated_wall


def new_game(
    mode: GameMode = GameMode.HALF,
    dealer_index: int = 0,
    seed: int | None = None,
) -> GameState:
    """Construct the initial GameState for a new round.

    Args:
        mode: Game format (east or half).  Affects when the game ends (M5).
        dealer_index: Seat index of the dealer (0-3).
        seed: RNG seed for the wall shuffle.  ``None`` for non-deterministic.

    Returns:
        A GameState with hands dealt and the wall ready for the first draw.

    References: docs/rules.md §1.1, §1.2, §3.5
    """
    wall = build_wall(mode="yonma", seed=seed)
    hands, wall = _deal_initial_hands(wall, dealer_index)

    # Seat winds: dealer = East, then South, West, North clockwise
    def _seat_wind(seat: int) -> Wind:
        return Wind((seat - dealer_index) % NUM_PLAYERS)

    players = tuple(
        PlayerState(
            hand=hands[seat],
            river=(),
            score=INITIAL_SCORE,
            seat_wind=_seat_wind(seat),
        )
        for seat in range(NUM_PLAYERS)
    )

    return GameState(
        mode=mode,
        round_wind=Wind.EAST,
        round_number=1,
        honba=0,
        riichi_sticks=0,
        dealer_index=dealer_index,
        active_player_index=dealer_index,
        players=players,
        wall=wall,
        turn_count=0,
    )
