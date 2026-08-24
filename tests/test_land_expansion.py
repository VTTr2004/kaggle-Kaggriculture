from dataclasses import replace

from kaggriculture_agent.economy import analyze_economy
from kaggriculture_agent.farm import analyze_farm
from kaggriculture_agent.features import build_strategic_features
from kaggriculture_agent.models import AgentSettings
from kaggriculture_agent.state import build_state
from kaggriculture_agent.strategy import RuleBasedStrategy
from tests.helpers import observation
from tests.test_economy import SeriesForecaster


def _empty_nw_board() -> list[list[object]]:
    board = [["LOCKED" for _ in range(10)] for _ in range(10)]
    for y in range(5):
        for x in range(5):
            board[y][x] = None
    return board


def test_expands_when_land_and_seeds_for_new_empty_tiles_are_affordable():
    state = build_state(
        observation(
            day=1,
            hour=0,
            money=1500,
            tiles=_empty_nw_board(),
        ),
        {"boardSize": 10, "episodeSteps": 720},
    )
    features = build_strategic_features(
        state, analyze_farm(state), analyze_economy(state)
    )

    intents = RuleBasedStrategy(AgentSettings())._market_intents(features, "WHEAT")
    commands = [intent.command for intent in intents]

    assert ("BUY_LAND",) in commands
    assert any(command[0] == "BUY_SEED" for command in commands)


def test_expands_using_the_value_of_products_in_the_shed():
    state = build_state(
        observation(
            day=1,
            hour=0,
            money=1200,
            shed={"WHEAT": 20},
            tiles=_empty_nw_board(),
        ),
        {"boardSize": 10, "episodeSteps": 720},
    )
    features = build_strategic_features(
        state, analyze_farm(state), analyze_economy(state)
    )

    intents = RuleBasedStrategy(AgentSettings())._market_intents(features, "WHEAT")
    commands = [intent.command for intent in intents]

    assert ("SELL", "WHEAT", 20) in commands
    assert ("BUY_LAND",) in commands
    assert any(command[0] == "BUY_SEED" for command in commands)


def test_expansion_check_includes_projected_hardcoded_farm_profit():
    state = build_state(
        observation(
            day=1,
            hour=0,
            money=0,
            tiles=_empty_nw_board(),
        ),
        {"boardSize": 10, "episodeSteps": 720},
    )
    state = replace(state, harvested_previous_day=True)
    features = build_strategic_features(
        state, analyze_farm(state), analyze_economy(state, forecaster=SeriesForecaster(0))
    )

    intents = RuleBasedStrategy(AgentSettings())._market_intents(features, "WHEAT")
    commands = [intent.command for intent in intents]

    assert ("BUY_LAND",) in commands
    assert ("BUY_SEED", "WHEAT", 50) in commands


def test_projected_profit_is_not_rechecked_without_a_previous_day_harvest():
    state = build_state(
        observation(
            day=1,
            hour=0,
            money=0,
            tiles=_empty_nw_board(),
        ),
        {"boardSize": 10, "episodeSteps": 720},
    )
    features = build_strategic_features(
        state, analyze_farm(state), analyze_economy(state)
    )

    intents = RuleBasedStrategy(AgentSettings())._market_intents(features, "WHEAT")

    assert ("BUY_LAND",) not in [intent.command for intent in intents]
