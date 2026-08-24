from kaggriculture_agent.economy import analyze_economy
from kaggriculture_agent.farm import analyze_farm
from kaggriculture_agent.features import build_strategic_features
from kaggriculture_agent.state import build_state
from kaggriculture_agent.strategy import RuleBasedStrategy
from tests.helpers import observation
from tests.test_economy import SeriesForecaster


class CarrotPriceForecaster(SeriesForecaster):
    def forecast_prices(self, prices, *, horizon_days):
        return type(super().forecast_prices(prices, horizon_days=horizon_days))(
            prices={
                "WHEAT": [1.0] * horizon_days,
                "CARROT": [1000.0] * horizon_days,
                "TOMATO": [1.0] * horizon_days,
                "STRAWBERRY": [1.0] * horizon_days,
                "MELON": [1.0] * horizon_days,
            },
            direction={},
        )


def test_strategy_uses_dynamic_price_series_when_selecting_a_crop():
    state = build_state(observation(day=1))
    economy = analyze_economy(state, forecaster=SeriesForecaster(0))
    features = build_strategic_features(state, analyze_farm(state), economy)

    assert RuleBasedStrategy._select_crop(features) == "WHEAT"


def test_strategy_uses_dynamic_price_series_for_a_late_crop_choice():
    state = build_state(observation(day=12))
    economy = analyze_economy(state, forecaster=CarrotPriceForecaster(0))
    features = build_strategic_features(state, analyze_farm(state), economy)

    assert RuleBasedStrategy._select_crop(features) == "CARROT"
