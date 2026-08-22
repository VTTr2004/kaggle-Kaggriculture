"""Economy intelligence based only on observable market/town state."""

from __future__ import annotations

from collections import Counter

from ..domain import BASE_PRICES, CROPS, SHOP_DEMAND
from ..models import AgentSettings, CropOpportunity, EconomyFeatures, GameState, MarketIntent


def _town_demand(state: GameState) -> dict[str, int]:
    demand: Counter[str] = Counter({item: 1 for item in BASE_PRICES})
    # Town center buys every product, so every product starts with weight one.
    for shop in state.town.get("unlocked_shops", ()) or ():
        demand.update(SHOP_DEMAND.get(str(shop), ()))
    return dict(demand)


def analyze_economy(state: GameState, settings: AgentSettings | None = None) -> EconomyFeatures:
    """Rank crops and emit sell proposals; it never schedules farm units."""
    settings = settings or AgentSettings()
    prices = state.market.get("prices", {}) or {}
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
        # Profit per occupied tile-day, discounted when the current price is
        # already depressed. This contract can later be produced by economy ML.
        score = (profit / max(1, spec.max_yield_day)) * demand_bonus * ratios[crop]
        if not feasible:
            score = float("-inf")
        opportunities.append(CropOpportunity(crop, units, revenue, profit, score, feasible))
    opportunities.sort(key=lambda value: (-value.score, value.crop))

    sell_intents: list[MarketIntent] = []
    shed = state.private.get("shed", {}) or {}
    for item, raw_count in shed.items():
        count = int(raw_count or 0)
        if count <= 0 or item not in BASE_PRICES:
            continue
        ratio = ratios.get(item, 1.0)
        final_day = state.remaining_days <= 1
        if final_day or ratio >= settings.sell_price_floor_ratio:
            sell_intents.append(
                MarketIntent(
                    command=("SELL", item, count),
                    priority=1200.0 if final_day else 880.0 + ratio * 100.0,
                    reason=f"liquidate {count} {item} at price ratio {ratio:.2f}",
                )
            )
    sell_intents.sort(key=lambda intent: -intent.priority)
    return EconomyFeatures(
        crop_opportunities=tuple(opportunities),
        sell_intents=tuple(sell_intents),
        demand=demand,
        price_ratios=ratios,
    )
