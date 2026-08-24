from kaggriculture_agent.economy.forecast import StatisticalMarketForecaster, forecast_price_series


def test_statistical_forecaster_returns_median_projection() -> None:
    forecaster = StatisticalMarketForecaster()
    forecaster.observe({"WHEAT": 25.0, "CARROT": 35.0})
    forecaster.observe({"WHEAT": 26.0, "CARROT": 34.0})
    result = forecaster.forecast_prices({"WHEAT": 27.0, "CARROT": 33.0}, horizon_days=3)
    assert result == {"WHEAT": [25.5] * 3, "CARROT": [34.5] * 3}


def test_statistical_forecaster_exposes_descriptive_statistics() -> None:
    forecaster = StatisticalMarketForecaster()
    forecaster.observe({"WHEAT": 25.0})
    stats = forecaster.statistics({"WHEAT": 27.0})["WHEAT"]
    assert stats["mean"] == 26.0
    assert stats["low"] == 25.0
    assert stats["high"] == 27.0


def test_forecast_price_series_returns_daily_prices_and_binary_direction() -> None:
    history = [
        {"WHEAT": 25.0, "CARROT": 35.0},
        {"WHEAT": 26.0, "CARROT": 34.0},
        {"WHEAT": 27.0, "CARROT": 33.0},
    ]
    result = forecast_price_series(history, {"WHEAT": 27.0, "CARROT": 33.0}, horizon_days=3)

    assert set(result) == {"WHEAT", "CARROT"}
    assert all(len(values) == 3 for values in result.values())
    assert result == {"WHEAT": [26.0] * 3, "CARROT": [34.0] * 3}
