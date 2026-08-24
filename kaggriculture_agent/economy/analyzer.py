"""Economy intelligence based only on observable market/town state."""

from __future__ import annotations

from ..domain import BASE_PRICES, CROPS, LAND_PRICES, hire_cost
from ..models import AgentSettings, CropOpportunity, EconomyFeatures, GameState, MarketIntent
from .forecast import StatisticalMarketForecaster, average_daily_town_demand, forecast_crop
from .investment import value_next_land
from .selling import forecast_sell
from .snapshot import build_economy_snapshot


def analyze_economy(
    state: GameState,
    settings: AgentSettings | None = None,
    forecaster: StatisticalMarketForecaster | None = None,
) -> EconomyFeatures:
    """Rank crops and emit market proposals; never schedule farm units."""
    settings = settings or AgentSettings()
    snapshot = build_economy_snapshot(state)
    prices = snapshot.prices
    demand = {item: average_daily_town_demand(state, snapshot, item) for item in BASE_PRICES}
    ratios = {
        item: float(prices.get(item, base)) / float(base) for item, base in BASE_PRICES.items()
    }

    price_forecast = {}
    if forecaster is not None:
        forecaster.observe(prices)
        projected = forecaster.forecast_prices(prices, horizon_days=state.remaining_days)
        price_forecast = getattr(projected, "prices", projected)
        if isinstance(price_forecast, dict) and "prices" in price_forecast:
            price_forecast = price_forecast["prices"]

    opportunities: list[CropOpportunity] = []
    for crop, spec in CROPS.items():
        forecast = forecast_crop(state, snapshot, crop)
        feasible = snapshot.remaining_days > forecast.occupied_days
        revenue = forecast.expected_revenue
        profit = revenue - spec.seed_cost
        score = profit / max(1, forecast.occupied_days)
        if not feasible:
            score = float("-inf")
        opportunities.append(
            CropOpportunity(
                crop=crop,
                seed_cost=spec.seed_cost,
                days_to_maturity=forecast.occupied_days,
                expected_units=forecast.expected_units,
                expected_revenue=revenue,
                expected_profit=profit,
                expected_sell_price=forecast.expected_average_price,
                current_market_inventory=forecast.current_inventory,
                projected_market_inventory=forecast.projected_inventory,
                projected_town_consumption=forecast.town_consumption,
                own_supply_assumption=forecast.own_pending_supply,
                opponent_supply_assumption=forecast.opponent_visible_supply,
                yield_days=forecast.yield_days,
                expected_unit_prices=forecast.expected_unit_prices,
                known_town_consumption=forecast.known_town_consumption,
                expected_future_shop_consumption=forecast.expected_future_shop_consumption,
                score=score,
                feasible=feasible,
            )
        )
    opportunities.sort(key=lambda value: (-value.score, value.crop))

    market_intents: list[MarketIntent] = []
    sell_opportunities = []
    for item, raw_count in snapshot.shed.items():
        count = int(raw_count or 0)
        if count <= 0 or item not in BASE_PRICES:
            continue
        sell = forecast_sell(state, snapshot, item, count, settings)
        sell_opportunities.append(sell)
        if sell.recommend_sell:
            market_intents.append(
                MarketIntent(
                    command=("SELL", item, count),
                    priority=(
                        1200.0
                        if snapshot.remaining_days <= 1
                        else 900.0 + sell.immediate_revenue / max(1, count)
                    ),
                    reason=sell.reason,
                )
            )
    market_intents.sort(key=lambda intent: -intent.priority)

    investment_intents: list[MarketIntent] = []
    if snapshot.remaining_days > 1 and snapshot.hour <= 2:
        missing = max(0, settings.target_hands - snapshot.current_hands)
        for offset in range(missing):
            cost = hire_cost(snapshot.hires_today + offset, state.farm_hand_cost_mult)
            investment_intents.append(
                MarketIntent(("HIRE",), 1040.0, float(cost), "quote daily labor")
            )

    land_opportunity = None
    land_index = snapshot.unlocked_land_count - 1
    if snapshot.remaining_days > 12 and 0 <= land_index < len(LAND_PRICES):
        land_cost = LAND_PRICES[land_index]
        best_crop = next(
            (
                opportunity
                for opportunity in opportunities
                if opportunity.feasible and opportunity.expected_profit > 0
            ),
            None,
        )
        if best_crop is not None:
            land_opportunity = value_next_land(best_crop, land_cost, snapshot.market_params)
        if (
            land_opportunity is not None
            and land_opportunity.net_value_after_land > 0
            and snapshot.money >= land_cost + settings.expand_cash_reserve
        ):
            investment_intents.append(
                MarketIntent(
                    ("BUY_LAND",),
                    680.0,
                    float(land_cost),
                    "one-cycle land value is positive; Farm capacity still required",
                )
            )

    return EconomyFeatures(
        crop_opportunities=tuple(opportunities),
        sell_intents=tuple(market_intents),
        sell_opportunities=tuple(sell_opportunities),
        land_opportunity=land_opportunity,
        market_intents=tuple(market_intents),
        investment_intents=tuple(investment_intents),
        demand=demand,
        price_ratios=ratios,
        opponent_visible_supply=snapshot.opponent_visible_supply,
        spendable_cash=max(0.0, snapshot.money - settings.cash_reserve),
        price_forecast=price_forecast,
        seed_priority={
            opportunity.crop: opportunity.score
            for opportunity in opportunities
            if opportunity.feasible
        },
        # Seed quantity combines Economy value with Farm capacity, so Strategy
        # owns that decision rather than Economy.
        buy_intents=(),
    )
