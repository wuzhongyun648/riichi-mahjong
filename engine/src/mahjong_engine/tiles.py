"""Tile encoding, parsing, and display utilities for Riichi Mahjong.

Encoding (docs/tile-encoding.md):
    Man (manzu):  1m-9m  →   0-8
    Pin (pinzu):  1p-9p  →   9-17
    Sou (souzu):  1s-9s  →  18-26
    Honors:       East South West North Haku Hatsu Chun  →  27-33

Hand state is represented as counts: list[int] of length 34 for all
fast computations (tenpai, shanten, yaku). String representations are
used only for I/O, logs, and tests.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TILE_COUNT: int = 34

MAN_START, MAN_END = 0, 8
PIN_START, PIN_END = 9, 17
SOU_START, SOU_END = 18, 26
HONOR_START, HONOR_END = 27, 33

EAST, SOUTH, WEST, NORTH = 27, 28, 29, 30
HAKU, HATSU, CHUN = 31, 32, 33

# Base tile code for each red-five variant
AKA_5M_BASE: int = 4   # 5m
AKA_5P_BASE: int = 13  # 5p
AKA_5S_BASE: int = 22  # 5s

_AKA_BASES: frozenset[int] = frozenset({AKA_5M_BASE, AKA_5P_BASE, AKA_5S_BASE})

_HONOR_NAMES: tuple[str, ...] = ("东", "南", "西", "北", "白", "发", "中")
_HONOR_BY_NAME: dict[str, int] = {name: HONOR_START + i for i, name in enumerate(_HONOR_NAMES)}
_SUIT_OFFSET: dict[str, int] = {"m": MAN_START, "p": PIN_START, "s": SOU_START}

# ---------------------------------------------------------------------------
# Predicates
# ---------------------------------------------------------------------------


def is_manzu(tile: int) -> bool:
    """Return True for 1m-9m (codes 0-8)."""
    return MAN_START <= tile <= MAN_END


def is_pinzu(tile: int) -> bool:
    """Return True for 1p-9p (codes 9-17)."""
    return PIN_START <= tile <= PIN_END


def is_souzu(tile: int) -> bool:
    """Return True for 1s-9s (codes 18-26)."""
    return SOU_START <= tile <= SOU_END


def is_honor(tile: int) -> bool:
    """Return True for wind/dragon tiles (codes 27-33)."""
    return HONOR_START <= tile <= HONOR_END


def is_wind(tile: int) -> bool:
    """Return True for wind tiles (East-North, codes 27-30)."""
    return EAST <= tile <= NORTH


def is_dragon(tile: int) -> bool:
    """Return True for dragon tiles (Haku/Hatsu/Chun, codes 31-33)."""
    return HAKU <= tile <= CHUN


def is_terminal(tile: int) -> bool:
    """Return True for terminal tiles: 1m/9m/1p/9p/1s/9s."""
    if is_honor(tile):
        return False
    pos = tile % 9  # 0 = "1"-tile, 8 = "9"-tile within the suit
    return pos == 0 or pos == 8


def is_yaochuuhai(tile: int) -> bool:
    """Return True for terminals and honors (幺九牌)."""
    return is_terminal(tile) or is_honor(tile)


def is_chuuchanpai(tile: int) -> bool:
    """Return True for middle tiles (not yaochuuhai)."""
    return not is_yaochuuhai(tile)


def is_suited(tile: int) -> bool:
    """Return True for man/pin/sou tiles."""
    return not is_honor(tile)


# ---------------------------------------------------------------------------
# Accessors
# ---------------------------------------------------------------------------


def tile_number(tile: int) -> int:
    """Return the numerical value 1-9 for suited tiles.

    For honors, returns 1-7 in declaration order (East=1 … Chun=7).
    """
    if is_honor(tile):
        return tile - HONOR_START + 1
    return tile % 9 + 1


def tile_suit(tile: int) -> str:
    """Return 'm', 'p', 's', or 'z' (honor)."""
    if is_manzu(tile):
        return "m"
    if is_pinzu(tile):
        return "p"
    if is_souzu(tile):
        return "s"
    return "z"


# ---------------------------------------------------------------------------
# String conversion
# ---------------------------------------------------------------------------


def tile_to_str(tile: int, is_aka: bool = False) -> str:
    """Convert a tile code to human-readable string.

    Args:
        tile: Tile code 0-33.
        is_aka: If True and tile is a five-tile, returns the red-five form.

    Returns:
        Examples: "1m", "赤5p", "东"

    Raises:
        ValueError: If tile code is out of range.
    """
    validate_tile(tile)
    if is_aka:
        if tile not in _AKA_BASES:
            raise ValueError(f"Tile {tile} cannot be aka (not a 5-tile)")
        return f"赤5{tile_suit(tile)}"
    if is_honor(tile):
        return _HONOR_NAMES[tile - HONOR_START]
    return f"{tile_number(tile)}{tile_suit(tile)}"


def parse_tile(s: str) -> tuple[int, bool]:
    """Parse a single tile string into (tile_code, is_aka).

    Accepts:
        Suited:  "1m"-"9m", "1p"-"9p", "1s"-"9s"
        Red five: "赤5m", "赤5p", "赤5s"
        Honors:  "东", "南", "西", "北", "白", "发", "中"

    Returns:
        (tile_code, is_aka) — is_aka is True only for red-five strings.

    Raises:
        ValueError: If the string cannot be parsed.
    """
    s = s.strip()
    if not s:
        raise ValueError("Empty tile string")

    # Honor check
    if s in _HONOR_BY_NAME:
        return _HONOR_BY_NAME[s], False

    # Red-five check: "赤5m" / "赤5p" / "赤5s"
    if s.startswith("赤5") and len(s) == 3 and s[2] in _SUIT_OFFSET:
        code = _SUIT_OFFSET[s[2]] + 4  # 5 → index 4 within suit
        return code, True

    # Suited tile: e.g. "1m", "9s"
    if len(s) >= 2 and s[-1] in _SUIT_OFFSET:
        try:
            num = int(s[:-1])
        except ValueError:
            raise ValueError(f"Invalid tile string: {s!r}") from None
        if not 1 <= num <= 9:
            raise ValueError(f"Tile number out of range in {s!r}: must be 1-9")
        return _SUIT_OFFSET[s[-1]] + (num - 1), False

    raise ValueError(f"Cannot parse tile string: {s!r}")


def parse_tiles(s: str) -> list[tuple[int, bool]]:
    """Parse a space-separated sequence of tile strings.

    Example:
        parse_tiles("1m 赤5p 东") == [(0, False), (13, True), (27, False)]
    """
    return [parse_tile(tok) for tok in s.split()]


def tiles_to_str(tiles: list[tuple[int, bool]]) -> str:
    """Convert a list of (tile_code, is_aka) pairs to a display string."""
    return " ".join(tile_to_str(t, a) for t, a in tiles)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_tile(tile: int) -> None:
    """Raise ValueError if tile code is outside 0-33."""
    if not 0 <= tile <= 33:
        raise ValueError(f"Tile code {tile} is out of range 0-33")


# ---------------------------------------------------------------------------
# Game-logic helpers
# ---------------------------------------------------------------------------


def next_dora(indicator: int) -> int:
    """Return the active dora tile for a given dora-indicator tile.

    Rules (docs/rules.md §3.3):
        Suited tiles: number wraps 9→1 within the same suit.
        Winds: East→South→West→North→East (27→28→29→30→27).
        Dragons: Haku→Hatsu→Chun→Haku (31→32→33→31).

    Args:
        indicator: Tile code of the dora indicator.

    Returns:
        Tile code of the actual dora tile.
    """
    validate_tile(indicator)
    if is_manzu(indicator):
        return MAN_START + (indicator - MAN_START + 1) % 9
    if is_pinzu(indicator):
        return PIN_START + (indicator - PIN_START + 1) % 9
    if is_souzu(indicator):
        return SOU_START + (indicator - SOU_START + 1) % 9
    if is_wind(indicator):
        return EAST + (indicator - EAST + 1) % 4
    # dragon
    return HAKU + (indicator - HAKU + 1) % 3


def make_counts(tiles: list[int]) -> list[int]:
    """Build a counts[34] array from a flat list of tile codes.

    Args:
        tiles: List of tile codes (0-33 each).

    Returns:
        List of length 34 where index i is the count of tile i.

    Raises:
        ValueError: If any tile code is out of range or any count exceeds 4.
    """
    counts = [0] * TILE_COUNT
    for t in tiles:
        validate_tile(t)
        counts[t] += 1
    for i, c in enumerate(counts):
        if c > 4:
            raise ValueError(f"Tile {i} appears {c} times (max 4)")
    return counts


def counts_to_tiles(counts: list[int]) -> list[int]:
    """Expand a counts[34] array back to a flat tile list.

    Returns tiles in code order (0→33).
    """
    return [i for i, c in enumerate(counts) for _ in range(c)]
