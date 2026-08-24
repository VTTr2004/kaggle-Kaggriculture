"""Transparent deterministic market and crop forecasts."""

from __future__ import annotations

from collections import Counter, deque
from collections.abc import Mapping
from dataclasses import dataclass
from statistics import mean, median, pstdev

from ..domain import CROPS, SHOP_DEMAND
from ..models import GameState
from .pricing import market_price
from .snapshot import EconomySnapshot


def forecast_price_series(
    history: list[Mapping[str, float]],
    current_prices: Mapping[str, float],
    *,
    horizon_days: int,
) -> dict[str, list[float]]:
    """Return a median-based, deterministic price projection."""
    if horizon_days < 0:
        raise ValueError("horizon_days must be non-negative")
    result: dict[str, list[float]] = {}
    for product, raw_current in current_prices.items():
        current = float(raw_current)
        values = [float(snapshot[product]) for snapshot in history if product in snapshot]
        center = median(values[-10:]) if values else current
        predicted = [round(max(1.0, float(center)), 2)] * horizon_days
        result[str(product)] = predicted
    return result


class StatisticalMarketForecaster:
    """Rolling descriptive statistics for prices, without model training."""

    def __init__(self, *, window: int = 10):
        self.window = max(2, window)
        self._prices: deque[dict[str, float]] = deque(maxlen=self.window)

    def observe(self, prices: Mapping[str, float]) -> None:
        current = {str(k): float(v) for k, v in prices.items() if float(v) > 0}
        if not current:
            return
        self._prices.append(current)

    def forecast_prices(
        self, prices: Mapping[str, float], *, horizon_days: int
    ) -> dict[str, list[float]]:
        return forecast_price_series(list(self._prices), prices, horizon_days=horizon_days)

    def statistics(self, prices: Mapping[str, float]) -> dict[str, dict[str, float]]:
        result: dict[str, dict[str, float]] = {}
        for product, raw_current in prices.items():
            key = str(product)
            values = [snapshot[key] for snapshot in self._prices if key in snapshot]
            values.append(float(raw_current))
            result[key] = {
                "mean": round(mean(values), 2),
                "median": round(median(values), 2),
                "volatility": round(pstdev(values), 2) if len(values) > 1 else 0.0,
                "low": round(min(values), 2),
                "high": round(max(values), 2),
            }
        return result


@dataclass(frozen=True)
class CropForecast:
    crop: str
    yield_days: tuple[int, ...]
    occupied_days: int
    expected_units: int
    current_inventory: int
    town_consumption: float
    known_town_consumption: float
    expected_future_shop_consumption: float
    own_pending_supply: int
    opponent_visible_supply: int
    projected_inventory: float
    expected_unit_prices: tuple[int, ...]
    expected_average_price: float
    expected_revenue: float


@dataclass(frozen=True)
class TownConsumptionForecast:
    item: str
    days: int
    center_consumption: float
    known_shop_consumption: float
    expected_future_shop_consumption: float

    @property
    def total(self) -> float:
        return (
            self.center_consumption
            + self.known_shop_consumption
            + self.expected_future_shop_consumption
        )


def _shop_units_per_event(snapshot: EconomySnapshot, item: str) -> int:
    demand: Counter[str] = Counter()
    for shop in snapshot.unlocked_shops:
        demand.update(SHOP_DEMAND.get(shop, ()))
    return demand[item]


def _expected_units_per_random_shop(item: str) -> float:
    if not SHOP_DEMAND:
        return 0.0
    return sum(products.count(item) for products in SHOP_DEMAND.values()) / len(SHOP_DEMAND)


