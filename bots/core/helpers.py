"""Reusable low-level helpers for bot implementations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def farm_for(observation: Mapping[str, Any]) -> Mapping[str, Any]:
    return observation["farms"][int(observation.get("player", 0))]


def tile_at(tiles: Sequence[Sequence[Any]], position: tuple[int, int]) -> Any:
    x, y = position
    if 0 <= y < len(tiles) and 0 <= x < len(tiles[y]):
        return tiles[y][x]
    return "LOCKED"


def fixed_route_unit_commands(
    observation: Mapping[str, Any],
    *,
    crop: str,
    routes: Sequence[Sequence[str]],
    harvest_after_days: int,
) -> tuple[list[Any], list[list[Any]]]:
    farm = farm_for(observation)
    day = int(observation.get("day", 0))
    hour = int(observation.get("hour", int(observation.get("step", 0)) % 24))
    positions = [tuple(farm.get("farmer", (4, 4)))] + [
        tuple(position) for position in farm.get("hands", ()) or ()
    ]
    tiles = farm.get("tiles", ()) or ()
    seeds = observation.get("private", {}).get("seeds", {}) or {}
    seed_quantity = int(seeds.get(crop, 0) or 0)

    commands: list[list[Any]] = []
    for index, position in enumerate(positions):
        tile = tile_at(tiles, position)
        command: list[Any] | None = None
        if isinstance(tile, dict) and tile.get("kind") == "PLANT":
            if (
                int(tile.get("yield_units", 0) or 0) > 0
                and day - int(tile.get("planted_day", day)) >= harvest_after_days
            ):
                command = ["HARVEST"]
            elif not tile.get("watered_today", False):
                command = ["WATER"]
        elif index < 2 and tile is None and seed_quantity > 0:
            command = ["PLANT", crop]
            seed_quantity -= 1

        if command is None:
            if index >= 2 and hour == 1:
                command = ["NORTH"]
            else:
                route_index = max(0, (hour - (2 if index < 2 else 3)) // 2)
                route = routes[index if index < 2 else index - 2]
                command = [route[route_index % len(route)]]
        commands.append(command)

    return commands[0], commands[1:]


def opening_seed_orders(
    observation: Mapping[str, Any],
    *,
    seed: str,
    seed_price: int,
    land_price: int = 1000,
) -> list[list[Any]]:
    farm = farm_for(observation)
    money = float(farm.get("money", 0.0))
    seed_quantity = max(0, int((money - land_price - 4) // seed_price))
    return [["BUY_LAND"], ["BUY_SEED", seed, seed_quantity]]


def daily_hire_orders(hour: int, hire_count: int) -> list[list[Any]]:
    return [["HIRE"] for _ in range(hire_count)] if hour == 0 else []
