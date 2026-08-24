"""Trial runner: one crop sample per fixed route across two top quadrants."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from kaggle_environments import make

CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "WHEAT")
TARGETS = ((4, 4), (5, 4), (4, 3), (5, 3), (3, 4), (6, 4))
INITIAL_PLANTERS = {0: 0, 1: 1, 4: 2, 5: 3, 8: 4, 9: 5}
INITIAL_WATERERS = {2: 0, 3: 1, 6: 2, 7: 3, 10: 4, 11: 5}

CROP_RULES = {
    "WHEAT": (2, 4, False),
    "CARROT": (2, 3, False),
    "TOMATO": (8, 8, True),
    "STRAWBERRY": (10, 10, True),
    "MELON": (10, 12, False),
}


def _tile(observation: Any, position: tuple[int, int]) -> Any:
    x, y = position
    return observation["farms"][0]["tiles"][y][x]


def _position(observation: Any, unit_index: int) -> tuple[int, int]:
    farm = observation["farms"][0]
    return tuple(farm["farmer"] if unit_index == 0 else farm["hands"][unit_index - 1])


def _move(position: tuple[int, int], target: tuple[int, int]) -> str:
    x, y = position
    tx, ty = target
    if x < tx:
        return "EAST"
    if x > tx:
        return "WEST"
    if y < ty:
        return "SOUTH"
    if y > ty:
        return "NORTH"
    return "PASS"


def _initial_action(observation: Any, unit_index: int) -> list[Any]:
    route = INITIAL_PLANTERS.get(unit_index)
    if route is not None:
        position = _position(observation, unit_index)
        target = TARGETS[route]
        if position == target and _tile(observation, target) is None:
            return ["PLANT", CROPS[route]]
        return [_move(position, target)]

    route = INITIAL_WATERERS.get(unit_index)
    if route is not None:
        position = _position(observation, unit_index)
        target = TARGETS[route]
        value = _tile(observation, target)
        if position == target and isinstance(value, dict) and not value.get("watered_today", False):
            return ["WATER"]
        return [_move(position, target)]
    return ["PASS"]


def _ongoing_harvest_routes(observation: Any) -> tuple[int, ...]:
    """Return routes whose regrow crop has a harvest ready right now."""

    day = int(observation["day"])
    ready: list[int] = []
    for route, target in enumerate(TARGETS):
        value = _tile(observation, target)
        if not isinstance(value, dict) or value.get("kind") != "PLANT":
            continue
        first_day, _peak_day, ongoing = CROP_RULES[value["crop"]]
        age = day - int(value.get("planted_day", 0))
        if ongoing and age >= first_day and int(value.get("yield_units", 0) or 0) > 0:
            ready.append(route)
    return tuple(ready)


def _service_assignments(observation: Any, unit_count: int) -> tuple[tuple[int, bool], ...]:
    """Assign one primary worker per route and extras to ready regrow routes."""

    base_count = min(unit_count, len(TARGETS))
    assignments = [(route, True) for route in range(base_count)]
    ready_routes = _ongoing_harvest_routes(observation)
    for route in ready_routes[: max(0, unit_count - len(TARGETS))]:
        assignments.append((route, False))
    return tuple(assignments)


def _service_action(
    observation: Any,
    unit_index: int,
    route: int | None = None,
    allow_harvest: bool = True,
) -> list[Any]:
    if route is None:
        return ["PASS"]
    position = _position(observation, unit_index)
    target = TARGETS[route]
    value = _tile(observation, target)
    if not isinstance(value, dict) or value.get("kind") != "PLANT":
        return ["PASS"]

    first_day, peak_day, ongoing = CROP_RULES[value["crop"]]
    age = int(observation["day"]) - int(value.get("planted_day", 0))
    ready = int(value.get("yield_units", 0) or 0) > 0 and (ongoing or age >= peak_day)
    if position == target and ready and allow_harvest:
        return ["HARVEST"]
    if position == target and not value.get("watered_today", False):
        return ["WATER"]
    return [_move(position, target)]


def crop_route_agent(observation: Any, configuration: Any) -> dict[str, list[Any]]:
    step = int(observation["step"])
    day = int(observation["day"])
    hour = int(observation["hour"])
    if step == 0:
        market = [["BUY_LAND"], *([["HIRE"]] * 8), ["BUY_SEED", "WHEAT", 2]]
    elif step == 1:
        market = [
            ["HIRE"],
            ["HIRE"],
            ["HIRE"],
            ["BUY_SEED", "CARROT", 1],
            ["BUY_SEED", "TOMATO", 1],
            ["BUY_SEED", "STRAWBERRY", 1],
            ["BUY_SEED", "MELON", 1],
        ]
    elif day > 0 and hour == 0:
        market = [["HIRE"]] * (5 + len(_ongoing_harvest_routes(observation)))
    else:
        market = []

    hands = observation["farms"][0].get("hands", [])
    count = 1 + len(hands)
    if day == 0:
        commands = [_initial_action(observation, index) for index in range(count)]
    else:
        assignments = _service_assignments(observation, count)
        commands = [
            _service_action(observation, index, route, allow_harvest)
            for index, (route, allow_harvest) in enumerate(assignments)
        ]
    return {"farmer": commands[0], "hands": commands[1:], "market": market}


def run(steps: int = 720) -> None:
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": steps, "seed": 20260822},
        debug=True,
    )
    env.run([crop_route_agent, "pass"])

    route_stats = [
        {"crop": crop, "plant": 0, "water": 0, "harvest": 0, "units": 0} for crop in CROPS
    ]
    daily = defaultdict(lambda: {"plant": 0, "water": 0, "harvest": 0, "units": 0})
    for state in env.steps[:-1]:
        observation = state[0].observation
        action = crop_route_agent(observation, env.configuration)
        commands = [action["farmer"], *action["hands"]]
        assignments = (
            _service_assignments(observation, len(commands)) if int(observation["day"]) > 0 else ()
        )
        for index, command in enumerate(commands):
            if index not in INITIAL_PLANTERS and int(observation["day"]) == 0:
                continue
            if int(observation["day"]) > 0 and index >= len(assignments):
                continue
            route = (
                INITIAL_PLANTERS[index] if int(observation["day"]) == 0 else assignments[index][0]
            )
            stats = route_stats[route]
            day_stats = daily[int(observation["day"])]
            if command[0] == "PLANT":
                stats["plant"] += 1
                day_stats["plant"] += 1
            elif command[0] == "WATER":
                stats["water"] += 1
                day_stats["water"] += 1
            elif command[0] == "HARVEST":
                stats["harvest"] += 1
                day_stats["harvest"] += 1
                value = _tile(observation, TARGETS[route])
                units = int(value.get("yield_units", 0) or 0) if isinstance(value, dict) else 0
                stats["units"] += units
                day_stats["units"] += units

    final = env.steps[-1][0].observation
    print("route_results=")
    for index, stats in enumerate(route_stats, 1):
        print(index, stats, "final_tile=", _tile(final, TARGETS[index - 1]))
    print("daily_summary=", dict(daily))
    print("final_day=", final["day"], "final_money=", final["farms"][0]["money"])
    print("final_hands=", len(final["farms"][0].get("hands", [])))
    print("duplicate_route_targets=", len(set(TARGETS)) != len(TARGETS))


if __name__ == "__main__":
    run()
