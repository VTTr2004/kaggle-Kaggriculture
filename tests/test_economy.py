from types import SimpleNamespace

import pytest
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
from kaggriculture_agent.economy_v2 import build_economy_snapshot_v2
from kaggriculture_agent.economy_v2.demand import (
    TownDemandForecastV2,
    forecast_town_demand_v2,
    next_shop_probabilities_v2,
)
from kaggriculture_agent.economy_v2.pricing import (
    LockstepMarketQuoteV2,
    MarketOrderV2,
    OrderQuoteV2,
    market_price_v2,
    price_breakdown_v2,
    quote_buy_product_v2,
    quote_lockstep_market_v2,
    quote_sell_v2,
    shape_value_v2,
)
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


def test_v2_snapshot_tracks_exact_time_and_shed_capacity() -> None:
    config = SimpleNamespace(
        episodeSteps=720,
        turnsPerDay=24,
        shedCapacity=10,
        townShopUnlockInterval=3,
        townShopSellInterval=4,
        townCenterSellInterval=24,
    )
    state = build_state(observation(day=29, hour=23, shed={"WHEAT": 7}), config)

    snapshot = build_economy_snapshot_v2(state)

    assert snapshot.step == 719
    assert snapshot.remaining_turns == 1
    assert snapshot.remaining_days == 1
    assert snapshot.turns_per_day == 24
    assert snapshot.town_shop_unlock_interval == 3
    assert snapshot.town_shop_sell_interval == 4
    assert snapshot.town_center_sell_interval == 24
    assert snapshot.shed_usage == 7
    assert snapshot.shed_free_capacity == 3


def test_v2_snapshot_separates_observable_own_supply_sources() -> None:
    obs = observation(shed={"WHEAT": 2}, inventories=[{"WHEAT": 3, "CARROT": 1}])
    obs["farms"][0]["tiles"][0][0] = {
        "kind": "PLANT",
        "crop": "WHEAT",
        "yield_units": 4,
    }

    snapshot = build_economy_snapshot_v2(build_state(obs))

    assert snapshot.own_shed_supply == {"WHEAT": 2}
    assert snapshot.own_carried_supply == {"WHEAT": 3, "CARROT": 1}
    assert snapshot.own_ready_supply == {"WHEAT": 4}
    assert snapshot.own_crop_counts == {"WHEAT": 1}


def test_v2_snapshot_reads_only_public_opponent_signals() -> None:
    obs = observation()
    obs["farms"][1].update(
        {
            "shed": {"MELON": 99},
            "seeds": {"MELON": 99},
            "inventories": [{"MELON": 99}],
            "hands": [[1, 1]],
            "unlocked_quadrants": ["NW", "NE"],
        }
    )
    obs["farms"][1]["tiles"][0][0] = {
        "kind": "PLANT",
        "crop": "MELON",
        "yield_units": 4,
    }

    snapshot = build_economy_snapshot_v2(build_state(obs))

    assert snapshot.opponent_ready_supply == {"MELON": 4}
    assert snapshot.opponent_crop_counts == {"MELON": 1}
    assert snapshot.opponent_hands == 1
    assert snapshot.opponent_unlocked_land_count == 2
    assert not hasattr(snapshot, "opponent_shed")
    assert not hasattr(snapshot, "opponent_seeds")
    assert not hasattr(snapshot, "opponent_inventories")


def test_v2_price_curve_matches_official_interpreter_boundaries() -> None:
    for item, params in OFFICIAL_MARKET_PARAMS.items():
        equilibrium = int(params["I0"])
        throughput = int(params["T"])
        for inventory in (
            equilibrium - throughput,
            equilibrium,
            equilibrium + throughput,
            equilibrium + 2 * throughput,
        ):
            assert market_price_v2(item, inventory) == official_market_price(item, inventory)


def test_v2_price_breakdown_explains_selected_side_and_shape() -> None:
    scarcity = price_breakdown_v2("CARROT", 9550)
    glut = price_breakdown_v2("CARROT", 10450)

    assert scarcity.side == "scarcity"
    assert scarcity.function == "hinge"
    assert scarcity.quoted_price == 70
    assert glut.side == "glut"
    assert glut.function == "sqrt"
    assert glut.quoted_price == 10


def test_v2_hinge_changes_from_linear_to_accelerating_after_throughput() -> None:
    assert shape_value_v2("hinge", 225, 450) == 0.5
    assert shape_value_v2("hinge", 450, 450) == 1.0
    assert shape_value_v2("hinge", 900, 450) == 10.0


