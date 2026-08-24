"""Types shared by farmer and economy bots."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict


class BotAction(TypedDict):
    farmer: list[Any]
    hands: list[list[Any]]
    market: list[list[Any]]


@dataclass(frozen=True)
class MarketAnalysis:
    prices: dict[str, tuple[float, ...]] = field(default_factory=dict)
    trends: dict[str, int] = field(default_factory=dict)
    shop_demand: dict[str, int] = field(default_factory=dict)
    town_center_demand: dict[str, int] = field(default_factory=dict)
    market_inventory: dict[str, int] = field(default_factory=dict)
    opponent_signals: dict[str, int] = field(default_factory=dict)
