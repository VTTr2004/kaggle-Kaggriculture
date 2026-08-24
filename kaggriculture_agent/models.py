"""Contracts shared by state, intelligence, strategy, fusion and execution."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

Position = tuple[int, int]
Command = tuple[Any, ...]


@dataclass(frozen=True)
class AgentSettings:
    target_hands: int = 4
    seed_buffer_per_unit: int = 2
    max_plants_per_unit: int = 5
    cash_reserve: float = 250.0
    expand_cash_reserve: float = 1800.0
    sell_price_floor_ratio: float = 0.35


@dataclass(frozen=True)
class GameState:
    player: int
    step: int
    day: int
    hour: int
    turns_per_day: int
    total_days: int
    board_size: int
    max_market_orders: int
    shed_capacity: int
    farm_hand_cost_mult: int
    town_shop_unlock_interval: int
    town_shop_sell_interval: int
    town_center_sell_interval: int
    farms: Sequence[Mapping[str, Any]]
    me: Mapping[str, Any]
    opponent: Mapping[str, Any]
    private: Mapping[str, Any]
    market: Mapping[str, Any]
    town: Mapping[str, Any]
    harvested_previous_day: bool = False

    @property
    def money(self) -> float:
        return float(self.me.get("money", 0.0))

    @property
    def remaining_days(self) -> int:
        return max(0, self.total_days - self.day)

    @property
    def tiles(self) -> Sequence[Sequence[Any]]:
        return self.me.get("tiles", ()) or ()

    @property
    def unit_positions(self) -> tuple[Position, ...]:
        farmer = self.me.get("farmer", (0, 0)) or (0, 0)
        hands = self.me.get("hands", ()) or ()
        return ((int(farmer[0]), int(farmer[1])),) + tuple(
            (int(pos[0]), int(pos[1])) for pos in hands
        )

    @property
    def inventories(self) -> tuple[Mapping[str, int], ...]:
        values = self.private.get("inventories", ()) or ()
        result = tuple(value or {} for value in values)
        missing = len(self.unit_positions) - len(result)
        return result + tuple({} for _ in range(max(0, missing)))

    @property
    def unlocked_quadrants(self) -> tuple[str, ...]:
        return tuple(self.me.get("unlocked_quadrants", ("NW",)) or ("NW",))


@dataclass(frozen=True)
class FarmTask:
    target: Position
    command: Command
    priority: float
    category: str
    reason: str
    required_item: str | None = None


@dataclass(frozen=True)
class FarmFeatures:
    tasks: tuple[FarmTask, ...]
    empty_tiles: tuple[Position, ...]
    plant_count: int
    animal_count: int
    weed_count: int
    urgent_count: int
    unlocked_tile_count: int
    utilization: float = 0.0


@dataclass(frozen=True)
class CropOpportunity:
    crop: str
    seed_cost: int
    days_to_maturity: int
    expected_units: int
    expected_revenue: float
    expected_profit: float
    expected_sell_price: float
    current_market_inventory: int
    projected_market_inventory: int
    projected_town_consumption: int
    own_supply_assumption: int
    opponent_supply_assumption: int
    yield_days: tuple[int, ...]
    expected_unit_prices: tuple[int, ...]
    known_town_consumption: float
    expected_future_shop_consumption: float
    score: float
    feasible: bool


@dataclass(frozen=True)
class SellOpportunity:
    item: str
    quantity: int
    immediate_unit_prices: tuple[int, ...]
    immediate_revenue: float
    hold_days: int
    hold_unit_prices: tuple[int, ...]
    hold_revenue: float
    projected_inventory_after_wait: float
    projected_town_consumption: float
    opponent_supply_assumption: int
    recommend_sell: bool
    reason: str


@dataclass(frozen=True)
class LandOpportunity:
    crop: str
    land_cost: float
    new_tiles: int
    seed_cost: float
    expected_units: int
    expected_revenue: float
    expected_profit_before_land: float
    net_value_after_land: float
    payback_days: float
    unit_prices: tuple[int, ...]


@dataclass(frozen=True)
class MarketIntent:
    command: Command
    priority: float
    estimated_cost: float = 0.0
    reason: str = ""


@dataclass(frozen=True)
class EconomyFeatures:
    crop_opportunities: tuple[CropOpportunity, ...]
    sell_intents: tuple[MarketIntent, ...]
    demand: Mapping[str, float]
    price_ratios: Mapping[str, float]
    sell_opportunities: tuple[SellOpportunity, ...] = field(default_factory=tuple)
    land_opportunity: LandOpportunity | None = None
    market_intents: tuple[MarketIntent, ...] = field(default_factory=tuple)
    investment_intents: tuple[MarketIntent, ...] = field(default_factory=tuple)
    opponent_visible_supply: Mapping[str, int] = field(default_factory=dict)
    spendable_cash: float = 0.0
    price_forecast: Mapping[str, Sequence[float]] = field(default_factory=dict)
    seed_priority: Mapping[str, float] = field(default_factory=dict)
    buy_intents: tuple[MarketIntent, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class StrategicFeatures:
    state: GameState
    farm: FarmFeatures
    economy: EconomyFeatures
    phase: str


@dataclass(frozen=True)
class UnitIntent:
    unit_index: int
    command: Command
    target: Position | None
    priority: float
    reason: str


@dataclass(frozen=True)
class StrategyPlan:
    selected_crop: str | None
    unit_intents: tuple[UnitIntent, ...]
    market_intents: tuple[MarketIntent, ...]
    notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FinalDecision:
    unit_commands: tuple[Command, ...]
    market_commands: tuple[Command, ...]