def town_consumption_breakdown_until(
    state: GameState,
    snapshot: EconomySnapshot,
    item: str,
    days: int,
) -> TownConsumptionForecast:
    """Forecast town drain, separating known shops from future random shops.

    Existing shops are facts. A future shop's identity is hidden, so its demand
    is the uniform expectation over the official shop table. Unlock timing and
    the eight-instance cap are deterministic.
    """
    horizon_turns = max(0, days) * state.turns_per_day
    end_step = state.step + horizon_turns
    known_units = _shop_units_per_event(snapshot, item)
    expected_new_units = 0.0
    expected_units_per_unlock = _expected_units_per_random_shop(item)
    shop_instances = len(snapshot.unlocked_shops)
    center_consumption = 0.0
    known_shop_consumption = 0.0
    future_shop_consumption = 0.0

    for step in range(state.step, end_step):
        if step % state.town_shop_sell_interval == 0:
            known_shop_consumption += known_units
            future_shop_consumption += expected_new_units
        if item != "FERTILIZER" and step % state.town_center_sell_interval == 0:
            center_consumption += 1.0

        next_step = step + 1
        if next_step % state.turns_per_day != 0:
            continue
        next_day = next_step // state.turns_per_day
        if next_day > 0 and next_day % state.town_shop_unlock_interval == 0 and shop_instances < 8:
            shop_instances += 1
            expected_new_units += expected_units_per_unlock

    return TownConsumptionForecast(
        item=item,
        days=max(0, days),
        center_consumption=center_consumption,
        known_shop_consumption=known_shop_consumption,
        expected_future_shop_consumption=future_shop_consumption,
    )


def town_consumption_until(
    state: GameState,
    snapshot: EconomySnapshot,
    item: str,
    days: int,
) -> float:
    """Expected scheduled town drain until a future day boundary."""
    return town_consumption_breakdown_until(state, snapshot, item, days).total


def average_daily_town_demand(
    state: GameState,
    snapshot: EconomySnapshot,
    item: str,
) -> float:
    """Readable units/day rate; the forecast itself uses exact event counts."""
    center = 0.0
    if item != "FERTILIZER":
        center = state.turns_per_day / state.town_center_sell_interval
    shops = (
        state.turns_per_day / state.town_shop_sell_interval * _shop_units_per_event(snapshot, item)
    )
    return center + shops


def _yield_batches(crop: str) -> tuple[tuple[int, int], ...]:
    spec = CROPS[crop]
    if not spec.ongoing:
        return ((spec.unfertilized_peak_day, spec.unfertilized_yield),)
    return tuple(
        (spec.first_yield_day + index * spec.interval, 1)
        for index in range(spec.unfertilized_yield)
    )


def forecast_crop(state: GameState, snapshot: EconomySnapshot, crop: str) -> CropForecast:
    """Forecast cash if each unfertilized yield is sold when it becomes available.

    Assumptions are deliberately explicit: town schedules are known; all public
    opponent-ready supply is sold once; unknown future opponent production is
    not invented; our own sale moves inventory one unit at a time.
    """
    batches = _yield_batches(crop)
    yield_days = tuple(day for day, _ in batches)
    current_inventory = int(snapshot.market_inventory.get(crop, 10000) or 0)
    own_pending_supply = int(snapshot.own_pending_supply.get(crop, 0) or 0)
    opponent_supply = int(snapshot.opponent_visible_supply.get(crop, 0) or 0)
    own_units_sold = 0
    prices: list[int] = []
    first_projected_inventory: float | None = None
    first_town_forecast: TownConsumptionForecast | None = None

    for day, quantity in batches:
        town_forecast = town_consumption_breakdown_until(state, snapshot, crop, day)
        town_drain = town_forecast.total
        inventory_before_batch = (
            current_inventory - town_drain + own_pending_supply + opponent_supply + own_units_sold
        )
        if first_projected_inventory is None:
            first_projected_inventory = inventory_before_batch
            first_town_forecast = town_forecast
        for offset in range(quantity):
            prices.append(
                market_price(
                    crop,
                    inventory_before_batch + offset,
                    snapshot.market_params,
                )
            )
        own_units_sold += quantity

    expected_units = sum(quantity for _, quantity in batches)
    revenue = float(sum(prices))
    occupied_days = max(yield_days)
    if first_town_forecast is None:
        first_town_forecast = TownConsumptionForecast(crop, 0, 0.0, 0.0, 0.0)
    return CropForecast(
        crop=crop,
        yield_days=yield_days,
        occupied_days=occupied_days,
        expected_units=expected_units,
        current_inventory=current_inventory,
        town_consumption=first_town_forecast.total,
        known_town_consumption=(
            first_town_forecast.center_consumption + first_town_forecast.known_shop_consumption
        ),
        expected_future_shop_consumption=(first_town_forecast.expected_future_shop_consumption),
        own_pending_supply=own_pending_supply,
        opponent_visible_supply=opponent_supply,
        projected_inventory=(
            current_inventory if first_projected_inventory is None else first_projected_inventory
        ),
        expected_unit_prices=tuple(prices),
        expected_average_price=revenue / max(1, expected_units),
        expected_revenue=revenue,
    )
