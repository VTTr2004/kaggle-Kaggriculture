"""Farm-side crop planning primitives.

The crop constants mirror the official Kaggriculture environment:
https://github.com/Kaggle/kaggle-environments/blob/master/kaggle_environments/envs/kaggriculture/kaggriculture.py

This module deliberately does not forecast prices.  The economy branch supplies
prices indexed by day offset, and the farm branch evaluates integer planting
choices against that forecast.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ..models import FarmFeatures, FarmTask, GameState, UnitIntent
from .pathfinding import distance, next_move

# Deliberately static for the first farm-only search.  This is not connected to
# the economy forecaster; replace this table manually when the competition
# assumptions change.
HARDCODED_BASE_PRICES: dict[str, float] = {
    "WHEAT": 25.0,
    "CARROT": 35.0,
    "TOMATO": 60.0,
    "STRAWBERRY": 120.0,
    "MELON": 250.0,
}


@dataclass(frozen=True)
class CropRule:
    seed_cost: int
    first_yield_day: int
    max_yield_day: int
    interval: int
    max_yield: int
    ongoing: bool


OFFICIAL_CROPS: dict[str, CropRule] = {
    "WHEAT": CropRule(10, 2, 4, 0, 6, False),
    "CARROT": CropRule(20, 2, 3, 0, 4, False),
    "TOMATO": CropRule(50, 8, 8, 1, 4, True),
    "STRAWBERRY": CropRule(100, 10, 10, 2, 4, True),
    "MELON": CropRule(80, 10, 12, 0, 6, False),
}


@dataclass(frozen=True)
class PlantState:
    """The part of a live plant observation needed by the planner."""

    crop: str
    planted_day: int
    yield_units: int = 0


@dataclass(frozen=True)
class FarmSnapshot:
    current_day: int
    remaining_days: int
    free_tiles: int
    existing_plants: tuple[PlantState, ...]


@dataclass(frozen=True)
class HarvestEvent:
    day: int
    units: int
    price: float
    revenue: float


@dataclass(frozen=True)
class CropProjection:
    crop: str
    planted_day: int
    harvest_events: tuple[HarvestEvent, ...]
    occupied_until_day: int

    @property
    def harvest_days(self) -> tuple[int, ...]:
        return tuple(event.day for event in self.harvest_events)

    @property
    def harvest_day(self) -> int | None:
        return self.harvest_events[-1].day if self.harvest_events else None

    @property
    def total_units(self) -> int:
        return sum(event.units for event in self.harvest_events)

    @property
    def revenue(self) -> float:
        return sum(event.revenue for event in self.harvest_events)


@dataclass(frozen=True)
class FarmPlan:
    seed_targets: Mapping[str, int]
    planting_days: Mapping[str, tuple[int, ...]]
    projected_profit: float
    projected_revenue: float
    projections: tuple[CropProjection, ...]


def hardcoded_price_series(horizon_days: int) -> dict[str, tuple[float, ...]]:
    """Return a static price table for the requested planning horizon."""

    if horizon_days < 0:
        raise ValueError("horizon_days must be non-negative")
    return {crop: (price,) * horizon_days for crop, price in HARDCODED_BASE_PRICES.items()}


def build_hardcoded_farm_plans(
    current_day: int,
    free_tiles: int,
    horizons: Sequence[int] = (5, 10),
    existing_plants: Sequence[PlantState] = (),
) -> dict[int, FarmPlan]:
    """Build deterministic best plans for fixed 5/10-day price assumptions."""

    normalized = tuple(dict.fromkeys(int(horizon) for horizon in horizons))
    if any(horizon < 0 for horizon in normalized):
        raise ValueError("planning horizons must be non-negative")
    max_horizon = max(normalized, default=0)
    prices = hardcoded_price_series(max_horizon)
    tile_count = max(0, int(free_tiles))
    plans: dict[int, FarmPlan] = {}
    for horizon in normalized:
        single_tile_plan = optimize_farm_plan(
            current_day=current_day,
            remaining_days=horizon,
            free_tiles=min(1, tile_count),
            price_forecast={crop: values[:horizon] for crop, values in prices.items()},
            existing_plants=existing_plants,
        )
        plans[horizon] = _repeat_independent_plan(single_tile_plan, tile_count)
    return plans


def _repeat_independent_plan(plan: FarmPlan, count: int) -> FarmPlan:
    """Scale a one-tile plan when tile decisions do not interact."""

    if count <= 0 or not plan.projections:
        return FarmPlan({}, {}, 0.0, 0.0, ())
    seed_targets = {crop: quantity * count for crop, quantity in plan.seed_targets.items()}
    planting_days = {crop: days * count for crop, days in plan.planting_days.items()}
    projections = plan.projections * count
    return FarmPlan(
        seed_targets=seed_targets,
        planting_days=planting_days,
        projected_profit=plan.projected_profit * count,
        projected_revenue=plan.projected_revenue * count,
        projections=projections,
    )


def farm_plan_to_dict(plan: FarmPlan) -> dict[str, Any]:
    """Serialize a plan, including the exact planting and harvest schedule."""

    return {
        "seed_targets": dict(plan.seed_targets),
        "planting_days": {crop: list(days) for crop, days in plan.planting_days.items()},
        "projected_profit": plan.projected_profit,
        "projected_revenue": plan.projected_revenue,
        "projections": [
            {
                "crop": projection.crop,
                "planted_day": projection.planted_day,
                "occupied_until_day": projection.occupied_until_day,
                "harvest_events": [
                    {
                        "day": event.day,
                        "units": event.units,
                        "price": event.price,
                        "revenue": event.revenue,
                    }
                    for event in projection.harvest_events
                ],
            }
            for projection in plan.projections
        ],
    }


def days_until_first_yield(rule: CropRule, planted_day: int, current_day: int) -> int:
    """Return calendar days until the crop's first possible production."""

    return max(0, rule.first_yield_day - (current_day - planted_day))


