from kaggle_environments.envs.kaggriculture.kaggriculture import (
    MARKET_PARAMS as OFFICIAL_MARKET_PARAMS,
)
from kaggle_environments.envs.kaggriculture.kaggriculture import (
    market_price as official_market_price,
)

from kaggriculture_agent.economy import analyze_economy, build_economy_snapshot
from kaggriculture_agent.economy.forecast import (
    forecast_crop,
    town_consumption_breakdown_until,
    town_consumption_until,
)
from kaggriculture_agent.economy.pricing import (
    DEFAULT_MARKET_PARAMS,
    market_price,
    price_breakdown,
)
from kaggriculture_agent.economy.selling import quote_sell_order
from kaggriculture_agent.state import build_state
from tests.helpers import observation


class SeriesForecaster:
    def __init__(self, _direction: int = 0) -> None:
        pass

    def observe(self, prices: dict[str, float]) -> None:
        pass

    def forecast_prices(
        self, prices: dict[str, float], *, horizon_days: int
    ) -> dict[str, list[float]]:
        return {item: [200.0 if item == "WHEAT" else 1.0] * horizon_days for item in prices}


def test_profitable_crop_is_selected_from_feasible_opportunities() -> None:
    features = analyze_economy(build_state(observation(day=0)))
    assert features.crop_opportunities[0].crop == "MELON"
    assert features.crop_opportunities[0].expected_profit > 0


def test_shop_instances_increase_demand_independently() -> None:
    obs = observation()
    obs["town"]["unlocked_shops"] = ["PET_CAFE", "PET_CAFE"]
    features = analyze_economy(build_state(obs))
    # Town center consumes 1/day. Each cafe consumes 2 carrots every 4
    # turns = 12/day, and duplicate shop instances count independently.
    assert features.demand["CARROT"] == 25


def test_price_curve_matches_official_interpreter_boundaries() -> None:
    for item, params in OFFICIAL_MARKET_PARAMS.items():
        equilibrium = int(params["I0"])
        throughput = int(params["T"])
        for inventory in (
            equilibrium - throughput,
            equilibrium,
            equilibrium + throughput,
            equilibrium + 2 * throughput,
        ):
            assert market_price(item, inventory) == official_market_price(item, inventory)
        assert DEFAULT_MARKET_PARAMS[item] == params


def test_price_breakdown_reconstructs_official_quote() -> None:
    detail = price_breakdown("MELON", 10150)

    assert detail.side == "glut"
    assert detail.function == "sq"
    assert detail.quoted_price == official_market_price("MELON", 10150)
    assert detail.raw_price == detail.base - detail.amplitude * detail.shape_at_distance


def test_forecast_uses_exact_town_schedule_and_visible_opponent_supply() -> None:
    obs = observation()
    obs["town"]["unlocked_shops"] = ["PET_CAFE", "PET_CAFE"]
    obs["market"]["inventory"]["CARROT"] = 10000
    obs["farms"][1]["tiles"][0][0] = {
        "kind": "PLANT",
        "crop": "CARROT",
        "yield_units": 3,
    }
    state = build_state(obs)
    snapshot = build_economy_snapshot(state)
    forecast = forecast_crop(state, snapshot, "CARROT")

    # Three days contain 3 town-center events and 18 shop events. Each of the
    # two cafes consumes 2 carrots per shop event: 3 + 18 * 4 = 75.
    assert town_consumption_until(state, snapshot, "CARROT", 3) == 75
    assert forecast.projected_inventory == 10000 - 75 + 3
    assert forecast.opponent_visible_supply == 3


def test_ongoing_crop_forecast_lists_each_production_day() -> None:
    state = build_state(observation())
    snapshot = build_economy_snapshot(state)

    assert forecast_crop(state, snapshot, "TOMATO").yield_days == (8, 9, 10, 11)
    assert forecast_crop(state, snapshot, "STRAWBERRY").yield_days == (10, 12, 14, 16)
    assert forecast_crop(state, snapshot, "MELON").yield_days == (10,)


def test_future_random_shop_demand_is_an_explicit_expectation() -> None:
    state = build_state(observation())
    snapshot = build_economy_snapshot(state)

    detail = town_consumption_breakdown_until(state, snapshot, "WHEAT", 6)

    assert detail.center_consumption == 6
    assert detail.known_shop_consumption == 0
    assert detail.expected_future_shop_consumption > 0


def test_sell_quote_moves_inventory_one_unit_at_a_time() -> None:
    quote = quote_sell_order("MELON", 3, 10000)

    assert quote.unit_prices == (
        official_market_price("MELON", 10000),
        official_market_price("MELON", 10001),
        official_market_price("MELON", 10002),
    )
    assert quote.ending_inventory == 10003


def test_sell_quote_does_not_add_supply_at_price_floor() -> None:
    quote = quote_sell_order("MELON", 3, 10300)

    assert quote.unit_prices == (1, 1, 1)
    assert quote.ending_inventory == 10300


def test_shed_inventory_emits_sell_intent() -> None:
    state = build_state(observation(shed={"WHEAT": 7}, day=29))
    features = analyze_economy(state)
    assert features.market_intents[0].command == ("SELL", "WHEAT", 7)
    assert features.sell_intents[0].command == ("SELL", "WHEAT", 7)


def test_economy_exposes_a_ten_day_price_series_for_farm_planning() -> None:
    from kaggriculture_agent.economy.forecast import StatisticalMarketForecaster

    forecaster = StatisticalMarketForecaster()
    features = analyze_economy(build_state(observation(day=1)), forecaster=forecaster)

    assert len(features.price_forecast["WHEAT"]) == build_state(observation(day=1)).remaining_days
    assert features.price_forecast["WHEAT"][0] == 25.0


def test_sell_forecast_can_hold_when_next_day_quote_is_better() -> None:
    features = analyze_economy(build_state(observation(shed={"WHEAT": 7})))

    sell = features.sell_opportunities[0]
    assert sell.hold_revenue > sell.immediate_revenue
    assert not sell.recommend_sell
    assert not features.market_intents


def test_snapshot_uses_only_public_opponent_supply() -> None:
    obs = observation()
    obs["farms"][1]["tiles"][0][0] = {
        "kind": "PLANT",
        "crop": "MELON",
        "yield_units": 4,
    }
    snapshot = build_economy_snapshot(build_state(obs))
    assert snapshot.opponent_crop_counts == {"MELON": 1}
    assert snapshot.opponent_visible_supply == {"MELON": 4}


def test_snapshot_counts_own_unsold_and_committed_crop_supply() -> None:
    obs = observation(shed={"MELON": 2}, inventories=[{"MELON": 3}])
    obs["farms"][0]["tiles"][0][0] = {
        "kind": "PLANT",
        "crop": "MELON",
        "yield_units": 1,
    }

    snapshot = build_economy_snapshot(build_state(obs))

    # Two in shed + three carried + six expected from the existing plant.
    assert snapshot.own_pending_supply["MELON"] == 11


def test_economy_quotes_hiring_but_does_not_schedule_units() -> None:
    features = analyze_economy(build_state(observation(hour=0)))
    assert [intent.command for intent in features.investment_intents].count(("HIRE",)) == 4
    assert not hasattr(features, "unit_intents")
