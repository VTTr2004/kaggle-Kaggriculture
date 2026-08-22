"""Farm intelligence: turn the board into prioritized, strategy-neutral tasks."""

from __future__ import annotations

from typing import Any

from ..domain import CROPS
from ..models import FarmFeatures, FarmTask, GameState


def _plant_tasks(state: GameState, x: int, y: int, tile: dict[str, Any]) -> list[FarmTask]:
    tasks: list[FarmTask] = []
    crop = str(tile.get("crop", ""))
    spec = CROPS.get(crop)
    if spec is None:
        return tasks

    age = state.day - int(tile.get("planted_day", state.day))
    yield_units = int(tile.get("yield_units", 0) or 0)
    watered = bool(tile.get("watered_today", False))
    unwatered = int(tile.get("consecutive_unwatered", 0) or 0)
    last_safe_day = state.day >= state.total_days - 1

    ready = age >= spec.first_yield_day and yield_units > 0
    at_peak = spec.ongoing or age >= spec.max_yield_day or last_safe_day
    if ready and at_peak:
        tasks.append(
            FarmTask(
                target=(x, y),
                command=("HARVEST",),
                priority=1120.0 if not spec.ongoing else 980.0 + yield_units * 15,
                category="harvest",
                reason=f"{crop} has {yield_units} units ready",
            )
        )

    if not watered and not (ready and at_peak and not spec.ongoing):
        urgency = 920.0 + state.hour * 7.0 + unwatered * 60.0
        tasks.append(
            FarmTask(
                target=(x, y),
                command=("WATER",),
                priority=urgency,
                category="water",
                reason=f"{crop} must be watered before end of day",
            )
        )
    return tasks


def _animal_tasks(state: GameState, x: int, y: int, tile: dict[str, Any]) -> list[FarmTask]:
    tasks: list[FarmTask] = []
    animal = str(tile.get("animal", "animal"))
    if int(tile.get("yield_units", 0) or 0) > 0:
        tasks.append(FarmTask((x, y), ("HARVEST",), 990.0, "harvest", f"collect {animal} product"))
    if not bool(tile.get("fed_today", False)):
        tasks.append(
            FarmTask(
                (x, y),
                ("FEED",),
                1060.0 + state.hour * 7.0,
                "feed",
                f"feed {animal}",
                required_item="WHEAT",
            )
        )
    if bool(tile.get("fertilizer_available", False)):
        tasks.append(
            FarmTask(
                (x, y),
                ("COLLECT_FERTILIZER",),
                720.0,
                "fertilizer",
                f"collect fertilizer from {animal}",
            )
        )
    if not bool(tile.get("cared_today", False)):
        tasks.append(FarmTask((x, y), ("CARE",), 620.0, "care", f"care for {animal}"))
    return tasks


def analyze_farm(state: GameState) -> FarmFeatures:
    """Extract tasks and capacity without making economic decisions."""
    tasks: list[FarmTask] = []
    empty_tiles: list[tuple[int, int]] = []
    plants = animals = weeds = unlocked = 0

    for y, row in enumerate(state.tiles):
        for x, tile in enumerate(row):
            if tile == "LOCKED":
                continue
            unlocked += 1
            if tile is None:
                empty_tiles.append((x, y))
            elif isinstance(tile, dict) and tile.get("kind") == "WEED":
                weeds += 1
                tasks.append(FarmTask((x, y), ("DIG",), 560.0, "dig", "clear weed for future use"))
            elif isinstance(tile, dict) and tile.get("kind") == "PLANT":
                plants += 1
                tasks.extend(_plant_tasks(state, x, y, tile))
            elif isinstance(tile, dict) and "animal" in tile:
                animals += 1
                tasks.extend(_animal_tasks(state, x, y, tile))

    tasks.sort(key=lambda task: (-task.priority, task.target[1], task.target[0]))
    urgent = sum(task.priority >= 900.0 for task in tasks)
    return FarmFeatures(
        tasks=tuple(tasks),
        empty_tiles=tuple(empty_tiles),
        plant_count=plants,
        animal_count=animals,
        weed_count=weeds,
        urgent_count=urgent,
        unlocked_tile_count=unlocked,
    )
