"""Deterministic statistical market projections; no machine learning."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from statistics import mean, median, pstdev


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

    def forecast_prices(self, prices: Mapping[str, float], *, horizon_days: int) -> dict[str, list[float]]:
        return forecast_price_series(list(self._prices), prices, horizon_days=horizon_days)

    def statistics(self, prices: Mapping[str, float]) -> dict[str, dict[str, float]]:
        result: dict[str, dict[str, float]] = {}
        for product, raw_current in prices.items():
            key = str(product)
            values = [snapshot[key] for snapshot in self._prices if key in snapshot]
            values.append(float(raw_current))
            result[key] = {"mean": round(mean(values), 2), "median": round(median(values), 2),
                           "volatility": round(pstdev(values), 2) if len(values) > 1 else 0.0,
                           "low": round(min(values), 2), "high": round(max(values), 2)}
        return result