def test_v2_pricing_uses_market_parameter_overrides_without_mutating_them() -> None:
    overrides = {
        "WHEAT": {
            "base": 30,
            "I0": 10000,
            "T": 500,
            "below_func": "linear",
            "below_target": 0.5,
            "above_func": "linear",
            "above_target": 0.5,
        }
    }

    assert market_price_v2("WHEAT", 9500, overrides) == 45
    assert overrides["WHEAT"]["base"] == 30


def test_v2_sell_quote_prices_each_unit_sequentially() -> None:
    quote = quote_sell_v2("WHEAT", 3, 9600)

    assert isinstance(quote, OrderQuoteV2)
    assert quote.operation == "SELL"
    assert quote.unit_prices == (
        market_price_v2("WHEAT", 9600),
        market_price_v2("WHEAT", 9601),
        market_price_v2("WHEAT", 9602),
    )
    assert quote.total == sum(quote.unit_prices)
    assert quote.average_price == quote.total / 3
    assert quote.ending_inventory == 9603


def test_v2_sell_quote_does_not_add_supply_at_price_floor() -> None:
    quote = quote_sell_v2("MELON", 3, 10300)

    assert quote.unit_prices == (1, 1, 1)
    assert quote.total == 3
    assert quote.average_price == 1
    assert quote.ending_inventory == 10300


def test_v2_zero_quantity_sell_quote_is_empty() -> None:
    quote = quote_sell_v2("WHEAT", 0, 10000)

    assert quote.quantity == 0
    assert quote.unit_prices == ()
    assert quote.total == 0
    assert quote.average_price == 0
    assert quote.ending_inventory == 10000


def test_v2_sell_quote_rejects_negative_quantity() -> None:
    with pytest.raises(ValueError, match="quantity"):
        quote_sell_v2("WHEAT", -1, 10000)


def test_v2_buy_product_quote_prices_at_post_buy_inventory() -> None:
    quote = quote_buy_product_v2("WHEAT", 3, 10000)

    assert isinstance(quote, OrderQuoteV2)
    assert quote.operation == "BUY_PRODUCT"
    assert quote.unit_prices == (
        market_price_v2("WHEAT", 9999),
        market_price_v2("WHEAT", 9998),
        market_price_v2("WHEAT", 9997),
    )
    assert quote.unit_prices == (26, 26, 27)
    assert quote.total == 79
    assert quote.average_price == 79 / 3
    assert quote.ending_inventory == 9997


def test_v2_buy_then_sell_round_trip_nets_zero_against_unchanged_market() -> None:
    buy = quote_buy_product_v2("WHEAT", 1, 10000)
    sell = quote_sell_v2("WHEAT", 1, buy.ending_inventory)

    assert buy.total == sell.total
    assert sell.ending_inventory == 10000


def test_v2_zero_quantity_buy_product_quote_is_empty() -> None:
    quote = quote_buy_product_v2("FERTILIZER", 0, 10000)

    assert quote.quantity == 0
    assert quote.unit_prices == ()
    assert quote.total == 0
    assert quote.average_price == 0
    assert quote.ending_inventory == 10000


def test_v2_buy_product_quote_rejects_invalid_product_or_quantity() -> None:
    with pytest.raises(ValueError, match="WHEAT or FERTILIZER"):
        quote_buy_product_v2("CARROT", 1, 10000)
    with pytest.raises(ValueError, match="quantity"):
        quote_buy_product_v2("WHEAT", -1, 10000)


def test_v2_lockstep_quotes_both_players_from_same_precommit_inventory() -> None:
    result = quote_lockstep_market_v2(
        {"STRAWBERRY": 10000},
        (
            (MarketOrderV2("SELL", "STRAWBERRY", 1),),
            (MarketOrderV2("SELL", "STRAWBERRY", 1),),
        ),
    )

    assert isinstance(result, LockstepMarketQuoteV2)
    assert result.player_order_quotes[0][0].unit_prices == (120,)
    assert result.player_order_quotes[1][0].unit_prices == (120,)
    assert market_price_v2("STRAWBERRY", 10001) == 118
    assert result.ending_inventory["STRAWBERRY"] == 10002


def test_v2_lockstep_processes_order_queues_by_shared_order_index() -> None:
    result = quote_lockstep_market_v2(
        {"STRAWBERRY": 10000},
        (
            (
                MarketOrderV2("SELL", "STRAWBERRY", 1),
                MarketOrderV2("SELL", "STRAWBERRY", 1),
            ),
            (MarketOrderV2("SELL", "STRAWBERRY", 1),),
        ),
    )

    assert [quote.unit_prices for quote in result.player_order_quotes[0]] == [(120,), (116,)]
    assert [quote.unit_prices for quote in result.player_order_quotes[1]] == [(120,)]
    assert result.ending_inventory["STRAWBERRY"] == 10003


