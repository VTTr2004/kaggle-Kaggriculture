"""Explainable unit-by-unit sell quotes using the official market curve."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..models import AgentSettings, GameState, SellOpportunity
from .forecast import town_consumption_until
from .pricing import market_price
from .snapshot import EconomySnapshot


@dataclass(frozen=True)
class SellOrderQuote:
    item: str
    quantity: int
    starting_inventory: float
    ending_inventory: float
    unit_prices: tuple[int, ...]
    revenue: float


def quote_sell_order(
    item: str,
    quantity: int,
    starting_inventory: int | float,
    market_params: Mapping[str, Mapping[str, Any]] | None = None,
) -> SellOrderQuote:
    """Quote sequential units exactly, including the official $1-floor rule."""
    inventory = float(starting_inventory)
    prices: list[int] = []
    for _ in range(max(0, quantity)):
        price = market_price(item, inventory, market_params)
        prices.append(price)
        # At the floor the interpreter buys the unit but does not add supply.
        if price > 1:
            inventory += 1
    return SellOrderQuote(
        item=item,
        quantity=max(0, quantity),
        starting_inventory=float(starting_inventory),
        ending_inventory=inventory,
        unit_prices=tuple(prices),
        revenue=float(sum(prices)),
    )


def forecast_sell(
    state: GameState,
    snapshot: EconomySnapshot,
    item: str,
    quantity: int,
    settings: AgentSettings,
    hold_days: int = 1,
) -> SellOpportunity:
    """Compare selling now with a transparent one-day hold baseline."""
    current_inventory = float(snapshot.market_inventory.get(item, 10000) or 0)
    immediate = quote_sell_order(item, quantity, current_inventory, snapshot.market_params)
    town_drain = town_consumption_until(state, snapshot, item, hold_days)
    opponent_supply = int(snapshot.opponent_visible_supply.get(item, 0) or 0)
    projected_inventory = current_inventory - town_drain + opponent_supply
    held = quote_sell_order(item, quantity, projected_inventory, snapshot.market_params)

    final_day = snapshot.remaining_days <= 1
    shed_pressure = snapshot.shed_usage_ratio >= 0.80
    liquidity_needed = snapshot.money < settings.cash_reserve
    sell_now = final_day or shed_pressure or liquidity_needed or immediate.revenue >= held.revenue
    if final_day:
        reason = "final-day liquidation: unsold goods score zero"
    elif shed_pressure:
        reason = "sell to prevent shed overflow"
    elif liquidity_needed:
        reason = "sell to restore the configured cash reserve"
    elif immediate.revenue >= held.revenue:
        reason = "sell-now revenue is at least the one-day hold forecast"
    else:
        reason = "hold one day: known/expected town demand may improve the quote"

    return SellOpportunity(
        item=item,
        quantity=quantity,
        immediate_unit_prices=immediate.unit_prices,
        immediate_revenue=immediate.revenue,
        hold_days=hold_days,
        hold_unit_prices=held.unit_prices,
        hold_revenue=held.revenue,
        projected_inventory_after_wait=projected_inventory,
        projected_town_consumption=town_drain,
        opponent_supply_assumption=opponent_supply,
        recommend_sell=sell_now,
        reason=reason,
    )
