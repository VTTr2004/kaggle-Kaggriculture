"""Economic quote for one additional official 5x5 land quadrant."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from ..models import CropOpportunity, LandOpportunity
from .selling import quote_sell_order


def value_next_land(
    crop: CropOpportunity,
    land_cost: float,
    market_params: Mapping[str, Mapping[str, Any]],
    new_tiles: int = 25,
) -> LandOpportunity:
    """Value one crop cycle on 25 new tiles, including its own price impact.

    This deliberately does not claim the farm can plant or care for those tiles;
    Shared Strategy still requires Farm utilization/capacity before accepting.
    """
    expected_units = new_tiles * crop.expected_units
    sale = quote_sell_order(
        crop.crop,
        expected_units,
        crop.projected_market_inventory,
        market_params,
    )
    total_seed_cost = float(new_tiles * crop.seed_cost)
    profit_before_land = sale.revenue - total_seed_cost
    net_value = profit_before_land - land_cost
    daily_profit = profit_before_land / max(1, crop.days_to_maturity)
    payback_days = land_cost / daily_profit if daily_profit > 0 else math.inf
    return LandOpportunity(
        crop=crop.crop,
        land_cost=float(land_cost),
        new_tiles=new_tiles,
        seed_cost=total_seed_cost,
        expected_units=expected_units,
        expected_revenue=sale.revenue,
        expected_profit_before_land=profit_before_land,
        net_value_after_land=net_value,
        payback_days=payback_days,
        unit_prices=sale.unit_prices,
    )
