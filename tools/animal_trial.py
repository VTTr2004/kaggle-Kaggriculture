"""Small end-to-end trial for buying, placing, feeding and harvesting a goose."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kaggle_environments import make


COOP_POSITION = (4, 4)


@dataclass(frozen=True)
class AnimalTrialResult:
    animal_alive: bool
    harvested_eggs: int
    fed_days: int


def _tile(observation: Any) -> Any:
    x, y = COOP_POSITION
    return observation["farms"][0]["tiles"][y][x]


def _farmer_inventory(observation: Any) -> dict[str, int]:
    inventories = observation.get("private", {}).get("inventories", [])
    return inventories[0] if inventories else {}


def goose_agent(observation: Any, configuration: Any) -> dict[str, list[Any]]:
    """Run the smallest valid goose lifecycle on the starting quadrant."""

    step = int(observation["step"])
    tile = _tile(observation)
    inventory = _farmer_inventory(observation)

    if step == 0:
        market = [["BUY_ANIMAL", "GOOSE", 1], ["BUY_PRODUCT", "WHEAT", 30]]
        farmer = ["BUILD_COOP"]
    elif (
        isinstance(tile, dict)
        and tile.get("kind") == "COOP"
        and "animal" not in tile
        and int(inventory.get("GOOSE", 0) or 0) > 0
    ):
        farmer = ["PLACE", "GOOSE"]
        market = []
    elif isinstance(tile, dict) and tile.get("kind") == "COOP" and "animal" not in tile:
        farmer = ["PICKUP", "GOOSE", 1]
        market = []
    elif isinstance(tile, dict) and "animal" in tile:
        market = []
        if not tile.get("fed_today", False):
            if int(inventory.get("WHEAT", 0) or 0) > 0:
                farmer = ["FEED"]
            else:
                farmer = ["PICKUP", "WHEAT", 5]
        elif int(tile.get("yield_units", 0) or 0) > 0:
            farmer = ["HARVEST"]
        elif tile.get("fertilizer_available", False):
            farmer = ["COLLECT_FERTILIZER"]
        elif not tile.get("cared_today", False):
            farmer = ["CARE"]
        else:
            farmer = ["PASS"]
    else:
        farmer = ["PASS"]
        market = []

    return {"farmer": farmer, "hands": [], "market": market}


def run_trial(steps: int = 120) -> AnimalTrialResult:
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": steps, "seed": 20260822},
        debug=True,
    )
    env.run([goose_agent, "pass"])

    harvested_eggs = 0
    fed_days: set[int] = set()
    for state in env.steps[:-1]:
        observation = state[0].observation
        action = goose_agent(observation, env.configuration)
        command = action["farmer"]
        if command[0] == "FEED":
            fed_days.add(int(observation["day"]))
        elif command[0] == "HARVEST":
            tile = _tile(observation)
            if isinstance(tile, dict):
                harvested_eggs += int(tile.get("yield_units", 0) or 0)

    final = env.steps[-1][0].observation
    tile = _tile(final)
    return AnimalTrialResult(
        animal_alive=isinstance(tile, dict) and tile.get("animal") == "GOOSE",
        harvested_eggs=harvested_eggs,
        fed_days=len(fed_days),
    )


if __name__ == "__main__":
    print(run_trial())
