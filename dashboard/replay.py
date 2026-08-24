"""Run deterministic local matches for the learning dashboard."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from kaggle_environments import make

from kaggriculture_agent.agent import agent as kaggriculture_agent

OPPONENTS = ("pass", "random", "starter")


def _plain(value: Any) -> Any:
    """Recursively detach Kaggle Struct values from the live environment."""
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_plain(item) for item in value]
    return value


@dataclass(frozen=True)
class LocalReplay:
    seed: int
    opponent: str
    player: int
    configuration: Mapping[str, Any]
    steps: tuple[tuple[Mapping[str, Any], ...], ...]

    @property
    def turn_count(self) -> int:
        return len(self.steps)

    @property
    def final_rewards(self) -> tuple[float | None, ...]:
        return tuple(agent.get("reward") for agent in self.steps[-1])

    @property
    def final_statuses(self) -> tuple[str, ...]:
        return tuple(str(agent.get("status", "")) for agent in self.steps[-1])


def run_local_match(
    seed: int = 20260822,
    opponent: str = "starter",
    player: int = 0,
    steps: int = 720,
) -> LocalReplay:
    """Run our real agent against a built-in opponent and retain every state."""
    if opponent not in OPPONENTS:
        raise ValueError(f"opponent must be one of {OPPONENTS}")
    if player not in (0, 1):
        raise ValueError("player must be 0 or 1")
    if steps <= 0:
        raise ValueError("steps must be positive")

    environment = make(
        "kaggriculture",
        configuration={"episodeSteps": steps, "seed": int(seed)},
        debug=True,
    )
    agents = [kaggriculture_agent, opponent]
    if player == 1:
        agents.reverse()
    environment.run(agents)

    raw = environment.toJSON()
    replay_steps = tuple(
        tuple(_plain(agent_state) for agent_state in recorded_step)
        for recorded_step in raw["steps"]
    )
    return LocalReplay(
        seed=int(seed),
        opponent=opponent,
        player=player,
        configuration=_plain(environment.configuration),
        steps=replay_steps,
    )
