from types import SimpleNamespace

import pytest

from kaggriculture_agent.state import build_state
from tests.helpers import observation


def test_state_normalizes_config_and_units() -> None:
    obs = observation(hands=[[3, 4]], inventories=[{}, {"WHEAT": 1}])
    config = SimpleNamespace(
        turnsPerDay=12,
        episodeSteps=120,
        boardSize=5,
        maxMarketOrdersPerTurn=7,
        shedCapacity=80,
        farmHandCostMult=2,
    )
    state = build_state(obs, config)
    assert state.total_days == 10
    assert state.unit_positions == ((4, 4), (3, 4))
    assert state.inventories[1]["WHEAT"] == 1
    assert state.max_market_orders == 7


def test_state_rejects_missing_farm() -> None:
    with pytest.raises(ValueError):
        build_state({"player": 0, "farms": []})
