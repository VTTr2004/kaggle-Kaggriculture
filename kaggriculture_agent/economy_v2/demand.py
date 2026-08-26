"""Exact and probabilistic Town-demand forecasts for Economy V2.

Known Town Center and shop consumption is deterministic. Future shop unlock
times are deterministic too, but shop identities are random, so their demand
is reported as low, expected, and high scenarios.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from ..domain import BASE_PRICES, SHOP_DEMAND
from .snapshot import EconomySnapshotV2

MAX_SHOP_INSTANCES = 8


@dataclass(frozen=True)
class TownConsumptionEventV2:
    """One scheduled Town drain at a specific game step."""

    step: int
    source: str
    item: str
    quantity_low: float
    quantity_expected: float
    quantity_high: float


@dataclass(frozen=True)
class TownDemandForecastV2:
    """Town consumption over the half-open interval ``[start_step, end_step)``."""

    item: str
    start_step: int
    end_step: int
    known_center_consumption: float
    known_shop_consumption: float
    next_shop_probabilities: Mapping[str, float]
    future_shop_unlock_steps: tuple[int, ...]
    future_shop_consumption_low: float
    expected_future_shop_consumption: float
    future_shop_consumption_high: float
    total_consumption_low: float
    total_expected_consumption: float
    total_consumption_high: float
    consumption_events: tuple[TownConsumptionEventV2, ...]


def next_shop_probabilities_v2(unlocked_shops: Sequence[str]) -> Mapping[str, float]:
    """Return the official uniform next-shop distribution before the cap.

    The interpreter draws with replacement from the sorted shop names. Existing
    names, including duplicates, therefore do not alter the next draw.
    """
    if len(unlocked_shops) >= MAX_SHOP_INSTANCES or not SHOP_DEMAND:
        return MappingProxyType({})
    probability = 1.0 / len(SHOP_DEMAND)
    return MappingProxyType({shop: probability for shop in sorted(SHOP_DEMAND)})


def _known_shop_units_per_tick(unlocked_shops: Sequence[str], item: str) -> int:
    return sum(SHOP_DEMAND.get(shop, ()).count(item) for shop in unlocked_shops)


def _random_shop_units_per_tick(item: str) -> tuple[float, float, float]:
    quantities = [float(products.count(item)) for products in SHOP_DEMAND.values()]
    if not quantities:
        return 0.0, 0.0, 0.0
    return min(quantities), sum(quantities) / len(quantities), max(quantities)


def _future_shop_unlock_steps(
    snapshot: EconomySnapshotV2,
    end_step: int,
) -> tuple[int, ...]:
    shop_instances = len(snapshot.unlocked_shops)
    unlock_steps: list[int] = []

    # A shop is added after the final step of an eligible day. It is visible
    # and can consume starting at the next step, which is a day boundary.
    for next_step in range(snapshot.step + 1, end_step):
        if shop_instances >= MAX_SHOP_INSTANCES:
            break
        if next_step % snapshot.turns_per_day != 0:
            continue
        next_day = next_step // snapshot.turns_per_day
        if next_day > 0 and next_day % snapshot.town_shop_unlock_interval == 0:
            unlock_steps.append(next_step)
            shop_instances += 1

    return tuple(unlock_steps)


def forecast_town_demand_v2(
    snapshot: EconomySnapshotV2,
    item: str,
    *,
    end_step: int,
) -> TownDemandForecastV2:
    """Forecast Town drain before ``end_step`` without using ML.

    Exact quantities are used for the Town Center and already-open shops.
    Future random shops use the official uniform draw to produce low,
    expectation, and high scenarios.
    """
    if item not in BASE_PRICES:
        raise ValueError(f"unknown market item: {item}")
    if end_step < snapshot.step:
        raise ValueError("end_step must not be before snapshot.step")

    unlock_steps = _future_shop_unlock_steps(snapshot, end_step)
    next_probabilities = next_shop_probabilities_v2(snapshot.unlocked_shops)
    known_shop_units = _known_shop_units_per_tick(snapshot.unlocked_shops, item)
    future_low_per_shop, future_expected_per_shop, future_high_per_shop = (
        _random_shop_units_per_tick(item)
    )

    center_total = 0.0
    known_shop_total = 0.0
    future_low_total = 0.0
    future_expected_total = 0.0
    future_high_total = 0.0
    active_future_shops = 0
    next_unlock_index = 0
    events: list[TownConsumptionEventV2] = []

    for step in range(snapshot.step, end_step):
        while next_unlock_index < len(unlock_steps) and unlock_steps[next_unlock_index] <= step:
            active_future_shops += 1
            next_unlock_index += 1

        if step % snapshot.town_shop_sell_interval == 0:
            if known_shop_units:
                quantity = float(known_shop_units)
                known_shop_total += quantity
                events.append(
                    TownConsumptionEventV2(
                        step=step,
                        source="KNOWN_SHOPS",
                        item=item,
                        quantity_low=quantity,
                        quantity_expected=quantity,
                        quantity_high=quantity,
                    )
                )

            if active_future_shops:
                quantity_low = active_future_shops * future_low_per_shop
                quantity_expected = active_future_shops * future_expected_per_shop
                quantity_high = active_future_shops * future_high_per_shop
                future_low_total += quantity_low
                future_expected_total += quantity_expected
                future_high_total += quantity_high
                if quantity_low or quantity_expected or quantity_high:
                    events.append(
                        TownConsumptionEventV2(
                            step=step,
                            source="FUTURE_SHOPS",
                            item=item,
                            quantity_low=quantity_low,
                            quantity_expected=quantity_expected,
                            quantity_high=quantity_high,
                        )
                    )

        if item != "FERTILIZER" and step % snapshot.town_center_sell_interval == 0:
            center_total += 1.0
            events.append(
                TownConsumptionEventV2(
                    step=step,
                    source="TOWN_CENTER",
                    item=item,
                    quantity_low=1.0,
                    quantity_expected=1.0,
                    quantity_high=1.0,
                )
            )

    total_low = center_total + known_shop_total + future_low_total
    total_expected = center_total + known_shop_total + future_expected_total
    total_high = center_total + known_shop_total + future_high_total
    return TownDemandForecastV2(
        item=item,
        start_step=snapshot.step,
        end_step=end_step,
        known_center_consumption=center_total,
        known_shop_consumption=known_shop_total,
        next_shop_probabilities=next_probabilities,
        future_shop_unlock_steps=unlock_steps,
        future_shop_consumption_low=future_low_total,
        expected_future_shop_consumption=future_expected_total,
        future_shop_consumption_high=future_high_total,
        total_consumption_low=total_low,
        total_expected_consumption=total_expected,
        total_consumption_high=total_high,
        consumption_events=tuple(events),
    )
