from kaggriculture_agent.farm import analyze_farm, plan_unit_actions
from kaggriculture_agent.farm.pathfinding import next_move
from kaggriculture_agent.state import build_state
from tests.helpers import observation


def test_weed_uses_official_dig_action() -> None:
    tiles = [[None for _ in range(5)] for _ in range(5)]
    tiles[2][1] = {"kind": "WEED"}
    features = analyze_farm(build_state(observation(tiles=tiles)))
    weed_task = next(task for task in features.tasks if task.category == "dig")
    assert weed_task.command == ("DIG",)
    assert weed_task.target == (1, 2)


def test_unwatered_plant_is_urgent() -> None:
    tiles = [[None for _ in range(5)] for _ in range(5)]
    tiles[4][4] = {
        "kind": "PLANT",
        "crop": "CARROT",
        "planted_day": 0,
        "watered_today": False,
        "consecutive_unwatered": 1,
        "yield_units": 1,
    }
    features = analyze_farm(build_state(observation(tiles=tiles, day=1, hour=20)))
    water = next(task for task in features.tasks if task.category == "water")
    assert water.priority >= 900
    assert water.command == ("WATER",)


def test_pathfinding_uses_official_directions() -> None:
    assert next_move((0, 0), (2, 0)) == ("EAST",)
    assert next_move((2, 2), (2, 0)) == ("NORTH",)


def test_farm_planner_consumes_shared_crop_choice_without_pricing() -> None:
    state = build_state(observation(seeds={"CARROT": 1}))
    features = analyze_farm(state)
    intents = plan_unit_actions(state, features, selected_crop="CARROT")
    assert intents[0].command == ("PLANT", "CARROT")
    assert features.utilization == 0.0
