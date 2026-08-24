"""Small deterministic random forecast used only for farm tests.

This is deliberately not a market model.  Replace it with the economy
member's real forecast function when that implementation is available.
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence

DEFAULT_TEST_BASE_PRICES: dict[str, float] = {
    "WHEAT": 25.0,
    "CARROT": 35.0,
    "TOMATO": 60.0,
    "STRAWBERRY": 120.0,
    "MELON": 250.0,
}


def random_price_forecast(
    crops: Sequence[str],
    horizon_days: int,
    *,
    seed: int = 0,
    base_prices: Mapping[str, float] | None = None,
    volatility: float = 0.15,
) -> dict[str, tuple[float, ...]]:
    """Return a reproducible random-walk price series for test scenarios."""

    if horizon_days < 0:
        raise ValueError("horizon_days must be non-negative")
    if volatility < 0:
        raise ValueError("volatility must be non-negative")

    bases = base_prices or DEFAULT_TEST_BASE_PRICES
    generator = random.Random(seed)
    result: dict[str, tuple[float, ...]] = {}
    for crop in crops:
        if crop not in bases:
            raise KeyError(f"missing base price for test crop: {crop}")
        price = float(bases[crop])
        values: list[float] = []
        for _ in range(horizon_days):
            price = max(1.0, price * (1.0 + generator.uniform(-volatility, volatility)))
            values.append(round(price, 2))
        result[crop] = tuple(values)
    return result
