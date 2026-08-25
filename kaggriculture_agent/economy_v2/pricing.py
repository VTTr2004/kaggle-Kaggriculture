"""Exact, explainable unit-price calculator for Economy V2."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

PRICE_FLOOR = 1
HINGE_GAIN = 8.0
BUYABLE_PRODUCTS = frozenset({"WHEAT", "FERTILIZER"})

# Official defaults mirrored from the installed Kaggriculture interpreter.
# Direct parity tests make any future interpreter drift visible.
DEFAULT_MARKET_PARAMS_V2: dict[str, dict[str, float | str]] = {
    "WHEAT": {
        "base": 25,
        "I0": 10000,
        "T": 400,
        "below_func": "sqrt",
        "below_target": 0.80,
        "above_func": "log",
        "above_target": 0.20,
    },
    "CARROT": {
        "base": 35,
        "I0": 10000,
        "T": 450,
        "below_func": "hinge",
        "below_target": 1.00,
        "above_func": "sqrt",
        "above_target": 0.70,
    },
    "TOMATO": {
        "base": 60,
        "I0": 10000,
        "T": 200,
        "below_func": "hinge",
        "below_target": 0.40,
        "above_func": "sqrt",
        "above_target": 0.60,
    },
    "STRAWBERRY": {
        "base": 120,
        "I0": 10000,
        "T": 100,
        "below_func": "sqrt",
        "below_target": 0.70,
        "above_func": "linear",
        "above_target": 1.60,
    },
    "MELON": {
        "base": 250,
        "I0": 10000,
        "T": 300,
        "below_func": "log",
        "below_target": 0.20,
        "above_func": "sq",
        "above_target": 3.60,
    },
    "EGG": {
        "base": 50,
        "I0": 10000,
        "T": 332,
        "below_func": "hinge",
        "below_target": 0.40,
        "above_func": "log",
        "above_target": 0.20,
    },
    "MILK": {
        "base": 160,
        "I0": 10000,
        "T": 122,
        "below_func": "sqrt",
        "below_target": 0.60,
        "above_func": "linear",
        "above_target": 1.60,
    },
    "WOOL": {
        "base": 200,
        "I0": 10000,
        "T": 105,
        "below_func": "log",
        "below_target": 0.20,
        "above_func": "sq",
        "above_target": 3.20,
    },
    "FERTILIZER": {
        "base": 100,
        "I0": 10000,
        "T": 200,
        "below_func": "linear",
        "below_target": 0.40,
        "above_func": "linear",
        "above_target": 0.40,
    },
}


@dataclass(frozen=True)
class PriceBreakdownV2:
    item: str
    inventory: float
    base_price: float
    equilibrium: float
    throughput: float
    side: str
    function: str
    target: float
    distance: float
    shape_at_distance: float
    shape_at_throughput: float
    amplitude: float
    raw_price: float
    quoted_price: int


@dataclass(frozen=True)
class OrderQuoteV2:
    """Explain one isolated multi-unit market order without executing it."""

    operation: str
    item: str
    quantity: int
    starting_inventory: float
    ending_inventory: float
    unit_prices: tuple[int, ...]
    total: float
    average_price: float


@dataclass(frozen=True)
class MarketOrderV2:
    """One executable dynamic-price order used by the lockstep calculator."""

    operation: str
    item: str
    quantity: int


@dataclass(frozen=True)
class PlayerOrderQuoteV2:
    """Per-player prices for one order inside a lockstep market queue."""

    operation: str
    item: str
    quantity: int
    unit_prices: tuple[int, ...]
    total: float
    average_price: float


@dataclass(frozen=True)
class LockstepMarketQuoteV2:
    """Result of quoting two ordered player queues without resource failures."""

    starting_inventory: Mapping[str, float]
    ending_inventory: Mapping[str, float]
    player_order_quotes: tuple[tuple[PlayerOrderQuoteV2, ...], ...]


def shape_value_v2(function: str, distance: float, throughput: float) -> float:
    """Apply one official curve shape to a non-negative inventory distance."""
    distance = max(0.0, float(distance))
    throughput = float(throughput)
    if function == "linear":
        return distance
    if function == "sq":
        return distance * distance
    if function == "sqrt":
        return math.sqrt(distance)
    if function == "log":
        return math.log(1.0 + distance)
    if function == "log10":
        return math.log10(1.0 + distance)
    if function == "hinge":
        if throughput <= 0:
            return distance
        normalized = distance / throughput
        return normalized + HINGE_GAIN * max(0.0, normalized - 1.0) ** 2
    return distance


def resolve_market_params_v2(
    item: str,
    overrides: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, float | str]:
    """Copy official defaults and apply a runtime override for one item."""
    if item not in DEFAULT_MARKET_PARAMS_V2:
        raise ValueError(f"unknown market item: {item}")
    params = dict(DEFAULT_MARKET_PARAMS_V2[item])
    if overrides:
        patch = overrides.get(item)
        if isinstance(patch, Mapping):
            params.update(patch)
    if float(params["T"]) <= 0:
        raise ValueError("market throughput T must be positive")
    return params


def price_breakdown_v2(
    item: str,
    inventory: int | float,
    overrides: Mapping[str, Mapping[str, Any]] | None = None,
) -> PriceBreakdownV2:
    """Expose every term used to quote one unit at an inventory level."""
    params = resolve_market_params_v2(item, overrides)
    base = float(params["base"])
    equilibrium = float(params["I0"])
    throughput = float(params["T"])
    inventory = float(inventory)

    if inventory < equilibrium:
        side = "scarcity"
        function = str(params["below_func"])
        target = float(params["below_target"])
        sign = 1.0
    else:
        side = "glut"
        function = str(params["above_func"])
        target = float(params["above_target"])
        sign = -1.0

    distance = abs(inventory - equilibrium)
    shape_at_distance = shape_value_v2(function, distance, throughput)
    shape_at_throughput = shape_value_v2(function, throughput, throughput)
    if shape_at_throughput == 0:
        raise ValueError("market curve must be non-zero at throughput T")
    amplitude = target * base / shape_at_throughput
    raw_price = base + sign * amplitude * shape_at_distance

    return PriceBreakdownV2(
        item=item,
        inventory=inventory,
        base_price=base,
        equilibrium=equilibrium,
        throughput=throughput,
        side=side,
        function=function,
        target=target,
        distance=distance,
        shape_at_distance=shape_at_distance,
        shape_at_throughput=shape_at_throughput,
        amplitude=amplitude,
        raw_price=raw_price,
        quoted_price=max(PRICE_FLOOR, int(round(raw_price))),
    )


def market_price_v2(
    item: str,
    inventory: int | float,
    overrides: Mapping[str, Mapping[str, Any]] | None = None,
) -> int:
    """Return the official integer quote for one unit."""
    return price_breakdown_v2(item, inventory, overrides).quoted_price


def quote_sell_v2(
    item: str,
    quantity: int,
    starting_inventory: int | float,
    overrides: Mapping[str, Mapping[str, Any]] | None = None,
) -> OrderQuoteV2:
    """Quote an isolated SELL order sequentially, including the $1-floor rule."""
    if quantity < 0:
        raise ValueError("quantity must be non-negative")

    inventory = float(starting_inventory)
    unit_prices: list[int] = []
    for _ in range(quantity):
        price = market_price_v2(item, inventory, overrides)
        unit_prices.append(price)
        if price > PRICE_FLOOR:
            inventory += 1

    total = float(sum(unit_prices))
    average_price = total / quantity if quantity else 0.0
    return OrderQuoteV2(
        operation="SELL",
        item=item,
        quantity=quantity,
        starting_inventory=float(starting_inventory),
        ending_inventory=inventory,
        unit_prices=tuple(unit_prices),
        total=total,
        average_price=average_price,
    )


def quote_buy_product_v2(
    item: str,
    quantity: int,
    starting_inventory: int | float,
    overrides: Mapping[str, Mapping[str, Any]] | None = None,
) -> OrderQuoteV2:
    """Quote an isolated BUY_PRODUCT order at each post-buy inventory level."""
    if item not in BUYABLE_PRODUCTS:
        raise ValueError("BUY_PRODUCT only supports WHEAT or FERTILIZER")
    if quantity < 0:
        raise ValueError("quantity must be non-negative")

    inventory = float(starting_inventory)
    unit_prices: list[int] = []
    for _ in range(quantity):
        inventory -= 1
        unit_prices.append(market_price_v2(item, inventory, overrides))

    total = float(sum(unit_prices))
    average_price = total / quantity if quantity else 0.0
    return OrderQuoteV2(
        operation="BUY_PRODUCT",
        item=item,
        quantity=quantity,
        starting_inventory=float(starting_inventory),
        ending_inventory=inventory,
        unit_prices=tuple(unit_prices),
        total=total,
        average_price=average_price,
    )


def _validate_lockstep_order(order: MarketOrderV2, inventory: Mapping[str, float]) -> None:
    if order.operation not in {"SELL", "BUY_PRODUCT"}:
        raise ValueError("lockstep pricing only supports SELL or BUY_PRODUCT")
    if order.quantity < 0:
        raise ValueError("quantity must be non-negative")
    if order.item not in DEFAULT_MARKET_PARAMS_V2:
        raise ValueError(f"unknown market item: {order.item}")
    if order.item not in inventory:
        raise ValueError(f"starting inventory is missing item: {order.item}")
    if order.operation == "BUY_PRODUCT" and order.item not in BUYABLE_PRODUCTS:
        raise ValueError("BUY_PRODUCT only supports WHEAT or FERTILIZER")


def quote_lockstep_market_v2(
    starting_inventory: Mapping[str, int | float],
    player_orders: tuple[tuple[MarketOrderV2, ...], ...],
    overrides: Mapping[str, Mapping[str, Any]] | None = None,
) -> LockstepMarketQuoteV2:
    """Quote two order queues using official per-unit pre-commit lockstep.

    Every supplied unit is assumed executable. Cash, shed capacity, owned
    quantity, and market-order limits remain Strategy/Fusion responsibilities.
    """
    if len(player_orders) != 2:
        raise ValueError("lockstep pricing requires exactly two player queues")

    initial = {str(item): float(value) for item, value in starting_inventory.items()}
    inventory = dict(initial)
    for queue in player_orders:
        for order in queue:
            _validate_lockstep_order(order, inventory)

    collected: list[list[list[int]]] = [[[] for _ in queue] for queue in player_orders]
    max_orders = max((len(queue) for queue in player_orders), default=0)

    for order_index in range(max_orders):
        active = [
            queue[order_index] if order_index < len(queue) else None for queue in player_orders
        ]
        remaining = [order.quantity if order is not None else 0 for order in active]

        while any(quantity > 0 for quantity in remaining):
            round_quotes: list[int | None] = [None, None]
            for player_index, order in enumerate(active):
                if order is None or remaining[player_index] <= 0:
                    continue
                quote_inventory = inventory[order.item]
                if order.operation == "BUY_PRODUCT":
                    quote_inventory -= 1
                round_quotes[player_index] = market_price_v2(
                    order.item,
                    quote_inventory,
                    overrides,
                )

            for player_index, order in enumerate(active):
                price = round_quotes[player_index]
                if order is None or price is None:
                    continue
                collected[player_index][order_index].append(price)
                if order.operation == "SELL":
                    if price > PRICE_FLOOR:
                        inventory[order.item] += 1
                else:
                    inventory[order.item] -= 1
                remaining[player_index] -= 1

    player_quotes: list[tuple[PlayerOrderQuoteV2, ...]] = []
    for player_index, queue in enumerate(player_orders):
        quotes: list[PlayerOrderQuoteV2] = []
        for order_index, order in enumerate(queue):
            unit_prices = tuple(collected[player_index][order_index])
            total = float(sum(unit_prices))
            quotes.append(
                PlayerOrderQuoteV2(
                    operation=order.operation,
                    item=order.item,
                    quantity=order.quantity,
                    unit_prices=unit_prices,
                    total=total,
                    average_price=total / order.quantity if order.quantity else 0.0,
                )
            )
        player_quotes.append(tuple(quotes))

    return LockstepMarketQuoteV2(
        starting_inventory=MappingProxyType(initial),
        ending_inventory=MappingProxyType(dict(inventory)),
        player_order_quotes=tuple(player_quotes),
    )