def test_v2_lockstep_can_quote_a_buy_and_sell_in_the_same_round() -> None:
    starting_inventory = {"WHEAT": 10000}
    result = quote_lockstep_market_v2(
        starting_inventory,
        (
            (MarketOrderV2("SELL", "WHEAT", 1),),
            (MarketOrderV2("BUY_PRODUCT", "WHEAT", 1),),
        ),
    )

    assert result.player_order_quotes[0][0].unit_prices == (25,)
    assert result.player_order_quotes[1][0].unit_prices == (26,)
    assert result.ending_inventory["WHEAT"] == 10000
    assert starting_inventory == {"WHEAT": 10000}


def test_v2_lockstep_rejects_invalid_queue_shape_or_order() -> None:
    with pytest.raises(ValueError, match="exactly two"):
        quote_lockstep_market_v2(
            {"WHEAT": 10000},
            ((MarketOrderV2("SELL", "WHEAT", 1),),),
        )
    with pytest.raises(ValueError, match="WHEAT or FERTILIZER"):
        quote_lockstep_market_v2(
            {"CARROT": 10000},
            (
                (MarketOrderV2("BUY_PRODUCT", "CARROT", 1),),
                (),
            ),
        )


def test_v2_next_shop_probabilities_are_uniform_until_instance_cap() -> None:
    probabilities = next_shop_probabilities_v2(("PET_CAFE", "PET_CAFE", "BAKERY"))

    assert len(probabilities) == 8
    assert sum(probabilities.values()) == 1
    assert all(probability == 0.125 for probability in probabilities.values())
    assert next_shop_probabilities_v2(("PET_CAFE",) * 8) == {}


def test_v2_town_demand_counts_duplicate_known_shops_and_center_ticks() -> None:
    obs = observation()
    obs["town"]["unlocked_shops"] = ["PET_CAFE", "PET_CAFE"]
    snapshot = build_economy_snapshot_v2(build_state(obs))

    forecast = forecast_town_demand_v2(snapshot, "CARROT", end_step=72)

    assert isinstance(forecast, TownDemandForecastV2)
    assert forecast.known_center_consumption == 3
    assert forecast.known_shop_consumption == 72
    assert forecast.expected_future_shop_consumption == 0
    assert forecast.total_expected_consumption == 75
    assert sum(event.quantity_expected for event in forecast.consumption_events) == 75


def test_v2_town_demand_forecasts_unlock_timing_and_random_shop_scenarios() -> None:
    snapshot = build_economy_snapshot_v2(build_state(observation()))

    forecast = forecast_town_demand_v2(snapshot, "WHEAT", end_step=144)

    assert forecast.future_shop_unlock_steps == (72,)
    assert forecast.known_center_consumption == 6
    assert forecast.known_shop_consumption == 0
    assert forecast.future_shop_consumption_low == 0
    assert forecast.expected_future_shop_consumption == pytest.approx(11.25)
    assert forecast.future_shop_consumption_high == 18
    assert forecast.total_expected_consumption == pytest.approx(17.25)
    assert (
        forecast.total_consumption_low
        <= forecast.total_expected_consumption
        <= forecast.total_consumption_high
    )


def test_v2_future_shop_only_consumes_after_end_of_day_unlock() -> None:
    snapshot = build_economy_snapshot_v2(build_state(observation(day=2, hour=23)))

    forecast = forecast_town_demand_v2(snapshot, "WHEAT", end_step=73)

    assert snapshot.step == 71
    assert forecast.future_shop_unlock_steps == (72,)
    assert forecast.known_center_consumption == 1
    assert forecast.expected_future_shop_consumption == pytest.approx(0.625)
    assert forecast.total_expected_consumption == pytest.approx(1.625)


def test_v2_town_center_never_consumes_fertilizer() -> None:
    snapshot = build_economy_snapshot_v2(build_state(observation()))

    forecast = forecast_town_demand_v2(snapshot, "FERTILIZER", end_step=72)

    assert forecast.known_center_consumption == 0
    assert forecast.total_expected_consumption == 0


def test_v2_town_demand_respects_eight_shop_instance_cap() -> None:
    obs = observation()
    obs["town"]["unlocked_shops"] = ["BAKERY"] * 8
    snapshot = build_economy_snapshot_v2(build_state(obs))

    forecast = forecast_town_demand_v2(snapshot, "WHEAT", end_step=216)

    assert forecast.next_shop_probabilities == {}
    assert forecast.future_shop_unlock_steps == ()
    assert forecast.expected_future_shop_consumption == 0
