"""Evaluate one agent over a reproducible seed interval."""

from __future__ import annotations

import argparse

from kaggle_environments import make


def seed_range(value: str) -> range:
    try:
        start, stop = (int(part) for part in value.split(":", maxsplit=1))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use START:STOP, for example 100:110") from exc
    if stop <= start:
        raise argparse.ArgumentTypeError("STOP must be greater than START")
    return range(start, stop)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--opponent", default="starter", choices=("pass", "random", "starter"))
    parser.add_argument("--seeds", type=seed_range, default=range(20260820, 20260825))
    parser.add_argument("--steps", type=int, default=720)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    wins = losses = ties = 0
    margins: list[float] = []
    for seed in args.seeds:
        env = make(
            "kaggriculture",
            configuration={"episodeSteps": args.steps, "seed": seed},
            debug=False,
        )
        env.run(["main.py", args.opponent])
        ours, theirs = (float(state.reward or 0) for state in env.steps[-1])
        margin = ours - theirs
        margins.append(margin)
        wins += margin > 0
        losses += margin < 0
        ties += margin == 0
        print(f"seed={seed} ours={ours:.0f} opponent={theirs:.0f} margin={margin:+.0f}")
    count = len(margins)
    print(
        f"games={count} W/L/T={wins}/{losses}/{ties} "
        f"win_rate={wins / max(1, count):.1%} avg_margin={sum(margins) / max(1, count):+.1f}"
    )


if __name__ == "__main__":
    main()
