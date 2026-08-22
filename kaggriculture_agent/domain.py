"""Official Kaggriculture constants used by both intelligence branches."""

from __future__ import annotations

from dataclasses import dataclass


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


CROPS: dict[str, CropSpec] = {
    "WHEAT": CropSpec(10, 25, 2, 4, 0, 6, False, 4),
    "CARROT": CropSpec(20, 35, 2, 3, 0, 4, False, 3),
    "TOMATO": CropSpec(50, 60, 8, 8, 1, 4, True, 4),
    "STRAWBERRY": CropSpec(100, 120, 10, 10, 2, 4, True, 4),
    "MELON": CropSpec(80, 250, 10, 12, 0, 6, False, 6),
}


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

BASE_PRICES = {
    "WHEAT": 25,
    "CARROT": 35,
    "TOMATO": 60,
    "STRAWBERRY": 120,
    "MELON": 250,
    "EGG": 50,
    "MILK": 160,
    "WOOL": 200,
    "FERTILIZER": 100,
}

SHOP_DEMAND: dict[str, tuple[str, ...]] = {
    "BAKERY": ("EGG", "WHEAT"),
    "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
    "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"),
    "YARN_STORE": ("WOOL", "WOOL"),
    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"),
    "PET_CAFE": ("CARROT", "CARROT"),
    "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
    "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY"),
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
