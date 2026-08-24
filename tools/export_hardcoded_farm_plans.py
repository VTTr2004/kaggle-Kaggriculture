"""Export deterministic 5/10-day farm plans using static crop prices."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from kaggriculture_agent.farm.planner import (
    HARDCODED_BASE_PRICES,
    build_hardcoded_farm_plans,
    farm_plan_to_dict,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--current-day", type=int, default=1)
    parser.add_argument("--free-tiles", type=int, default=50)
    parser.add_argument("--output", type=Path, default=Path("artifacts/farm_plans_hardcoded.json"))
    args = parser.parse_args()

    plans = build_hardcoded_farm_plans(
        current_day=args.current_day,
        free_tiles=args.free_tiles,
        horizons=(5, 10),
    )
    payload = {
        "price_source": "HARDCODED_BASE_PRICES",
        "prices": HARDCODED_BASE_PRICES,
        "current_day": args.current_day,
        "free_tiles": args.free_tiles,
        "plans": {str(horizon): farm_plan_to_dict(plan) for horizon, plan in plans.items()},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    for horizon, plan in plans.items():
        print(
            f"horizon={horizon} crop={dict(plan.seed_targets)} "
            f"profit={plan.projected_profit:.2f} revenue={plan.projected_revenue:.2f}"
        )
    print(f"saved={args.output}")


if __name__ == "__main__":
    main()
