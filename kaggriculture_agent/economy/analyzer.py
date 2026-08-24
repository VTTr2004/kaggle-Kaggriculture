"""Economy intelligence based only on observable market/town state."""

from __future__ import annotations

from collections import Counter

from ..domain import BASE_PRICES, CROPS, SHOP_DEMAND
from ..models import AgentSettings, CropOpportunity, EconomyFeatures, GameState, MarketIntent
from .forecast import StatisticalMarketForecaster


def _town_demand(state: GameState) -> dict[str, int]:
    demand: Counter[str] = Counter({item: 1 for item in BASE_PRICES})
    # Town center buys every product, so every product starts with weight one.
    for shop in state.town.get("unlocked_shops", ()) or ():
        demand.update(SHOP_DEMAND.get(str(shop), ()))
    return dict(demand)


def analyze_economy(
    state: GameState,
    settings: AgentSettings | None = None,
    forecaster: StatisticalMarketForecaster | None = None,
) -> EconomyFeatures:
    """Rank crops and emit sell proposals; it never schedules farm units."""
    settings = settings or AgentSettings()
    prices = state.market.get("prices", {}) or {}
    price_forecast = {}
    if forecaster is not None:
        forecaster.observe(prices)
        projected = forecaster.forecast_prices(prices, horizon_days=state.remaining_days)
        price_forecast = getattr(projected, "prices", projected)
        if isinstance(price_forecast, dict) and "prices" in price_forecast:
            price_forecast = price_forecast["prices"]
    demand = _town_demand(state)
    ratios = {
        item: float(prices.get(item, base)) / float(base) for item, base in BASE_PRICES.items()
    }

    opportunities: list[CropOpportunity] = []
    for crop, spec in CROPS.items():
        feasible = state.remaining_days > spec.max_yield_day
        units = spec.unfertilized_yield
        price = float(prices.get(crop, spec.base_price))
        revenue = units * price
        profit = revenue - spec.seed_cost
        demand_bonus = 1.0 + 0.04 * max(0, demand.get(crop, 1) - 1)
        score = (profit / max(1, spec.max_yield_day)) * demand_bonus * ratios[crop]
        if not feasible:
            score = float("-inf")
        opportunities.append(CropOpportunity(crop, units, revenue, profit, score, feasible))
    opportunities.sort(key=lambda value: (-value.score, value.crop))

    seeds = state.private.get("seeds", {}) or {}
    empty_tiles = sum(1 for row in (state.tiles or ()) for tile in (row or ()) if tile is None)
    buy_intents: list[MarketIntent] = []
    for opportunity in opportunities:
        if not opportunity.feasible or opportunity.expected_profit <= 0:
            continue
        current = int(seeds.get(opportunity.crop, 0) or 0)
        quantity = max(0, min(empty_tiles - current, 6))
        affordable = int(max(0.0, state.money - settings.cash_reserve) // CROPS[opportunity.crop].seed_cost)
        quantity = min(quantity, affordable)
        if quantity > 0:
            buy_intents.append(MarketIntent(
                command=("BUY_SEED", opportunity.crop, quantity),
                priority=700.0 + opportunity.score,
                estimated_cost=float(quantity * CROPS[opportunity.crop].seed_cost),
                reason=f"buy highest-priority seed ({opportunity.crop})",
            ))
        break

    sell_intents: list[MarketIntent] = []
    shed = state.private.get("shed", {}) or {}
    for item, raw_count in shed.items():
        count = int(raw_count or 0)
        if count <= 0 or item not in BASE_PRICES:
            continue
        ratio = ratios.get(item, 1.0)
        final_day = state.remaining_days <= 1
        should_sell = (
            final_day
            or ratio >= settings.sell_price_floor_ratio
        )
        if should_sell:
            sell_intents.append(
                MarketIntent(
                    command=("SELL", item, count),
                    priority=1200.0 if final_day else 880.0 + ratio * 100.0,
                    reason=(
                        f"liquidate {count} {item}"
                        f" (price ratio={ratio:.2f})"
                    ),
                )
            )
    sell_intents.sort(key=lambda intent: -intent.priority)
    return EconomyFeatures(
        crop_opportunities=tuple(opportunities),
        sell_intents=tuple(sell_intents),
        demand=demand,
        price_ratios=ratios,
        price_forecast=price_forecast,
        seed_priority={opportunity.crop: opportunity.score for opportunity in opportunities if opportunity.feasible},
        buy_intents=tuple(buy_intents),
    )
