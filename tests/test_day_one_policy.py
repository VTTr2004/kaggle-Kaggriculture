from __future__ import annotations

from kaggriculture_agent.state import build_state
from kaggriculture_agent.strategy.day_one import (
    first_day_market_intents,
    first_day_unit_commands,
)


def _day_one_observation(*, step: int = 0, hands=None, tiles=None, seeds=None):
    board = tiles or [[None for _ in range(10)] for _ in range(10)]
    farm = {
        "money": 3000.0,
        "farmer": [4, 4],
        "hands": hands or [],
        "tiles": board,
        "unlocked_quadrants": ["NW", "NE"] if step else ["NW"],
        "hires_today": len(hands or []),
    }
    return {
        "player": 0,
        "step": step,
        "day": 0,
        "hour": step,
        "farms": [farm],
        "private": {
            "seeds": seeds or {"WHEAT": 50},
            "shed": {},
            "inventories": [{} for _ in range(1 + len(hands or []))],
        },
        "market": {"prices": {"WHEAT": 25}},
        "town": {"unlocked_shops": []},
    }


def test_first_day_buys_ne_hires_three_hands_and_fills_two_quadrants_with_wheat():
    state = build_state(_day_one_observation(), {"boardSize": 10, "episodeSteps": 720})

    commands = [intent.command for intent in first_day_market_intents(state)]

    assert commands == [
        ("BUY_LAND",),
        ("HIRE",),
        ("HIRE",),
        ("HIRE",),
        ("BUY_SEED", "WHEAT", 50),
    ]


def test_first_day_pairs_planters_with_followers_before_watering():
    hands = [[5, 4], [4, 5], [5, 5]]
    state = build_state(
        _day_one_observation(step=1, hands=hands),
        {"boardSize": 10, "episodeSteps": 720},
    )

    commands = first_day_unit_commands(state)

    assert commands == (
        ("PLANT", "WHEAT"),
        ("PLANT", "WHEAT"),
        ("NORTH",),
        ("NORTH",),
    )


def test_first_day_followers_water_the_planted_tiles_on_the_next_turn():
    tiles = [[None for _ in range(10)] for _ in range(10)]
    tiles[4][4] = {
        "kind": "PLANT",
        "crop": "WHEAT",
        "planted_day": 0,
        "watered_today": False,
        "yield_units": 1,
    }
    tiles[4][5] = {
        "kind": "PLANT",
        "crop": "WHEAT",
        "planted_day": 0,
        "watered_today": False,
        "yield_units": 1,
    }
    state = build_state(
        _day_one_observation(
            step=2,
            hands=[[5, 4], [4, 4], [5, 4]],
            tiles=tiles,
        ),
        {"boardSize": 10, "episodeSteps": 720},
    )

    commands = first_day_unit_commands(state)

    assert commands[2:] == (("WATER",), ("WATER",))
