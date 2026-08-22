"""Economy intelligence based only on observable market/town state."""

from __future__ import annotations

from collections import Counter

from ..domain import BASE_PRICES, CROPS, LAND_PRICES, SHOP_DEMAND, hire_cost
from ..models import AgentSettings, CropOpportunity, EconomyFeatures, GameState, MarketIntent
from .snapshot import EconomySnapshot, build_economy_snapshot


def _town_demand(snapshot: EconomySnapshot) -> dict[str, int]:
    demand: Counter[str] = Counter({item: 1 for item in BASE_PRICES})
    # Town center buys every product, so every product starts with weight one.
    for shop in snapshot.unlocked_shops:
        demand.update(SHOP_DEMAND.get(str(shop), ()))
    return dict(demand)


def analyze_economy(state: GameState, settings: AgentSettings | None = None) -> EconomyFeatures:
    """Rank crops and emit sell proposals; it never schedules farm units."""
    settings = settings or AgentSettings()
    snapshot = build_economy_snapshot(state)
    prices = snapshot.prices
    demand = _town_demand(snapshot)
    ratios = {
        item: float(prices.get(item, base)) / float(base) for item, base in BASE_PRICES.items()
    }

    opportunities: list[CropOpportunity] = []
    for crop, spec in CROPS.items():
        feasible = snapshot.remaining_days > spec.max_yield_day
        units = spec.unfertilized_yield
        price = float(prices.get(crop, spec.base_price))
        revenue = units * price
        profit = revenue - spec.seed_cost
        demand_bonus = 1.0 + 0.04 * max(0, demand.get(crop, 1) - 1)
        # Profit per occupied tile-day, discounted when the current price is
        # already depressed. This contract can later be produced by economy ML.
        score = (profit / max(1, spec.max_yield_day)) * demand_bonus * ratios[crop]
        if not feasible:
            score = float("-inf")
        opportunities.append(
            CropOpportunity(
                crop=crop,
                seed_cost=spec.seed_cost,
                days_to_maturity=spec.max_yield_day,
                expected_units=units,
                expected_revenue=revenue,
                expected_profit=profit,
                score=score,
                feasible=feasible,
            )
        )
    opportunities.sort(key=lambda value: (-value.score, value.crop))

    market_intents: list[MarketIntent] = []
    for item, raw_count in snapshot.shed.items():
        count = int(raw_count or 0)
        if count <= 0 or item not in BASE_PRICES:
            continue
        ratio = ratios.get(item, 1.0)
        final_day = snapshot.remaining_days <= 1
        shed_pressure = snapshot.shed_usage_ratio >= 0.80
        if final_day or shed_pressure or ratio >= settings.sell_price_floor_ratio:
            market_intents.append(
                MarketIntent(
                    command=("SELL", item, count),
                    priority=1200.0 if final_day else 880.0 + ratio * 100.0,
                    reason=f"liquidate {count} {item} at price ratio {ratio:.2f}",
                )
            )
    market_intents.sort(key=lambda intent: -intent.priority)

    # These are economy quotes. Shared Strategy may reject them when Farm says
    # there is not enough work/capacity to justify the investment.
    investment_intents: list[MarketIntent] = []
    if snapshot.remaining_days > 1 and snapshot.hour <= 2:
        missing = max(0, settings.target_hands - snapshot.current_hands)
        hires_before = snapshot.hires_today
        for offset in range(missing):
            cost = hire_cost(hires_before + offset, state.farm_hand_cost_mult)
            investment_intents.append(
                MarketIntent(("HIRE",), 1040.0, float(cost), "quote daily labor")
            )

    land_index = snapshot.unlocked_land_count - 1
    if snapshot.remaining_days > 12 and 0 <= land_index < len(LAND_PRICES):
        land_cost = LAND_PRICES[land_index]
        if snapshot.money >= land_cost + settings.expand_cash_reserve:
            investment_intents.append(
                MarketIntent(("BUY_LAND",), 680.0, float(land_cost), "quote next quadrant")
            )

    return EconomyFeatures(
        crop_opportunities=tuple(opportunities),
        market_intents=tuple(market_intents),
        investment_intents=tuple(investment_intents),
        demand=demand,
        price_ratios=ratios,
        opponent_visible_supply=snapshot.opponent_visible_supply,
        spendable_cash=max(0.0, snapshot.money - settings.cash_reserve),
    )
