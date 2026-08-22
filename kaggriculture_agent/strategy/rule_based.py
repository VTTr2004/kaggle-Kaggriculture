"""Deterministic shared strategy built on farm + economy features."""

from __future__ import annotations

from ..domain import CROPS, LAND_PRICES
from ..farm.pathfinding import distance, next_move
from ..models import (
    AgentSettings,
    FarmTask,
    MarketIntent,
    StrategicFeatures,
    StrategyPlan,
    UnitIntent,
)


class RuleBasedStrategy:
    """Baseline policy with replaceable scoring and no cross-game global state."""

    def __init__(self, settings: AgentSettings | None = None):
        self.settings = settings or AgentSettings()

    @staticmethod
    def _select_crop(features: StrategicFeatures) -> str | None:
        for opportunity in features.economy.crop_opportunities:
            if opportunity.feasible and opportunity.expected_profit > 0:
                return opportunity.crop
        return None

    @staticmethod
    def _can_do(task: FarmTask, inventory: dict[str, int] | object) -> bool:
        if task.required_item is None:
            return True
        getter = getattr(inventory, "get", None)
        return bool(getter and getter(task.required_item, 0) > 0)

    def _schedule_units(
        self, features: StrategicFeatures, selected_crop: str | None
    ) -> tuple[UnitIntent, ...]:
        state = features.state
        positions = state.unit_positions
        inventories = state.inventories
        assignments: dict[int, FarmTask] = {}
        used_targets: set[tuple[int, int]] = set()

        # Global greedy matching prevents the farmer from always taking the best
        # task even when a hand is already standing on it.
        candidates: list[tuple[float, int, FarmTask]] = []
        for unit_index, position in enumerate(positions):
            inventory = inventories[unit_index] if unit_index < len(inventories) else {}
            for task in features.farm.tasks:
                if self._can_do(task, inventory):
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

        # Plant only with seeds already present. Market purchases happen after
        # unit actions in the official interpreter and are usable next turn.
        seeds = state.private.get("seeds", {}) or {}
        available = int(seeds.get(selected_crop, 0) or 0) if selected_crop else 0
        empty = [position for position in features.farm.empty_tiles if position not in used_targets]
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
                reason=f"plant highest-ranked crop {selected_crop}",
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

    def _market_intents(
        self, features: StrategicFeatures, selected_crop: str | None
    ) -> tuple[MarketIntent, ...]:
        state = features.state
        intents = list(features.economy.sell_intents)
        current_hands = len(state.me.get("hands", ()) or ())

        if state.remaining_days > 1 and state.hour <= 2:
            missing_hands = max(0, self.settings.target_hands - current_hands)
            for _ in range(missing_hands):
                intents.append(MarketIntent(("HIRE",), 1040.0, reason="daily labor capacity"))

        if selected_crop:
            current_seeds = int((state.private.get("seeds", {}) or {}).get(selected_crop, 0) or 0)
            expected_units = 1 + max(current_hands, self.settings.target_hands)
            plant_capacity = min(
                features.farm.unlocked_tile_count,
                expected_units * self.settings.max_plants_per_unit,
            )
            committed = features.farm.plant_count + current_seeds
            needed = max(0, plant_capacity - committed)
            desired_buffer = max(2, expected_units * self.settings.seed_buffer_per_unit)
            quantity = min(needed, max(0, desired_buffer - current_seeds), 6)
            spec = CROPS[selected_crop]
            affordable = int(max(0.0, state.money - self.settings.cash_reserve) // spec.seed_cost)
            quantity = min(quantity, affordable)
            if quantity > 0:
                intents.append(
                    MarketIntent(
                        ("BUY_SEED", selected_crop, quantity),
                        760.0,
                        estimated_cost=float(quantity * spec.seed_cost),
                        reason=f"stock planting buffer for {selected_crop}",
                    )
                )

        unlocked = len(state.unlocked_quadrants)
        utilization = features.farm.plant_count / max(1, features.farm.unlocked_tile_count)
        if (
            state.hour == 0
            and state.remaining_days > 12
            and unlocked - 1 < len(LAND_PRICES)
            and utilization >= 0.80
        ):
            cost = LAND_PRICES[unlocked - 1]
            if state.money >= cost + self.settings.expand_cash_reserve:
                intents.append(
                    MarketIntent(("BUY_LAND",), 680.0, float(cost), "expand saturated farm")
                )
        return tuple(intents)

    def decide(self, features: StrategicFeatures) -> StrategyPlan:
        selected_crop = self._select_crop(features)
        return StrategyPlan(
            selected_crop=selected_crop,
            unit_intents=self._schedule_units(features, selected_crop),
            market_intents=self._market_intents(features, selected_crop),
            notes=(f"phase={features.phase}", f"crop={selected_crop or 'none'}"),
        )
