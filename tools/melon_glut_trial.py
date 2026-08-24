"""Backward-compatible entry point for the version 1 MELON trial."""

from __future__ import annotations

import json
from pathlib import Path

from bots.core.composer import compose_bots
from bots.economy.economy_v1 import EconomyV1, EconomyV1Config
from bots.farmer.farmer_v1 import FarmerV1
from bots.runner import result_to_dict, run_scenario


def run_trial(
    steps: int = 720,
    seed: int = 20260822,
    sell_days: tuple[int, int] = (20, 20),
) -> dict[str, object]:
    result = run_scenario(
        agents=(
            compose_bots(
                FarmerV1(),
                EconomyV1(EconomyV1Config(sell_day=sell_days[0])),
            ),
            compose_bots(
                FarmerV1(),
                EconomyV1(EconomyV1Config(sell_day=sell_days[1])),
            ),
        ),
        steps=steps,
        seed=seed,
        name=f"melon-v1-{sell_days[0]}-{sell_days[1]}",
    )
    payload = result_to_dict(result)
    Path("replays/melon_glut_trial.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    return payload


if __name__ == "__main__":
    print(json.dumps(run_trial(), indent=2))
