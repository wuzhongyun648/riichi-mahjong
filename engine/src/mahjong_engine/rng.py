"""Seedable shuffle utilities for wall construction.

Using a seeded RNG ensures bugs are reproducible and replays are deterministic.
The stdlib ``random.Random`` is sufficient — cryptographic quality is not needed.
"""

from __future__ import annotations

import random
from typing import TypeVar

T = TypeVar("T")


def shuffled(items: list[T], seed: int | None = None) -> list[T]:
    """Return a shuffled copy of *items* using an optionally seeded RNG.

    The original list is not modified.

    Args:
        items: Sequence to shuffle.
        seed: Integer seed for reproducibility.  Pass ``None`` (default) for a
              non-deterministic shuffle.

    Returns:
        A new list containing the same elements in a shuffled order.

    Complexity:
        O(n) — Fisher-Yates via ``random.Random.shuffle``.
    """
    result = list(items)
    rng = random.Random(seed)
    rng.shuffle(result)
    return result
