"""Exact, standard-library copy of the official market price curve."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

PRICE_FLOOR = 1
HINGE_GAIN = 8.0

# Mirrored from the installed Kaggriculture interpreter. Boundary tests compare
# this implementation with the official function so version drift is visible.
DEFAULT_MARKET_PARAMS: dict[str, dict[str, float | str]] = {
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
class PriceBreakdown:
    item: str
    inventory: float
    base: float
    equilibrium_inventory: float
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


def _shape(function: str, distance: float, throughput: float) -> float:
    distance = max(0.0, distance)
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


def resolved_market_params(
    item: str,
    overrides: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, float | str]:
    """Return official defaults merged with an observation override, if any."""
    params = dict(DEFAULT_MARKET_PARAMS[item])
    if overrides:
        patch = overrides.get(item)
        if isinstance(patch, Mapping):
            params.update(patch)
    return params


def market_price(
    item: str,
    inventory: int | float,
    overrides: Mapping[str, Mapping[str, Any]] | None = None,
) -> int:
    """Quote one unit at an inventory level using the official price function."""
    return price_breakdown(item, inventory, overrides).quoted_price


def price_breakdown(
    item: str,
    inventory: int | float,
    overrides: Mapping[str, Mapping[str, Any]] | None = None,
) -> PriceBreakdown:
    """Expose every official price-curve term for tests and the dashboard."""
    params = resolved_market_params(item, overrides)
    base = float(params["base"])
    equilibrium = float(params["I0"])
    throughput = float(params["T"])
    if inventory < equilibrium:
        side = "scarcity"
        function = str(params["below_func"])
        target = float(params["below_target"])
        distance = equilibrium - inventory
        sign = 1.0
    else:
        side = "glut"
        function = str(params["above_func"])
        target = float(params["above_target"])
        distance = inventory - equilibrium
        sign = -1.0
    shape_at_throughput = _shape(function, throughput, throughput)
    shape_at_distance = _shape(function, distance, throughput)
    amplitude = target * base / shape_at_throughput
    raw_price = base + sign * amplitude * shape_at_distance
    return PriceBreakdown(
        item=item,
        inventory=float(inventory),
        base=base,
        equilibrium_inventory=equilibrium,
        throughput=throughput,
        side=side,
        function=function,
        target=target,
        distance=float(distance),
        shape_at_distance=shape_at_distance,
        shape_at_throughput=shape_at_throughput,
        amplitude=amplitude,
        raw_price=raw_price,
        quoted_price=max(PRICE_FLOOR, int(round(raw_price))),
    )
