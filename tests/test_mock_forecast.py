from __future__ import annotations

from kaggriculture_agent.economy.mock_forecast import random_price_forecast


def test_random_price_forecast_is_reproducible_and_has_expected_shape() -> None:
    first = random_price_forecast(("CARROT", "MELON"), horizon_days=5, seed=7)
    second = random_price_forecast(("CARROT", "MELON"), horizon_days=5, seed=7)

    assert first == second
    assert set(first) == {"CARROT", "MELON"}
    assert all(len(prices) == 5 for prices in first.values())
    assert all(price > 0 for prices in first.values() for price in prices)


def test_random_price_forecast_uses_supplied_base_prices() -> None:
    forecast = random_price_forecast(
        ("CUSTOM",), horizon_days=1, seed=1, base_prices={"CUSTOM": 80}
    )

    assert 68 <= forecast["CUSTOM"][0] <= 92
