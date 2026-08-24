"""Run reusable bot scenarios and collect comparable market metrics."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from kaggle_environments import make

Bot = Callable[[Mapping[str, Any], Any], dict[str, Any]]


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    steps: int
    rewards: tuple[float, ...]
    first_prices: dict[str, float]
    lowest_prices: dict[str, float]
    last_prices: dict[str, float]
    sold_by_player: dict[str, dict[str, int]]


def run_scenario(
    *,
    agents: Sequence[Bot],
    steps: int = 720,
    seed: int = 20260822,
    name: str = "scenario",
) -> ScenarioResult:
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": steps, "seed": seed},
        debug=False,
    )
    env.run(list(agents))

    first_prices: dict[str, float] = {}
    lowest_prices: dict[str, float] = {}
    last_prices: dict[str, float] = {}
    sold_by_player: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for frame in env.steps:
        for state in frame:
            observation = state.observation
            prices = observation.get("market", {}).get("prices", {}) or {}
            for item, raw_price in prices.items():
                price = float(raw_price)
                first_prices.setdefault(item, price)
                lowest_prices[item] = min(lowest_prices.get(item, price), price)
                last_prices[item] = price

            action = state.action or {}
            player = str(observation.get("player", 0))
            for order in action.get("market", []) or []:
                if len(order) >= 3 and order[0] == "SELL":
                    sold_by_player[player][order[1]] += int(order[2])

    final_states = env.steps[-1]
    rewards = tuple(float(state.reward or 0.0) for state in final_states)
    return ScenarioResult(
        name=name,
        steps=len(env.steps),
        rewards=rewards,
        first_prices=first_prices,
        lowest_prices=lowest_prices,
        last_prices=last_prices,
        sold_by_player={player: dict(items) for player, items in sold_by_player.items()},
    )


def result_to_dict(result: ScenarioResult) -> dict[str, Any]:
    return asdict(result)
