from main import agent
from tests.helpers import observation


def test_agent_holds_inventory_when_forecast_is_neutral() -> None:
    tiles = [[None for _ in range(5)] for _ in range(5)]
    tiles[0][2] = {
        "kind": "PLANT",
        "crop": "MELON",
        "planted_day": 0,
        "watered_today": False,
        "consecutive_unwatered": 1,
        "yield_units": 1,
    }
    action = agent(observation(farmer=(0, 0), tiles=tiles, shed={"WHEAT": 3}, hour=3))
    assert action["farmer"] == ["EAST"]
    assert ["SELL", "WHEAT", 3] in action["market"]
    assert set(action) == {"farmer", "hands", "market"}


def test_agent_emits_exactly_one_action_per_existing_hand() -> None:
    obs = observation(hands=[[3, 4], [4, 3]], seeds={"MELON": 1})
    action = agent(obs)
    assert len(action["hands"]) == 2
    planted = [action["farmer"], *action["hands"]]
    assert sum(command[:1] == ["PLANT"] for command in planted) <= 1


def test_agent_fails_closed_on_bad_observation() -> None:
    assert agent({}) == {"farmer": ["PASS"], "hands": [], "market": []}


def test_shared_strategy_rejects_land_quote_without_farm_utilization() -> None:
    action = agent(observation(money=5000, hour=0))
    assert ["BUY_LAND"] not in action["market"]


def test_shared_strategy_accepts_land_quote_when_farm_is_saturated() -> None:
    tiles = [[None for _ in range(5)] for _ in range(5)]
    for index in range(20):
        x, y = index % 5, index // 5
        tiles[y][x] = {
            "kind": "PLANT",
            "crop": "MELON",
            "planted_day": 0,
            "watered_today": True,
            "consecutive_unwatered": 0,
            "yield_units": 1,
        }
    action = agent(observation(tiles=tiles, money=5000, hour=0))
    assert ["BUY_LAND"] in action["market"]
