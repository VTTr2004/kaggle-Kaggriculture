from kaggriculture_agent.economy.forecast import StatisticalMarketForecaster


def test_statistical_forecaster_uses_median_projection_and_basic_statistics() -> None:
    forecaster = StatisticalMarketForecaster(window=10)
    forecaster.observe({"MELON": 100})
    forecaster.observe({"MELON": 200})

    assert forecaster.forecast_prices({"MELON": 300}, horizon_days=3)["MELON"] == [150.0] * 3
    assert forecaster.statistics({"MELON": 300})["MELON"]["median"] == 200.0


def test_economy_no_longer_exposes_ml_direction_or_confidence() -> None:
    from tests.helpers import observation
    from kaggriculture_agent.economy import analyze_economy
    from kaggriculture_agent.state import build_state

    economy = analyze_economy(build_state(observation(day=1)))

    assert not hasattr(economy, "forecast_direction")
    assert not hasattr(economy, "forecast_confidence")
