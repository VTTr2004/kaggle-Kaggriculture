"""Decision fusion: resolve budgets, counts and action invariants."""

from __future__ import annotations

from collections import Counter

from .domain import ANIMALS, BASE_PRICES, CROPS, LAND_PRICES, UNIT_OPERATIONS, hire_cost
from .models import Command, FinalDecision, GameState, StrategyPlan


def _valid_unit_command(command: Command) -> bool:
    return bool(command) and isinstance(command[0], str) and command[0] in UNIT_OPERATIONS


def _order_cost(command: Command, state: GameState, hires: int) -> float:
    op = command[0]
    if op == "HIRE":
        return float(hire_cost(hires, state.farm_hand_cost_mult))
    if op == "BUY_LAND":
        index = len(state.unlocked_quadrants) - 1
        return float(LAND_PRICES[index]) if index < len(LAND_PRICES) else float("inf")
    if len(command) < 3:
        return 0.0
    item, count = str(command[1]), int(command[2])
    if op == "BUY_SEED" and item in CROPS:
        return float(CROPS[item].seed_cost * count)
    if op == "BUY_ANIMAL" and item in ANIMALS:
        return float(ANIMALS[item].cost * count)
    if op == "BUY_PRODUCT":
        prices = state.market.get("prices", {}) or {}
        return float(prices.get(item, BASE_PRICES.get(item, 0))) * count
    return 0.0


def _fuse_units(state: GameState, plan: StrategyPlan) -> tuple[Command, ...]:
    commands: list[Command] = [("PASS",) for _ in state.unit_positions]
    seeds = Counter(state.private.get("seeds", {}) or {})
    for intent in sorted(plan.unit_intents, key=lambda value: -value.priority):
        if not 0 <= intent.unit_index < len(commands) or not _valid_unit_command(intent.command):
            continue
        command = intent.command
        if command[0] == "PLANT":
            if len(command) < 2 or seeds[str(command[1])] <= 0:
                continue
            seeds[str(command[1])] -= 1
        commands[intent.unit_index] = command
    return tuple(commands)


def _fuse_market(state: GameState, plan: StrategyPlan) -> tuple[Command, ...]:
    budget = state.money
    hires = int(state.me.get("hires_today", 0) or 0)
    shed = Counter(state.private.get("shed", {}) or {})
    accepted: list[Command] = []
    valid_market_ops = {"BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL", "HIRE", "BUY_LAND"}

    for intent in sorted(plan.market_intents, key=lambda value: -value.priority):
        if len(accepted) >= state.max_market_orders:
            break
        command = intent.command
        if not command or command[0] not in valid_market_ops:
            continue
        op = command[0]
        if op in {"BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"}:
            if len(command) != 3:
                continue
            try:
                count = int(command[2])
            except (TypeError, ValueError):
                continue
            if count <= 0:
                continue
        if op == "SELL":
            item, requested = str(command[1]), int(command[2])
            quantity = min(requested, shed[item])
            if quantity <= 0 or item not in BASE_PRICES:
                continue
            command = ("SELL", item, quantity)
            shed[item] -= quantity
            prices = state.market.get("prices", {}) or {}
            budget += float(prices.get(item, BASE_PRICES[item])) * quantity
        else:
            cost = _order_cost(command, state, hires)
            if cost > budget:
                continue
            budget -= cost
            if op == "HIRE":
                hires += 1
            if op == "BUY_LAND" and any(order[0] == "BUY_LAND" for order in accepted):
                continue
        accepted.append(command)
    return tuple(accepted)


def fuse_decisions(state: GameState, plan: StrategyPlan) -> FinalDecision:
    return FinalDecision(
        unit_commands=_fuse_units(state, plan),
        market_commands=_fuse_market(state, plan),
    )
