"""Immutable observable inputs for Economy V2.

This module only classifies facts visible in the current state. Forecasting
future production, prices, and opponent behavior belongs to later V2 modules.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from ..domain import ANIMALS, BASE_PRICES, CROPS
from ..models import GameState


def _integer_mapping(values: Mapping[str, Any]) -> Mapping[str, int]:
    return MappingProxyType({str(key): int(value or 0) for key, value in values.items()})


def _float_mapping(values: Mapping[str, Any]) -> Mapping[str, float]:
    return MappingProxyType({str(key): float(value or 0.0) for key, value in values.items()})


def _nested_mapping(
    values: Mapping[str, Mapping[str, Any]],
) -> Mapping[str, Mapping[str, Any]]:
    return MappingProxyType(
        {
            str(key): MappingProxyType(dict(value))
            for key, value in values.items()
            if isinstance(value, Mapping)
        }
    )


def _product_supply(values: Mapping[str, Any]) -> Mapping[str, int]:
    return MappingProxyType(
        {
            str(item): int(count)
            for item, count in values.items()
            if item in BASE_PRICES and int(count or 0) > 0
        }
    )


def _carried_supply(inventories: tuple[Mapping[str, int], ...]) -> Mapping[str, int]:
    carried: Counter[str] = Counter()
    for inventory in inventories:
        for item, count in inventory.items():
            if item in BASE_PRICES and int(count or 0) > 0:
                carried[str(item)] += int(count)
    return MappingProxyType(dict(carried))


def _public_farm_signals(
    farm: Mapping[str, Any],
) -> tuple[Mapping[str, int], Mapping[str, int], Mapping[str, int]]:
    crop_counts: Counter[str] = Counter()
    animal_counts: Counter[str] = Counter()
    ready_supply: Counter[str] = Counter()

    for row in farm.get("tiles", ()) or ():
        for tile in row:
            if not isinstance(tile, Mapping):
                continue
            if tile.get("kind") == "PLANT" and tile.get("crop") in CROPS:
                crop = str(tile["crop"])
                crop_counts[crop] += 1
                ready_supply[crop] += max(0, int(tile.get("yield_units", 0) or 0))
                continue
            if tile.get("animal") in ANIMALS:
                animal = str(tile["animal"])
                animal_counts[animal] += 1
                product = ANIMALS[animal].product
                ready_supply[product] += max(0, int(tile.get("yield_units", 0) or 0))

    return (
        MappingProxyType(dict(crop_counts)),
        MappingProxyType(dict(animal_counts)),
        MappingProxyType({item: count for item, count in ready_supply.items() if count > 0}),
    )


@dataclass(frozen=True)
class EconomySnapshotV2:
    """Economy-owned facts copied from one normalized game state."""

    step: int
    day: int
    hour: int
    episode_steps: int
    remaining_turns: int
    remaining_days: int
    money: float
    opponent_money: float
    prices: Mapping[str, float]
    market_inventory: Mapping[str, int]
    market_params: Mapping[str, Mapping[str, Any]]
    shed: Mapping[str, int]
    seeds: Mapping[str, int]
    unit_inventories: tuple[Mapping[str, int], ...]
    shed_usage: int
    shed_capacity: int
    shed_free_capacity: int
    unlocked_shops: tuple[str, ...]
    own_hands: int
    own_hires_today: int
    own_unlocked_land_count: int
    opponent_hands: int
    opponent_hires_today: int
    opponent_unlocked_land_count: int
    own_shed_supply: Mapping[str, int]
    own_carried_supply: Mapping[str, int]
    own_ready_supply: Mapping[str, int]
    own_crop_counts: Mapping[str, int]
    own_animal_counts: Mapping[str, int]
    opponent_ready_supply: Mapping[str, int]
    opponent_crop_counts: Mapping[str, int]
    opponent_animal_counts: Mapping[str, int]


def build_economy_snapshot_v2(state: GameState) -> EconomySnapshotV2:
    """Build V2's immutable snapshot without reading opponent private data."""
    raw_shed = state.private.get("shed", {}) or {}
    raw_seeds = state.private.get("seeds", {}) or {}
    unit_inventories = tuple(_integer_mapping(inventory) for inventory in state.inventories)
    shed = _integer_mapping(raw_shed)
    shed_usage = sum(max(0, count) for count in shed.values())
    own_crop_counts, own_animal_counts, own_ready_supply = _public_farm_signals(state.me)
    opponent_crop_counts, opponent_animal_counts, opponent_ready_supply = _public_farm_signals(
        state.opponent
    )

    return EconomySnapshotV2(
        step=state.step,
        day=state.day,
        hour=state.hour,
        episode_steps=state.episode_steps,
        remaining_turns=state.remaining_turns,
        remaining_days=state.remaining_days,
        money=state.money,
        opponent_money=float(state.opponent.get("money", 0.0) or 0.0),
        prices=_float_mapping(state.market.get("prices", {}) or {}),
        market_inventory=_integer_mapping(state.market.get("inventory", {}) or {}),
        market_params=_nested_mapping(state.market.get("params", {}) or {}),
        shed=shed,
        seeds=_integer_mapping(raw_seeds),
        unit_inventories=unit_inventories,
        shed_usage=shed_usage,
        shed_capacity=state.shed_capacity,
        shed_free_capacity=max(0, state.shed_capacity - shed_usage),
        unlocked_shops=tuple(str(shop) for shop in state.town.get("unlocked_shops", ()) or ()),
        own_hands=len(state.me.get("hands", ()) or ()),
        own_hires_today=int(state.me.get("hires_today", 0) or 0),
        own_unlocked_land_count=len(state.unlocked_quadrants),
        opponent_hands=len(state.opponent.get("hands", ()) or ()),
        opponent_hires_today=int(state.opponent.get("hires_today", 0) or 0),
        opponent_unlocked_land_count=len(
            state.opponent.get("unlocked_quadrants", ("NW",)) or ("NW",)
        ),
        own_shed_supply=_product_supply(raw_shed),
        own_carried_supply=_carried_supply(unit_inventories),
        own_ready_supply=own_ready_supply,
        own_crop_counts=own_crop_counts,
        own_animal_counts=own_animal_counts,
        opponent_ready_supply=opponent_ready_supply,
        opponent_crop_counts=opponent_crop_counts,
        opponent_animal_counts=opponent_animal_counts,
    )
