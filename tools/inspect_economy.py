"""Inspect Economy's input, analysis and handoff for one real game turn."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Explain Economy's reasoning at one turn of a real local match."
    )
    parser.add_argument("--turn", type=int, default=0, help="Recorded state index, 0..719")
    parser.add_argument("--seed", type=int, default=20260822)
    parser.add_argument("--player", type=int, choices=(0, 1), default=0)
    parser.add_argument("--opponent", choices=("pass", "random", "starter"), default="starter")
    return parser.parse_args()


def _inventory_text(values: object) -> str:
    if not isinstance(values, dict):
        return "none"
    nonzero = [f"{item}={int(count)}" for item, count in values.items() if int(count or 0) > 0]
    return ", ".join(nonzero) if nonzero else "none"


def _print_intents(title: str, intents: tuple[object, ...]) -> None:
    print(f"\n{title}")
    if not intents:
        print("  (none)")
        return
    for intent in intents:
        command = " ".join(str(part) for part in intent.command)
        print(
            f"  {command:<24} priority={intent.priority:7.1f} "
            f"cost={intent.estimated_cost:7.1f}  {intent.reason}"
        )


def main() -> None:
    from kaggle_environments import make

    from kaggriculture_agent.economy import analyze_economy, build_economy_snapshot
    from kaggriculture_agent.farm import analyze_farm
    from kaggriculture_agent.features import build_strategic_features
    from kaggriculture_agent.fusion import fuse_decisions
    from kaggriculture_agent.models import AgentSettings
    from kaggriculture_agent.state import build_state
    from kaggriculture_agent.strategy import RuleBasedStrategy

    args = parse_args()
    if not 0 <= args.turn < 720:
        raise SystemExit("--turn must be between 0 and 719")

    env = make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "seed": args.seed},
        debug=True,
    )
    agents = ["main.py", args.opponent]
    if args.player == 1:
        agents.reverse()
    env.run(agents)

    observation = env.steps[args.turn][args.player].observation
    state = build_state(observation, env.configuration)
    settings = AgentSettings()
    snapshot = build_economy_snapshot(state)
    economy = analyze_economy(state, settings)
    farm = analyze_farm(state)
    strategic = build_strategic_features(state, farm, economy)
    plan = RuleBasedStrategy(settings).decide(strategic)
    final = fuse_decisions(state, plan)

    print("ECONOMY INPUT")
    print(
        f"  seed={args.seed} player={args.player} turn={args.turn} "
        f"day={snapshot.day} hour={snapshot.hour} remaining_days={snapshot.remaining_days}"
    )
    print(
        f"  money={snapshot.money:.0f} spendable={economy.spendable_cash:.0f} "
        f"shed_usage={snapshot.shed_usage_ratio:.0%}"
    )
    print(f"  shed: {_inventory_text(dict(snapshot.shed))}")
    print(f"  seeds: {_inventory_text(dict(snapshot.seeds))}")
    print(
        f"  opponent_money={snapshot.opponent_money:.0f} "
        f"opponent_crops={dict(snapshot.opponent_crop_counts)} "
        f"visible_ready_supply={dict(snapshot.opponent_visible_supply)}"
    )
    print(f"  town_shops={list(snapshot.unlocked_shops)}")

    print("\nCROP RANKING")
    print("  #  crop       current forecast seed days units   profit  profit/day feasible")
    for rank, opportunity in enumerate(economy.crop_opportunities, start=1):
        price = float(snapshot.prices.get(opportunity.crop, 0.0))
        print(
            f"  {rank:<2} {opportunity.crop:<10} {price:>7.0f} "
            f"{opportunity.expected_sell_price:>8.1f} {opportunity.seed_cost:>4} "
            f"{opportunity.days_to_maturity:>4} {opportunity.expected_units:>5} "
            f"{opportunity.expected_profit:>8.0f} {opportunity.score:>11.1f} "
            f"{str(opportunity.feasible):>8}"
        )
    print("  score = forecast profit / occupied tile-days")

    _print_intents("ECONOMY DIRECT MARKET CANDIDATES", economy.market_intents)
    _print_intents("ECONOMY INVESTMENT QUOTES", economy.investment_intents)

    print("\nFARM SIGNALS USED BY SHARED STRATEGY")
    print(
        f"  plants={farm.plant_count} animals={farm.animal_count} "
        f"empty={len(farm.empty_tiles)} urgent_tasks={farm.urgent_count} "
        f"utilization={farm.utilization:.0%}"
    )

    print("\nSHARED STRATEGY RESULT")
    print(f"  selected_crop={plan.selected_crop or 'none'}")
    print(f"  proposed_market={[list(intent.command) for intent in plan.market_intents]}")
    print(f"  accepted_market={[list(command) for command in final.market_commands]}")
    print(
        "\nRead top-to-bottom: input -> ranking -> candidates -> farm signals -> accepted orders."
    )


if __name__ == "__main__":
    main()