def days_until_harvest(plant: PlantState, current_day: int) -> int:
    """Return days until an observed plant has harvestable yield."""

    try:
        rule = OFFICIAL_CROPS[plant.crop]
    except KeyError as exc:
        raise ValueError(f"unknown crop in plant state: {plant.crop}") from exc
    age = current_day - plant.planted_day
    if age >= rule.first_yield_day and plant.yield_units > 0:
        return 0
    return days_until_first_yield(rule, plant.planted_day, current_day)


def _value(value: Any, key: str, default: Any) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def extract_farm_snapshot(observation: Any, remaining_days: int, player: int = 0) -> FarmSnapshot:
    """Extract farm planning state from the official observation shape."""

    farms = _value(observation, "farms", ()) or ()
    if player < 0 or player >= len(farms):
        raise ValueError("observation does not contain the requested farm")

    farm = farms[player] or {}
    tiles = _value(farm, "tiles", ()) or ()
    existing: list[PlantState] = []
    free_tiles = 0
    for row in tiles:
        for tile in row:
            if tile == "LOCKED":
                continue
            if tile is None:
                free_tiles += 1
                continue
            if _value(tile, "kind", None) == "PLANT":
                existing.append(
                    PlantState(
                        crop=str(_value(tile, "crop", "")),
                        planted_day=int(_value(tile, "planted_day", 0) or 0),
                        yield_units=int(_value(tile, "yield_units", 0) or 0),
                    )
                )

    return FarmSnapshot(
        current_day=int(_value(observation, "day", 0) or 0),
        remaining_days=max(0, int(remaining_days)),
        free_tiles=free_tiles,
        existing_plants=tuple(existing),
    )


def _price_at(prices: Sequence[float], day: int, current_day: int) -> float:
    if not prices:
        return 0.0
    offset = max(0, day - current_day)
    return float(prices[min(offset, len(prices) - 1)])


def _one_time_units(rule: CropRule, planted_day: int, harvest_day: int) -> int:
    age = harvest_day - planted_day
    window_start = (rule.max_yield_day + 1) // 2
    bonus_days = max(0, min(age, rule.max_yield_day) - window_start + 1)
    return min(rule.max_yield, 1 + bonus_days)


