"""Version 1 economy policy for the farm stress scenario."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from kaggriculture_agent.domain import BASE_PRICES, SHOP_DEMAND

from ..core.base import EconomyBot
from ..core.helpers import opening_seed_orders
from ..core.types import MarketAnalysis


@dataclass(frozen=True)
class EconomyV1Config:
    item: str = "MELON"
    sell_day: int = 20
    seed: str = "MELON"
    seed_price: int = 80
    land_price: int = 1000


class EconomyV1(EconomyBot):
    def __init__(self, config: EconomyV1Config | None = None):
        self.config = config or EconomyV1Config()
        self._previous_prices: dict[str, float] = {}

    def forecast_prices(self, observation, horizon: int) -> MarketAnalysis:
        market = observation.get("market", {}) or {}
        raw_prices = market.get("prices", {}) or {}
        prices_now = {str(item): float(value) for item, value in raw_prices.items()}
        trends = {
            item: 1
            if price > self._previous_prices.get(item, price)
            else -1
            if price < self._previous_prices.get(item, price)
            else 0
            for item, price in prices_now.items()
        }
        self._previous_prices = prices_now

        shop_demand: Counter[str] = Counter()
        for shop in (observation.get("town", {}) or {}).get("unlocked_shops", ()) or ():
            shop_demand.update(SHOP_DEMAND.get(str(shop), ()))
        town_center_demand = {item: 1 for item in BASE_PRICES}
        inventory = {
            str(item): int(value or 0)
            for item, value in (market.get("inventory", {}) or {}).items()
        }
        return MarketAnalysis(
            prices={
                item: tuple(price for _ in range(max(1, horizon)))
                for item, price in prices_now.items()
            },
            trends=trends,
            shop_demand=dict(shop_demand),
            town_center_demand=town_center_demand,
            market_inventory=inventory,
            opponent_signals={},
        )

    def _build_market_orders(self, observation, analysis):
        step = self.step(observation)
        day = self.day(observation)
        if step == 0:
            return opening_seed_orders(
                observation,
                seed=self.config.seed,
                seed_price=self.config.seed_price,
                land_price=self.config.land_price,
            )
        if day < self.config.sell_day:
            return []
        shed = observation.get("private", {}).get("shed", {}) or {}
        quantity = int(shed.get(self.config.item, 0) or 0)
        return [["SELL", self.config.item, quantity]] if quantity > 0 else []
