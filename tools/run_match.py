"""Run one deterministic local match and optionally save a replay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from kaggle_environments import make


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--opponent", default="starter", choices=("pass", "random", "starter"))
    parser.add_argument("--seed", type=int, default=20260822)
    parser.add_argument("--steps", type=int, default=720)
    parser.add_argument("--player", type=int, choices=(0, 1), default=0)
    parser.add_argument("--replay", type=Path, default=Path("replays/latest.json"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configuration = {"episodeSteps": args.steps, "seed": args.seed}
    env = make("kaggriculture", configuration=configuration, debug=True)
    agents = ["main.py", args.opponent]
    if args.player == 1:
        agents.reverse()
    env.run(agents)

    final = env.steps[-1]
    rewards = [state.reward for state in final]
    statuses = [state.status for state in final]
    print(
        f"seed={args.seed} recorded_states={len(env.steps)} rewards={rewards} statuses={statuses}"
    )

    if args.replay:
        args.replay.parent.mkdir(parents=True, exist_ok=True)
        args.replay.write_text(json.dumps(env.toJSON()), encoding="utf-8")
        print(f"replay={args.replay}")


if __name__ == "__main__":
    main()
