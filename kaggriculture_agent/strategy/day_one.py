"""Deterministic first-day farm opening.

The opening is intentionally simple: buy the NE quadrant, hire three hands,
fill the two top quadrants with Wheat, then run two planter routes with two
one-tile-lag watering followers.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..models import Command, GameState, MarketIntent

WHEAT_SEED_COUNT = 50

# The black and red routes are the two top-quadrant planter routes. The yellow
# route is represented by the one-tile-lag follower schedule below.
ROUTE_BLACK: tuple[str, ...] = (
    "WEST",
    "WEST",
    "WEST",
    "WEST",
    "NORTH",
    "NORTH",
    "NORTH",
    "NORTH",
    "EAST",
    "EAST",
    "EAST",
    "EAST",
    "SOUTH",
    "SOUTH",
    "SOUTH",
    "SOUTH",
)
ROUTE_RED: tuple[str, ...] = (
    "EAST",
    "EAST",
    "EAST",
    "EAST",
    "NORTH",
    "NORTH",
    "NORTH",
    "NORTH",
    "WEST",
    "WEST",
    "WEST",
    "WEST",
    "SOUTH",
    "SOUTH",
    "SOUTH",
    "SOUTH",
)
PLANTER_ROUTES: tuple[tuple[str, ...], ...] = (ROUTE_BLACK, ROUTE_RED)


def _quadrant(x: int, y: int, board_size: int) -> str:
    half = board_size // 2
    return ("N" if y < half else "S") + ("W" if x < half else "E")


def _empty_owned_tiles(state: GameState) -> int:
    return sum(
        1
        for y, row in enumerate(state.tiles)
        for x, tile in enumerate(row)
        if tile is None and _quadrant(x, y, state.board_size) in state.unlocked_quadrants
    )


def first_day_market_intents(state: GameState) -> tuple[MarketIntent, ...]:
    """Return the fixed opening orders for a fresh game."""

    if state.day != 0 or state.step != 0:
        return ()

    half = state.board_size // 2
    empty_after_ne = _empty_owned_tiles(state)
    if "NE" not in state.unlocked_quadrants:
        empty_after_ne += half * half

    intents = [
        MarketIntent(("BUY_LAND",), 1400.0, 1000.0, "open NE on the first turn"),
        MarketIntent(("HIRE",), 1300.0, reason="opening planter"),
        MarketIntent(("HIRE",), 1300.0, reason="opening NW waterer"),
        MarketIntent(("HIRE",), 1300.0, reason="opening NE waterer"),
    ]
    quantity = min(WHEAT_SEED_COUNT, max(0, empty_after_ne))
    if quantity:
        intents.append(
            MarketIntent(
                ("BUY_SEED", "WHEAT", quantity),
                1200.0,
                float(quantity * 10),
                "fill the two top quadrants with Wheat",
            )
        )
    return tuple(intents)


def _tile(state: GameState, position: tuple[int, int]):
    x, y = position
    if not (0 <= y < len(state.tiles) and 0 <= x < len(state.tiles[y])):
        return "LOCKED"
    return state.tiles[y][x]


def _route_command(route: Sequence[str], index: int) -> Command:
    return (route[index % len(route)],)


def _planter_command(state: GameState, unit_index: int) -> Command:
    position = state.unit_positions[unit_index]
    if _tile(state, position) is None:
        return ("PLANT", "WHEAT")
    # Step 1 plants the starting tile. Thereafter movement and planting
    # alternate, so movement index 0 is used on step 2.
    movement_index = max(0, (state.step - 2) // 2)
    return _route_command(PLANTER_ROUTES[unit_index], movement_index)


def _follower_command(state: GameState, unit_index: int) -> Command:
    paired_planter = unit_index - 2
    position = state.unit_positions[unit_index]
    tile = _tile(state, position)
    if (
        isinstance(tile, dict)
        and tile.get("kind") == "PLANT"
        and not tile.get("watered_today", False)
    ):
        return ("WATER",)
    if state.step == 1:
        return ("NORTH",)
    movement_index = max(0, (state.step - 3) // 2)
    return _route_command(PLANTER_ROUTES[paired_planter], movement_index)


def first_day_unit_commands(state: GameState) -> tuple[Command, ...]:
    """Return one fixed action per unit for day zero."""

    if state.day != 0 or not state.unit_positions:
        return tuple(("PASS",) for _ in state.unit_positions)
    if state.step == 0:
        return tuple(("PASS",) for _ in state.unit_positions)

    commands: list[Command] = []
    for unit_index in range(len(state.unit_positions)):
        if unit_index < 2:
            commands.append(_planter_command(state, unit_index))
        elif unit_index < 4:
            commands.append(_follower_command(state, unit_index))
        else:
            commands.append(("PASS",))
    return tuple(commands)
