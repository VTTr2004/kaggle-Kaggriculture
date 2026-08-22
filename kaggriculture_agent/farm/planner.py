"""Farm-owned scheduling and pathfinding from tasks to unit intentions."""

from __future__ import annotations

from ..models import FarmFeatures, FarmTask, GameState, UnitIntent
from .pathfinding import distance, next_move


def _can_do(task: FarmTask, inventory: object) -> bool:
    if task.required_item is None:
        return True
    getter = getattr(inventory, "get", None)
    return bool(getter and getter(task.required_item, 0) > 0)


def plan_unit_actions(
    state: GameState, farm: FarmFeatures, selected_crop: str | None
) -> tuple[UnitIntent, ...]:
    """Assign work and movement; economic ranking stays outside this module."""
    positions = state.unit_positions
    inventories = state.inventories
    assignments: dict[int, FarmTask] = {}
    used_targets: set[tuple[int, int]] = set()

    candidates: list[tuple[float, int, FarmTask]] = []
    for unit_index, position in enumerate(positions):
        inventory = inventories[unit_index] if unit_index < len(inventories) else {}
        for task in farm.tasks:
            if _can_do(task, inventory):
                score = task.priority - distance(position, task.target) * 11.0
                if position == task.target:
                    score += 45.0
                candidates.append((score, unit_index, task))
    candidates.sort(key=lambda item: (-item[0], item[1], item[2].target[1], item[2].target[0]))
    for _, unit_index, task in candidates:
        if unit_index in assignments or task.target in used_targets:
            continue
        assignments[unit_index] = task
        used_targets.add(task.target)
        if len(assignments) == len(positions):
            break

    # Seeds purchased this turn arrive after unit actions and cannot be used yet.
    seeds = state.private.get("seeds", {}) or {}
    available = int(seeds.get(selected_crop, 0) or 0) if selected_crop else 0
    empty = [position for position in farm.empty_tiles if position not in used_targets]
    for unit_index, position in enumerate(positions):
        if unit_index in assignments or available <= 0 or not selected_crop or not empty:
            continue
        target = min(empty, key=lambda value: (distance(position, value), value[1], value[0]))
        empty.remove(target)
        assignments[unit_index] = FarmTask(
            target=target,
            command=("PLANT", selected_crop),
            priority=480.0,
            category="plant",
            reason=f"plant shared-strategy crop {selected_crop}",
        )
        available -= 1

    intents: list[UnitIntent] = []
    for unit_index, position in enumerate(positions):
        task = assignments.get(unit_index)
        if task is None:
            command = ("PASS",)
            target = None
            priority = 0.0
            reason = "no feasible farm task"
        elif position == task.target:
            command = task.command
            target = task.target
            priority = task.priority
            reason = task.reason
        else:
            command = next_move(position, task.target)
            target = task.target
            priority = task.priority
            reason = f"move toward {task.category}: {task.reason}"
        intents.append(UnitIntent(unit_index, command, target, priority, reason))
    return tuple(intents)