def project_crop(
    rule: CropRule,
    planted_day: int,
    current_day: int,
    horizon_days: int,
    prices: Sequence[float],
) -> CropProjection:
    """Project harvest revenue for one optimally watered new crop.

    One-time crops choose the best harvest day in their available window.  For
    ongoing crops, each scheduled production is represented as a separate
    harvest event.  This intentionally models the farm decision only; price
    forecasting and market inventory remain outside this module.
    """

    if horizon_days <= 0:
        return CropProjection(rule_name(rule), planted_day, (), current_day)

    horizon_end = current_day + horizon_days - 1
    if rule.ongoing:
        first_day = max(current_day, planted_day + rule.first_yield_day)
        last_day = planted_day + rule.first_yield_day + (rule.max_yield - 1) * rule.interval
        events: list[HarvestEvent] = []
        if rule.interval > 0:
            first_scheduled = planted_day + rule.first_yield_day
            n = max(0, (first_day - first_scheduled + rule.interval - 1) // rule.interval)
            day = first_scheduled + n * rule.interval
            while day <= min(last_day, horizon_end):
                price = _price_at(prices, day, current_day)
                events.append(HarvestEvent(day, 1, price, price))
                day += rule.interval
        occupied_until = (events[-1].day + 1) if events else horizon_end + 1
        return CropProjection(rule_name(rule), planted_day, tuple(events), occupied_until)

    first_day = max(current_day, planted_day + rule.first_yield_day)
    last_day = min(horizon_end, planted_day + rule.max_yield_day)
    candidates: list[HarvestEvent] = []
    for day in range(first_day, last_day + 1):
        units = _one_time_units(rule, planted_day, day)
        price = _price_at(prices, day, current_day)
        candidates.append(HarvestEvent(day, units, price, units * price))

    if not candidates:
        return CropProjection(rule_name(rule), planted_day, (), horizon_end + 1)

    best = max(candidates, key=lambda event: (event.revenue, -event.day))
    return CropProjection(rule_name(rule), planted_day, (best,), best.day)


def rule_name(rule: CropRule) -> str:
    for crop, known_rule in OFFICIAL_CROPS.items():
        if rule == known_rule:
            return crop
    return "CUSTOM"


def _allocations(crops: tuple[str, ...], capacity: int) -> list[dict[str, int]]:
    results: list[dict[str, int]] = []

    def visit(index: int, remaining: int, allocation: dict[str, int]) -> None:
        if index == len(crops):
            results.append({crop: count for crop, count in allocation.items() if count})
            return
        crop = crops[index]
        for count in range(remaining + 1):
            allocation[crop] = count
            visit(index + 1, remaining - count, allocation)
        allocation.pop(crop, None)

    visit(0, capacity, {})
    return results


def optimize_farm_plan(
    current_day: int,
    remaining_days: int,
    free_tiles: int,
    price_forecast: Mapping[str, Sequence[float]],
    existing_plants: Sequence[PlantState] = (),
    candidate_crops: Sequence[str] = tuple(OFFICIAL_CROPS),
) -> FarmPlan:
    """Find an integer crop allocation for the current planning horizon.

    The optimizer chooses new plants for currently free tiles.  Existing plants
    are accepted as state context and are not replaced by this first planner;
    callers can compare a later replacement plan explicitly before issuing DIG.
    """

    crops = tuple(crop for crop in candidate_crops if crop in OFFICIAL_CROPS)
    capacity = max(0, int(free_tiles))
    best = FarmPlan({}, {}, 0.0, 0.0, ())

    for allocation in _allocations(crops, capacity):
        projections: list[CropProjection] = []
        revenue = 0.0
        profit = 0.0
        for crop, count in allocation.items():
            projection = project_crop(
                OFFICIAL_CROPS[crop],
                planted_day=current_day,
                current_day=current_day,
                horizon_days=remaining_days,
                prices=price_forecast.get(crop, ()),
            )
            if not projection.harvest_events:
                profit = float("-inf")
                break
            projections.extend([projection] * count)
            revenue += count * projection.revenue
            profit += count * (projection.revenue - OFFICIAL_CROPS[crop].seed_cost)

        if profit > best.projected_profit:
            seed_targets = dict(sorted(allocation.items()))
            planting_days = {crop: (current_day,) * count for crop, count in seed_targets.items()}
            best = FarmPlan(seed_targets, planting_days, profit, revenue, tuple(projections))

    return best


def plan_unit_actions(
    state: GameState, farm: FarmFeatures, selected_crop: str | None
) -> tuple[UnitIntent, ...]:
    """Assign available farm tasks while respecting current inventory."""
    positions = state.unit_positions
    inventories = state.inventories
    assignments: dict[int, FarmTask] = {}
    used_targets: set[tuple[int, int]] = set()

    for unit_index, position in enumerate(positions):
        inventory = inventories[unit_index] if unit_index < len(inventories) else {}
        candidates = [
            task
            for task in farm.tasks
            if task.required_item is None
            or (hasattr(inventory, "get") and inventory.get(task.required_item, 0) > 0)
        ]
        candidates = [task for task in candidates if task.target not in used_targets]
        if candidates:
            task = min(
                candidates,
                key=lambda value: (
                    -value.priority,
                    distance(position, value.target),
                    value.target,
                ),
            )
            assignments[unit_index] = task
            used_targets.add(task.target)

    seeds = state.private.get("seeds", {}) or {}
    available = int(seeds.get(selected_crop, 0) or 0) if selected_crop else 0
    empty = [position for position in farm.empty_tiles if position not in used_targets]
    for unit_index, position in enumerate(positions):
        if unit_index in assignments or available <= 0 or not selected_crop or not empty:
            continue
        target = min(empty, key=lambda value: (distance(position, value), value[1], value[0]))
        empty.remove(target)
        assignments[unit_index] = FarmTask(
            target,
            ("PLANT", selected_crop),
            480.0,
            "plant",
            f"plant {selected_crop}",
        )
        available -= 1

    intents = []
    for unit_index, position in enumerate(positions):
        task = assignments.get(unit_index)
        if task is None:
            intents.append(UnitIntent(unit_index, ("PASS",), None, 0.0, "no feasible farm task"))
        elif position == task.target:
            intents.append(
                UnitIntent(unit_index, task.command, task.target, task.priority, task.reason)
            )
        else:
            intents.append(
                UnitIntent(
                    unit_index,
                    next_move(position, task.target),
                    task.target,
                    task.priority,
                    f"move toward {task.category}",
                )
            )
    return tuple(intents)
