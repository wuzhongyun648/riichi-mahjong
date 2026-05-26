"""Wall (live + dead) construction and immutable state for Riichi Mahjong.

Dead wall layout within ``WallState.tiles[-14:]``:
    indices  0-4  : dora indicator slots  (revealed 1 at start, +1 per kan)
    indices  5-9  : ura-dora indicator slots
    indices 10-13 : rinshan tile slots    (drawn from index 13 downward)

The live wall occupies ``tiles[live_pos : 136 - 14 - rinshan_drawn]``.
Each kan draws one rinshan tile from the dead-wall end and "borrows" one
tile from the live-wall end to keep the dead wall logically 14 tiles.

References: docs/rules.md §2.1, §3.1-§3.5
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from mahjong_engine.tiles import (
    AKA_5M_BASE,
    AKA_5P_BASE,
    AKA_5S_BASE,
    TILE_COUNT,
    next_dora,
    validate_tile,
)

# ---------------------------------------------------------------------------
# Constants (docs/rules.md §3.2)
# ---------------------------------------------------------------------------

DEAD_WALL_SIZE: int = 14
TOTAL_TILES: int = 136  # 34 kinds × 4 copies
LIVE_WALL_SIZE: int = TOTAL_TILES - DEAD_WALL_SIZE  # 122
INITIAL_DORA_REVEALED: int = 1
MAX_DORA_REVEALED: int = 5   # 1 initial + 1 per kan, max 4 kans
MAX_KAN: int = 4

# Dead-wall slot positions (relative to dead-wall start = index 122)
_DORA_SLOT_START: int = 0
_URA_SLOT_START: int = 5
_RINSHAN_SLOT_START: int = 10  # tiles[122+10..122+13]; draw from 13 down


# ---------------------------------------------------------------------------
# WallTile — a tile with its aka flag
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WallTile:
    """Single tile entry in the wall, bundling the tile code with its aka flag."""

    code: int
    is_aka: bool = False

    def __post_init__(self) -> None:
        validate_tile(self.code)


# ---------------------------------------------------------------------------
# WallState — immutable wall snapshot
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WallState:
    """Immutable snapshot of the wall at any point in a game.

    Attributes:
        tiles: All 136 tiles in deal order.  The last 14 are the dead wall.
        live_pos: Front index of the live wall (next tile to deal).
        rinshan_drawn: Number of rinshan tiles drawn so far (0-4).
        dora_revealed: Number of dora indicators currently face-up (1-5).

    Live wall:  ``tiles[live_pos : 122 - rinshan_drawn]``
    Dead wall:  ``tiles[122:]``  (always 14 tiles; rinshan draws reduce the
                effective live wall instead of physically moving tiles)
    """

    tiles: tuple[WallTile, ...]
    live_pos: int = 0
    rinshan_drawn: int = 0
    dora_revealed: int = INITIAL_DORA_REVEALED

    def __post_init__(self) -> None:
        if len(self.tiles) != TOTAL_TILES:
            raise ValueError(f"Wall must have {TOTAL_TILES} tiles, got {len(self.tiles)}")
        if not 0 <= self.rinshan_drawn <= MAX_KAN:
            raise ValueError(f"rinshan_drawn must be 0-{MAX_KAN}")
        if not 1 <= self.dora_revealed <= MAX_DORA_REVEALED:
            raise ValueError(f"dora_revealed must be 1-{MAX_DORA_REVEALED}")

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def dead_start(self) -> int:
        """Index where the dead wall begins in ``tiles``."""
        return TOTAL_TILES - DEAD_WALL_SIZE  # always 122

    @property
    def live_remaining(self) -> int:
        """Number of tiles remaining in the live wall."""
        # Each kan draw "consumes" one tile from the live-wall end
        return self.dead_start - self.rinshan_drawn - self.live_pos

    @property
    def dead_wall(self) -> tuple[WallTile, ...]:
        """The 14-tile dead-wall slice."""
        return self.tiles[self.dead_start:]

    @property
    def dora_indicators(self) -> tuple[WallTile, ...]:
        """Currently revealed dora-indicator tiles (1-5)."""
        dead = self.dead_wall
        return tuple(dead[_DORA_SLOT_START + i] for i in range(self.dora_revealed))

    @property
    def active_dora_tiles(self) -> tuple[int, ...]:
        """Tile codes of the actual dora tiles (indicator + 1 wrap)."""
        return tuple(next_dora(w.code) for w in self.dora_indicators)

    @property
    def ura_indicators(self) -> tuple[WallTile, ...]:
        """Ura-dora indicator tiles (same count as revealed dora; used on riichi win)."""
        dead = self.dead_wall
        return tuple(dead[_URA_SLOT_START + i] for i in range(self.dora_revealed))

    # ------------------------------------------------------------------
    # Peek helpers (do not advance state)
    # ------------------------------------------------------------------

    def peek_live(self) -> WallTile:
        """Return the next live-wall tile without advancing the pointer.

        Raises:
            IndexError: If the live wall is exhausted.
        """
        if self.live_remaining <= 0:
            raise IndexError("Live wall is exhausted")
        return self.tiles[self.live_pos]

    def peek_rinshan(self) -> WallTile:
        """Return the next rinshan tile without advancing the counter.

        Rinshan tiles are at dead_wall[13], [12], [11], [10] in that order.

        Raises:
            IndexError: If no rinshan tiles remain (4 kans already drawn).
        """
        if self.rinshan_drawn >= MAX_KAN:
            raise IndexError("No rinshan tiles remain (max 4 kans reached)")
        idx = self.dead_start + (_RINSHAN_SLOT_START + MAX_KAN - 1) - self.rinshan_drawn
        return self.tiles[idx]


# ---------------------------------------------------------------------------
# Wall construction
# ---------------------------------------------------------------------------


def _base_tiles() -> list[int]:
    """Return a list of 136 tile codes — each of 0-33 exactly four times."""
    return [t for t in range(TILE_COUNT) for _ in range(4)]


def _inject_aka(codes: list[int], rng: random.Random) -> list[WallTile]:
    """Convert a shuffled code list to WallTile objects, marking one of each
    five-tile as a red five.

    One copy each of 5m (code 4), 5p (code 13), 5s (code 22) will have
    ``is_aka=True``.  The choice of which copy is random (controlled by *rng*).

    Complexity: O(n)  — docs/rules.md §2.1
    """
    result: list[WallTile] = [WallTile(code=c) for c in codes]
    for aka_base in (AKA_5M_BASE, AKA_5P_BASE, AKA_5S_BASE):
        positions = [i for i, c in enumerate(codes) if c == aka_base]
        chosen = rng.choice(positions)
        result[chosen] = WallTile(code=aka_base, is_aka=True)
    return result


def build_wall(mode: str = "yonma", seed: int | None = None) -> WallState:
    """Build and return an initial WallState ready for dealing.

    Steps:
        1. Generate 136 base tile codes (each of 0-33 × 4).
        2. Shuffle with the provided seed.
        3. Mark one copy each of 5m/5p/5s as aka (red five).
        4. Wrap in WallState with live_pos=0, rinshan_drawn=0, dora_revealed=1.

    Args:
        mode: Game mode.  Only ``"yonma"`` (4-player) is implemented (M1 scope).
        seed: RNG seed for reproducibility.  ``None`` for non-deterministic.

    Returns:
        A freshly constructed WallState.

    Raises:
        NotImplementedError: If *mode* is not ``"yonma"``.

    References: docs/rules.md §2.1, §3.1-§3.5
    """
    if mode != "yonma":
        raise NotImplementedError(f"Mode {mode!r} is not yet implemented (see M9)")

    rng = random.Random(seed)
    base = _base_tiles()
    rng.shuffle(base)
    wall_tiles = _inject_aka(base, rng)

    return WallState(
        tiles=tuple(wall_tiles),
        live_pos=0,
        rinshan_drawn=0,
        dora_revealed=INITIAL_DORA_REVEALED,
    )
