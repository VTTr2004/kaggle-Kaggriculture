from kaggriculture_agent.economy import analyze_economy
from kaggriculture_agent.state import build_state
from tests.helpers import observation


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
