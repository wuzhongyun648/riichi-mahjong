"""Hand container: counts array, meld representation, and mutators.

The counts array (length 34) is the primary representation for all fast
computations (tenpai, shanten, yaku).  Aka (red-five) flags are tracked
separately as booleans and never affect tile codes.

See docs/tile-encoding.md for encoding specification.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from mahjong_engine.tiles import (
    AKA_5M_BASE,
    AKA_5P_BASE,
    AKA_5S_BASE,
    TILE_COUNT,
    parse_tiles,
    validate_tile,
)

_AKA_BASES = (AKA_5M_BASE, AKA_5P_BASE, AKA_5S_BASE)


# ---------------------------------------------------------------------------
# Meld
# ---------------------------------------------------------------------------


class MeldType(Enum):
    """Kind of exposed (or concealed-kan) meld."""

    CHI = "chi"            # sequence called from upper player
    PON = "pon"            # triplet
    KAN_OPEN = "kan_open"      # open quad — 大明杠 (daiminkan)
    KAN_ADDED = "kan_added"    # added quad — 加杠 (shouminkan); eligible for chankan
    KAN_CLOSED = "kan_closed"  # concealed quad — 暗杠 (ankan)


@dataclass(frozen=True)
class Meld:
    """An exposed (or concealed-kan) meld.

    Attributes:
        type: Kind of meld.
        tiles: Tile codes. Length 3 for CHI/PON, 4 for any KAN.
        called_from: Seat offset (1=upper, 2=opposite, 3=lower) of the player
                     whose discard or added tile triggered the call.
                     None for KAN_CLOSED.
        called_tile: Tile code of the tile that was called from another player.
                     None for KAN_CLOSED.
        aka_flags: Parallel bool tuple — True at position i means tiles[i] is
                   a red five.  Defaults to all-False if not supplied.
    """

    type: MeldType
    tiles: tuple[int, ...]
    called_from: int | None
    called_tile: int | None
    aka_flags: tuple[bool, ...] = ()

    def __post_init__(self) -> None:
        expected = 4 if "kan" in self.type.value else 3
        if len(self.tiles) != expected:
            raise ValueError(
                f"{self.type.name} requires {expected} tiles, got {len(self.tiles)}"
            )
        if not self.aka_flags:
            object.__setattr__(self, "aka_flags", tuple(False for _ in self.tiles))
        if len(self.aka_flags) != len(self.tiles):
            raise ValueError("aka_flags length must match tiles length")
        for t in self.tiles:
            validate_tile(t)


# ---------------------------------------------------------------------------
# Hand
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Hand:
    """Immutable concealed-hand state.

    Attributes:
        counts: Tile counts array of length 34.  counts[i] = number of tile i.
        melds: Exposed melds (and concealed kans) in declaration order.
        aka_5m: True if the hand contains a red 5-man.
        aka_5p: True if the hand contains a red 5-pin.
        aka_5s: True if the hand contains a red 5-sou.

    Invariants:
        len(counts) == 34
        0 <= counts[i] <= 4  for all i
        sum(counts) is 1-14 depending on game phase
    """

    counts: tuple[int, ...]
    melds: tuple[Meld, ...] = ()
    aka_5m: bool = False
    aka_5p: bool = False
    aka_5s: bool = False

    def __post_init__(self) -> None:
        if len(self.counts) != TILE_COUNT:
            raise ValueError(f"counts must have length {TILE_COUNT}, got {len(self.counts)}")
        for i, c in enumerate(self.counts):
            if not 0 <= c <= 4:
                raise ValueError(f"counts[{i}] = {c}: must be 0-4")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def tile_count(self) -> int:
        """Number of tiles in the concealed portion of the hand."""
        return sum(self.counts)

    @property
    def meld_count(self) -> int:
        """Number of exposed melds (including concealed kans)."""
        return len(self.melds)

    @property
    def aka_count(self) -> int:
        """Number of red-five tiles in the concealed hand."""
        return int(self.aka_5m) + int(self.aka_5p) + int(self.aka_5s)

    # ------------------------------------------------------------------
    # Mutators (return new Hand — original is unchanged)
    # ------------------------------------------------------------------

    def add_tile(self, tile: int, is_aka: bool = False) -> Hand:
        """Return a new Hand with one tile added to the concealed portion.

        Args:
            tile: Tile code 0-33.
            is_aka: True if the tile is a red five.

        Returns:
            New Hand with the tile added.

        Raises:
            ValueError: If tile already has 4 copies, or is_aka is True for a
                        non-five tile.
        """
        validate_tile(tile)
        if is_aka and tile not in _AKA_BASES:
            raise ValueError(f"Tile {tile} cannot be a red five (not a 5-tile)")
        new_counts = list(self.counts)
        if new_counts[tile] >= 4:
            raise ValueError(f"Cannot add tile {tile}: already 4 copies in hand")
        new_counts[tile] += 1
        return replace(
            self,
            counts=tuple(new_counts),
            aka_5m=self.aka_5m or (is_aka and tile == AKA_5M_BASE),
            aka_5p=self.aka_5p or (is_aka and tile == AKA_5P_BASE),
            aka_5s=self.aka_5s or (is_aka and tile == AKA_5S_BASE),
        )

    def remove_tile(self, tile: int, remove_aka: bool = False) -> Hand:
        """Return a new Hand with one tile removed from the concealed portion.

        Args:
            tile: Tile code 0-33.
            remove_aka: If True, also clears the aka flag for this tile type.
                        Use this when the specific removed tile is confirmed to
                        be the red five.

        Returns:
            New Hand with the tile removed.

        Raises:
            ValueError: If the tile is not present in the hand.
        """
        validate_tile(tile)
        new_counts = list(self.counts)
        if new_counts[tile] == 0:
            raise ValueError(f"Tile {tile} not in hand")
        new_counts[tile] -= 1
        return replace(
            self,
            counts=tuple(new_counts),
            aka_5m=self.aka_5m and not (remove_aka and tile == AKA_5M_BASE),
            aka_5p=self.aka_5p and not (remove_aka and tile == AKA_5P_BASE),
            aka_5s=self.aka_5s and not (remove_aka and tile == AKA_5S_BASE),
        )

    def add_meld(self, meld: Meld) -> Hand:
        """Return a new Hand with a meld appended."""
        return replace(self, melds=(*self.melds, meld))

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def empty(cls) -> Hand:
        """Return an empty hand (no tiles, no melds)."""
        return cls(counts=tuple([0] * TILE_COUNT))

    @classmethod
    def from_tile_list(
        cls,
        tiles: list[tuple[int, bool]],
        melds: tuple[Meld, ...] = (),
    ) -> Hand:
        """Build a Hand from a list of (tile_code, is_aka) pairs.

        Useful for tests and CLI input.

        Args:
            tiles: List of (tile_code, is_aka) pairs.
            melds: Optional exposed melds.
        """
        hand = cls(counts=tuple([0] * TILE_COUNT), melds=melds)
        for tile, is_aka in tiles:
            hand = hand.add_tile(tile, is_aka)
        return hand

    @classmethod
    def from_str(
        cls,
        s: str,
        melds: tuple[Meld, ...] = (),
    ) -> Hand:
        """Build a Hand from a space-separated tile string.

        Example:
            Hand.from_str("1m 2m 3m 赤5p 7p 8p 9p 1s 2s 3s 东 东 东")

        Args:
            s: Space-separated tile string (see docs/tile-encoding.md §4).
            melds: Optional exposed melds.
        """
        return cls.from_tile_list(parse_tiles(s), melds)
