from kaggriculture_agent.economy import analyze_economy
from kaggriculture_agent.features import build_strategic_features
from kaggriculture_agent.farm import analyze_farm
from kaggriculture_agent.models import EconomyFeatures
from kaggriculture_agent.state import build_state
from kaggriculture_agent.strategy import RuleBasedStrategy
from tests.helpers import observation


def test_farmer_chooses_highest_priority_seed_that_is_in_inventory() -> None:
    state = build_state(
        observation(
            day=1,
            seeds={"WHEAT": 4, "MELON": 2},
        )
    )
    economy = analyze_economy(state)
    economy = EconomyFeatures(
        crop_opportunities=economy.crop_opportunities,
        sell_intents=economy.sell_intents,
        demand=economy.demand,
        price_ratios=economy.price_ratios,
        price_forecast=economy.price_forecast,
        seed_priority={"WHEAT": 1.0, "MELON": 2.0},
        buy_intents=(),
    )
    features = build_strategic_features(state, analyze_farm(state), economy)

    assert RuleBasedStrategy._select_crop(features) == "MELON"


def test_farmer_falls_back_to_next_priority_seed_when_top_seed_is_empty() -> None:
    state = build_state(observation(day=1, seeds={"WHEAT": 4}))
    economy = analyze_economy(state)
    economy = EconomyFeatures(
        crop_opportunities=economy.crop_opportunities,
        sell_intents=economy.sell_intents,
        demand=economy.demand,
        price_ratios=economy.price_ratios,
        price_forecast=economy.price_forecast,
        seed_priority={"MELON": 2.0, "WHEAT": 1.0},
        buy_intents=(),
    )
    features = build_strategic_features(state, analyze_farm(state), economy)

    assert RuleBasedStrategy._select_crop(features) == "WHEAT"
