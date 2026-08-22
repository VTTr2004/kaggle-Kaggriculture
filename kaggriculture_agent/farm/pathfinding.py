"""Movement helpers.

Locked quadrants are traversable in Kaggriculture, so Manhattan routing is
legal. Keeping this behind a module makes A* or congestion-aware routing a
drop-in replacement later.
"""

from __future__ import annotations

from ..models import Command, Position


def distance(start: Position, target: Position) -> int:
    return abs(target[0] - start[0]) + abs(target[1] - start[1])


def next_move(start: Position, target: Position) -> Command:
    """Return one official movement command toward ``target``."""
    sx, sy = start
    tx, ty = target
    if sx < tx:
        return ("EAST",)
    if sx > tx:
        return ("WEST",)
    if sy < ty:
        return ("SOUTH",)
    if sy > ty:
        return ("NORTH",)
    return ("PASS",)
