"""Deterministic shared strategy built on farm + economy features."""

from __future__ import annotations

from ..domain import BASE_PRICES, CROPS, LAND_PRICES
from ..farm.pathfinding import distance, next_move
from ..farm.planner import optimize_farm_plan
from ..models import (
    AgentSettings,
    FarmTask,
    MarketIntent,
    StrategicFeatures,
    StrategyPlan,
    UnitIntent,
)
from .day_one import first_day_market_intents, first_day_unit_commands


class RuleBasedStrategy:
    """Baseline policy with replaceable scoring and no cross-game global state."""

    def __init__(self, settings: AgentSettings | None = None):
        self.settings = settings or AgentSettings()

    @staticmethod
    def _select_crop(features: StrategicFeatures) -> str | None:
        free_tiles = len(features.farm.empty_tiles)
        seeds = features.state.private.get("seeds", {}) or {}
        if free_tiles and features.economy.seed_priority:
            feasible = {
                opportunity.crop: opportunity.feasible
                for opportunity in features.economy.crop_opportunities
            }
            stocked = [
                crop for crop, _ in sorted(
                    features.economy.seed_priority.items(),
                    key=lambda item: (-item[1], item[0]),
                )
                if int(seeds.get(crop, 0) or 0) > 0 and feasible.get(crop, False)
            ]
            if stocked:
                return stocked[0]
        if free_tiles and features.economy.price_forecast:
            state = features.state
            plan = optimize_farm_plan(
                current_day=state.day,
                remaining_days=state.remaining_days,
                free_tiles=1,
                price_forecast={
                    crop: tuple(values[: state.remaining_days])
                    for crop, values in features.economy.price_forecast.items()
                },
            )
            for crop, count in plan.seed_targets.items():
                if count > 0:
                    return crop

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
        intents = list(features.economy.sell_intents) + list(features.economy.buy_intents)
        current_hands = len(state.me.get("hands", ()) or ())

        next_land_index = len(state.unlocked_quadrants) - 1
        can_expand = (
            state.hour == 0
            and state.remaining_days > 1
            and next_land_index < len(LAND_PRICES)
            and features.farm.utilization >= 0.80
        )
        next_land_cost = LAND_PRICES[next_land_index] if can_expand else 0
        new_land_tiles = (max(1, state.board_size // 2)) ** 2
        expansion_seed_quantity: int | None = None
        shed = state.private.get("shed", {}) or {}
        market_prices = state.market.get("prices", {}) or {}
        projected_shed_value = sum(
            int(count or 0)
            * float(market_prices.get(item, BASE_PRICES.get(item, 0)))
            for item, count in shed.items()
            if item in BASE_PRICES and int(count or 0) > 0
        )
        projected_farm_profit = 0.0
        if (
            can_expand
            and selected_crop
            and state.hour == 0
            and state.harvested_previous_day
        ):
            planning_horizon = state.remaining_days
            if planning_horizon > 0:
                farm_plan = (
                    optimize_farm_plan(
                        current_day=state.day,
                        remaining_days=state.remaining_days,
                        free_tiles=1,
                        price_forecast={
                            crop: tuple(values[: state.remaining_days])
                            for crop, values in features.economy.price_forecast.items()
                        },
                    )
                    if features.economy.price_forecast
                    else None
                )
                if farm_plan and selected_crop in farm_plan.seed_targets:
                    projected_farm_profit = max(0.0, farm_plan.projected_profit)
                    projected_farm_profit *= len(features.farm.empty_tiles)

        if state.remaining_days > 1 and state.hour <= 2:
            missing_hands = max(0, self.settings.target_hands - current_hands)
            for _ in range(missing_hands):
                intents.append(MarketIntent(("HIRE",), 1040.0, reason="daily labor capacity"))

        if selected_crop:
            current_seeds = int((state.private.get("seeds", {}) or {}).get(selected_crop, 0) or 0)
            spec = CROPS[selected_crop]
            if can_expand:
                required_seeds_after_expansion = len(features.farm.empty_tiles) + new_land_tiles
                missing_for_expansion = max(
                    0, required_seeds_after_expansion - current_seeds
                )
                expansion_cost = next_land_cost + missing_for_expansion * spec.seed_cost
                projected_money = (
                    state.money + projected_shed_value + projected_farm_profit
                )
                if projected_money >= expansion_cost:
                    expansion_seed_quantity = missing_for_expansion

            expected_units = 1 + max(current_hands, self.settings.target_hands)
            plant_capacity = min(
                features.farm.unlocked_tile_count,
                expected_units * self.settings.max_plants_per_unit,
            )
            committed = features.farm.plant_count + current_seeds
            needed = max(0, plant_capacity - committed)
            desired_buffer = max(2, expected_units * self.settings.seed_buffer_per_unit)
            quantity = min(needed, max(0, desired_buffer - current_seeds), 6)
            affordable = int(max(0.0, state.money - self.settings.cash_reserve) // spec.seed_cost)
            quantity = min(quantity, affordable)
            if not features.economy.buy_intents and expansion_seed_quantity is not None:
                if expansion_seed_quantity > 0:
                    intents.append(
                        MarketIntent(
                            ("BUY_SEED", selected_crop, expansion_seed_quantity),
                            1090.0,
                            float(expansion_seed_quantity * spec.seed_cost),
                            "stock seed for every empty tile after expansion",
                        )
                    )
            elif not features.economy.buy_intents and quantity > 0:
                intents.append(
                    MarketIntent(
                        ("BUY_SEED", selected_crop, quantity),
                        760.0,
                        estimated_cost=float(quantity * spec.seed_cost),
                        reason=f"stock planting buffer for {selected_crop}",
                    )
                )

        if expansion_seed_quantity is not None:
            already_selling = {
                str(intent.command[1])
                for intent in intents
                if intent.command and intent.command[0] == "SELL" and len(intent.command) >= 2
            }
            for item, raw_count in shed.items():
                count = int(raw_count or 0)
                if count > 0 and item in BASE_PRICES and item not in already_selling:
                    intents.append(
                        MarketIntent(
                            ("SELL", item, count),
                            1200.0,
                            reason="liquidate shed to fund land and seed expansion",
                        )
                    )
            intents.append(
                MarketIntent(
                    ("BUY_LAND",),
                    1100.0,
                            float(next_land_cost),
                    "expand when current, shed, and projected farm money cover land and seeds",
                )
            )
        return tuple(intents)

    def decide(self, features: StrategicFeatures) -> StrategyPlan:
        if features.state.day == 0 and features.state.board_size >= 10:
            commands = first_day_unit_commands(features.state)
            unit_intents = tuple(
                UnitIntent(index, command, None, 1200.0, "fixed first-day route")
                for index, command in enumerate(commands)
            )
            return StrategyPlan(
                selected_crop="WHEAT",
                unit_intents=unit_intents,
                market_intents=first_day_market_intents(features.state),
                notes=("phase=day-one-fixed", "crop=WHEAT"),
            )
        selected_crop = self._select_crop(features)
        return StrategyPlan(
            selected_crop=selected_crop,
            unit_intents=self._schedule_units(features, selected_crop),
            market_intents=self._market_intents(features, selected_crop),
            notes=(f"phase={features.phase}", f"crop={selected_crop or 'none'}"),
        )
