from kaggriculture_agent.economy import analyze_economy
from kaggriculture_agent.state import build_state
from tests.helpers import observation


class SeriesForecaster:
    def __init__(self, _direction: int = 0) -> None:
        pass

    def observe(self, prices: dict[str, float]) -> None:
        pass

    def forecast_prices(self, prices: dict[str, float], *, horizon_days: int) -> dict[str, list[float]]:
        return {item: [200.0 if item == "WHEAT" else 1.0] * horizon_days for item in prices}




def test_profitable_crop_is_selected_from_feasible_opportunities() -> None:
    features = analyze_economy(build_state(observation(day=0)))
    assert features.crop_opportunities[0].crop == "MELON"
    assert features.crop_opportunities[0].expected_profit > 0


def test_shop_instances_increase_demand_independently() -> None:
    obs = observation()
    obs["town"]["unlocked_shops"] = ["PET_CAFE", "PET_CAFE"]
    features = analyze_economy(build_state(obs))
    assert features.demand["CARROT"] == 5  # center 1 + two cafes * 2


def test_shed_inventory_emits_sell_intent() -> None:
    state = build_state(observation(shed={"WHEAT": 7}))
    features = analyze_economy(state)
    assert features.sell_intents[0].command == ("SELL", "WHEAT", 7)


def test_economy_exposes_a_ten_day_price_series_for_farm_planning() -> None:
    from kaggriculture_agent.economy.forecast import StatisticalMarketForecaster
    forecaster = StatisticalMarketForecaster()
    features = analyze_economy(build_state(observation(day=1)), forecaster=forecaster)

    assert len(features.price_forecast["WHEAT"]) == build_state(
        observation(day=1)
    ).remaining_days
    assert features.price_forecast["WHEAT"][0] == 25.0
