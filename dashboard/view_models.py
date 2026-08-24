"""Build one explainable turn from a saved local replay."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from kaggriculture_agent.economy import EconomySnapshot, analyze_economy, build_economy_snapshot
from kaggriculture_agent.economy.pricing import PriceBreakdown, price_breakdown
from kaggriculture_agent.execution import to_kaggle_action
from kaggriculture_agent.farm import analyze_farm
from kaggriculture_agent.features import build_strategic_features
from kaggriculture_agent.fusion import fuse_decisions
from kaggriculture_agent.models import (
    AgentSettings,
    EconomyFeatures,
    FarmFeatures,
    FinalDecision,
    GameState,
    StrategicFeatures,
    StrategyPlan,
)
from kaggriculture_agent.state import build_state
from kaggriculture_agent.strategy import RuleBasedStrategy

from .replay import LocalReplay


@dataclass(frozen=True)
class TurnAnalysis:
    turn: int
    state: GameState
    snapshot: EconomySnapshot
    farm: FarmFeatures
    economy: EconomyFeatures
    strategic: StrategicFeatures
    plan: StrategyPlan
    final: FinalDecision
    expected_action: Mapping[str, Any]
    recorded_action: Mapping[str, Any] | None


@dataclass(frozen=True)
class CropScoreBreakdown:
    crop: str
    current_price: float
    current_market_inventory: int
    projected_town_consumption: float
    known_town_consumption: float
    expected_future_shop_consumption: float
    own_supply_assumption: int
    opponent_supply_assumption: int
    projected_market_inventory: float
    yield_days: tuple[int, ...]
    expected_unit_prices: tuple[int, ...]
    expected_units: int
    expected_sell_price: float
    expected_revenue: float
    seed_cost: int
    expected_profit: float
    occupied_days: int
    score: float
    feasible: bool
    price_curve: PriceBreakdown


def analyze_turn(
    replay: LocalReplay,
    turn: int,
    settings: AgentSettings | None = None,
) -> TurnAnalysis:
    """Re-run the same stateless pipeline on one recorded observation."""
    if not 0 <= turn < replay.turn_count:
        raise IndexError(f"turn must be in 0..{replay.turn_count - 1}")

    settings = settings or AgentSettings()
    agent_state = replay.steps[turn][replay.player]
    state = build_state(agent_state["observation"], replay.configuration)
    snapshot = build_economy_snapshot(state)
    farm = analyze_farm(state)
    economy = analyze_economy(state, settings)
    strategic = build_strategic_features(state, farm, economy)
    plan = RuleBasedStrategy(settings).decide(strategic)
    final = fuse_decisions(state, plan)
    # Kaggle stores the action produced from state N on recorded state N + 1.
    recorded_action = None
    if turn + 1 < replay.turn_count:
        recorded_action = replay.steps[turn + 1][replay.player].get("action") or {}
    return TurnAnalysis(
        turn=turn,
        state=state,
        snapshot=snapshot,
        farm=farm,
        economy=economy,
        strategic=strategic,
        plan=plan,
        final=final,
        expected_action=to_kaggle_action(final),
        recorded_action=recorded_action,
    )


def crop_score_breakdown(analysis: TurnAnalysis, crop: str) -> CropScoreBreakdown:
    """Expose every term used by the current rule-based crop score."""
    opportunity = next(
        (item for item in analysis.economy.crop_opportunities if item.crop == crop),
        None,
    )
    if opportunity is None:
        raise KeyError(f"unknown crop: {crop}")

    current_price = float(analysis.snapshot.prices.get(crop, 0.0))
    return CropScoreBreakdown(
        crop=crop,
        current_price=current_price,
        current_market_inventory=opportunity.current_market_inventory,
        projected_town_consumption=opportunity.projected_town_consumption,
        known_town_consumption=opportunity.known_town_consumption,
        expected_future_shop_consumption=(opportunity.expected_future_shop_consumption),
        own_supply_assumption=opportunity.own_supply_assumption,
        opponent_supply_assumption=opportunity.opponent_supply_assumption,
        projected_market_inventory=opportunity.projected_market_inventory,
        yield_days=opportunity.yield_days,
        expected_unit_prices=opportunity.expected_unit_prices,
        expected_units=opportunity.expected_units,
        expected_sell_price=opportunity.expected_sell_price,
        expected_revenue=opportunity.expected_revenue,
        seed_cost=opportunity.seed_cost,
        expected_profit=opportunity.expected_profit,
        occupied_days=opportunity.days_to_maturity,
        score=opportunity.score,
        feasible=opportunity.feasible,
        price_curve=price_breakdown(
            crop,
            opportunity.projected_market_inventory,
            analysis.snapshot.market_params,
        ),
    )
