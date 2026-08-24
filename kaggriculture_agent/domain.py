"""Official Kaggriculture constants used by both intelligence branches."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CropSpec:
    seed_cost: int
    base_price: int
    first_yield_day: int
    max_yield_day: int
    interval: int
    max_yield: int
    ongoing: bool
    unfertilized_yield: int

    @property
    def unfertilized_peak_day(self) -> int:
        """Earliest official day that the modeled unfertilized yield is ready."""
        if self.ongoing:
            return self.first_yield_day + (self.unfertilized_yield - 1) * self.interval
        bonus_window_start = (self.max_yield_day + 1) // 2
        return bonus_window_start + max(0, self.unfertilized_yield - 2)


_ECONOMY_DATA = Path(__file__).resolve().parents[1] / "data" / "economy"


def _load_json(name: str):
    with (_ECONOMY_DATA / name).open(encoding="utf-8") as handle:
        return json.load(handle)


_CROP_RULES = _load_json("crop_rules.json")
CROPS: dict[str, CropSpec] = {name: CropSpec(**values) for name, values in _CROP_RULES.items()}


@dataclass(frozen=True)
class AnimalSpec:
    cost: int
    structure: str
    first_yield_day: int
    interval: int
    max_held: int
    product: str


ANIMALS: dict[str, AnimalSpec] = {
    "GOOSE": AnimalSpec(300, "COOP", 4, 1, 4, "EGG"),
    "COW": AnimalSpec(400, "PASTURE", 8, 2, 6, "MILK"),
    "SHEEP": AnimalSpec(500, "PASTURE", 6, 3, 6, "WOOL"),
}

BASE_PRICES: dict[str, int] = _load_json("market_prices.json")
SHOP_DEMAND: dict[str, tuple[str, ...]] = {
    shop: tuple(items) for shop, items in _load_json("shop_demand.json").items()
}

LAND_ORDER = ("NE", "SW", "SE")
LAND_PRICES = (1000, 2000, 4000)
UNIT_OPERATIONS = {
    "NORTH",
    "SOUTH",
    "EAST",
    "WEST",
    "PASS",
    "PICKUP",
    "DROP",
    "PLANT",
    "WATER",
    "HARVEST",
    "FERTILIZE",
    "BUILD_COOP",
    "BUILD_PASTURE",
    "DIG",
    "PLACE",
    "FEED",
    "COLLECT_FERTILIZER",
    "CARE",
}


def hire_cost(number_already_hired: int, multiplier: int = 1) -> int:
    """Return the official 1, 1, 2, 3, 5... daily hire cost."""
    a, b = 1, 1
    for _ in range(max(0, number_already_hired)):
        a, b = b, a + b
    return multiplier * a
