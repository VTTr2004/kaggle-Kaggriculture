"""Economy-owned view of current observable state.

This deliberately contains opponent public supply but never invents access to
the opponent's private shed, seeds, or unit inventories.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass

from ..domain import ANIMALS
from ..models import GameState


@dataclass(frozen=True)
class EconomySnapshot:
    day: int
    hour: int
    remaining_days: int
    money: float
    prices: Mapping[str, float]
    market_inventory: Mapping[str, int]
    shed: Mapping[str, int]
    seeds: Mapping[str, int]
    unlocked_shops: tuple[str, ...]
    current_hands: int
    hires_today: int
    unlocked_land_count: int
    shed_usage_ratio: float
    opponent_money: float
    opponent_crop_counts: Mapping[str, int]
    opponent_visible_supply: Mapping[str, int]


def _opponent_signals(state: GameState) -> tuple[dict[str, int], dict[str, int]]:
    crop_counts: Counter[str] = Counter()
    visible_supply: Counter[str] = Counter()
    for row in state.opponent.get("tiles", ()) or ():
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                crop = str(tile.get("crop", ""))
                if crop:
                    crop_counts[crop] += 1
                    visible_supply[crop] += int(tile.get("yield_units", 0) or 0)
            elif tile.get("animal") in ANIMALS:
                animal = str(tile["animal"])
                product = ANIMALS[animal].product
                visible_supply[product] += int(tile.get("yield_units", 0) or 0)
    return dict(crop_counts), dict(visible_supply)


def build_economy_snapshot(state: GameState) -> EconomySnapshot:
    """Copy only the current information Economy is allowed to reason about."""
    shed = state.private.get("shed", {}) or {}
    crop_counts, visible_supply = _opponent_signals(state)
    return EconomySnapshot(
        day=state.day,
        hour=state.hour,
        remaining_days=state.remaining_days,
        money=state.money,
        prices=state.market.get("prices", {}) or {},
        market_inventory=state.market.get("inventory", {}) or {},
        shed=shed,
        seeds=state.private.get("seeds", {}) or {},
        unlocked_shops=tuple(state.town.get("unlocked_shops", ()) or ()),
        current_hands=len(state.me.get("hands", ()) or ()),
        hires_today=int(state.me.get("hires_today", 0) or 0),
        unlocked_land_count=len(state.unlocked_quadrants),
        shed_usage_ratio=sum(int(value or 0) for value in shed.values()) / state.shed_capacity,
        opponent_money=float(state.opponent.get("money", 0.0) or 0.0),
        opponent_crop_counts=crop_counts,
        opponent_visible_supply=visible_supply,
    )
