"""
Utilities for Kaggriculture Agent
"""
from typing import Optional, Dict, List, Any, Tuple


# Crop definitions
CROPS = {
    "WHEAT": {"first_yield_day": 2, "base_price": 5, "seed_cost": 10},
    "CORN": {"first_yield_day": 3, "base_price": 10, "seed_cost": 25},
    "TOMATO": {"first_yield_day": 4, "base_price": 20, "seed_cost": 50},
    "POTATO": {"first_yield_day": 5, "base_price": 40, "seed_cost": 80},
}

ANIMALS = {
    "CHICKEN": {"buy_price": 50, "product": "EGGS", "product_price": 10},
    "COW": {"buy_price": 200, "product": "MILK", "product_price": 50},
}

MARKET_ITEMS = ["WHEAT", "CORN", "TOMATO", "POTATO", "EGGS", "MILK", "ANIMAL_FEED"]


def get_player_state(obs: Dict, player_idx: int) -> Dict:
    """Get state for a specific player."""
    farms = obs.get("farms", [])
    if player_idx >= len(farms):
        return {}
    return farms[player_idx]


def get_my_state(obs: Dict) -> Tuple[Dict, Dict, int]:
    """Get my farm state, private info, and money."""
    player = obs.get("player", 0)
    me = get_player_state(obs, player)
    private = obs.get("private", {})
    money = me.get("money", 100)
    return me, private, money


def get_my_tiles(me: Dict) -> List[List]:
    """Get player's tiles grid."""
    return me.get("tiles", [[None] * 10 for _ in range(10)])


def get_farmer_pos(me: Dict) -> Tuple[int, int]:
    """Get farmer position (x, y)."""
    farmer = me.get("farmer", [0, 0])
    return farmer[0], farmer[1]


def get_tile_at(tiles: List[List], x: int, y: int) -> Optional[Dict]:
    """Get tile content at position."""
    if 0 <= y < len(tiles) and 0 <= x < len(tiles[0]):
        return tiles[y][x]
    return None


def find_nearest_empty_tile(
    tiles: List[List], start_x: int, start_y: int
) -> Optional[Tuple[int, int]]:
    """Find nearest empty tile to plant."""
    best = None
    best_dist = float("inf")

    for y in range(len(tiles)):
        for x in range(len(tiles[0])):
            tile = tiles[y][x]
            if tile is None:
                dist = abs(x - start_x) + abs(y - start_y)
                if dist < best_dist:
                    best_dist = dist
                    best = (x, y)

    return best


def find_crop_to_harvest(
    tiles: List[List], day: int
) -> List[Tuple[int, int, Dict]]:
    """Find all crops ready to harvest."""
    ready = []

    for y in range(len(tiles)):
        for x in range(len(tiles[0])):
            tile = tiles[y][x]
            if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                crop_type = tile.get("type", "WHEAT")
                crop_info = CROPS.get(crop_type, CROPS["WHEAT"])
                age = day - tile.get("planted_day", 0)

                if age >= crop_info["first_yield_day"]:
                    ready.append((x, y, tile))

    return ready


def find_crop_to_water(
    tiles: List[List], day: int
) -> List[Tuple[int, int, Dict]]:
    """Find crops that need watering."""
    need_water = []

    for y in range(len(tiles)):
        for x in range(len(tiles[0])):
            tile = tiles[y][x]
            if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                if not tile.get("watered_today", False):
                    need_water.append((x, y, tile))

    return need_water


def find_weeds(tiles: List[List]) -> List[Tuple[int, int]]:
    """Find tiles with weeds."""
    weeds = []

    for y in range(len(tiles)):
        for x in range(len(tiles[0])):
            tile = tiles[y][x]
            if isinstance(tile, dict) and tile.get("kind") == "WEED":
                weeds.append((x, y))

    return weeds


def get_plant_yield(tile: Dict) -> int:
    """Calculate yield from a plant."""
    plant_type = tile.get("type", "WHEAT")
    crop_info = CROPS.get(plant_type, CROPS["WHEAT"])
    watered = tile.get("watered_today", False)
    base_yield = crop_info["base_price"]

    return base_yield * (2 if watered else 1)


def should_plant_crop(
    money: int, seeds: Dict, day: int, remaining_days: int
) -> Optional[str]:
    """Decide which crop to plant based on profitability."""
    remaining_days = remaining_days or (30 - day)

    best_crop = None
    best_score = -float("inf")

    for crop_name, crop_info in CROPS.items():
        seed_count = seeds.get(crop_name, 0)
        if seed_count > 0:
            days_needed = crop_info["first_yield_day"]
            if days_needed <= remaining_days:
                profit = crop_info["base_price"] * 2 - crop_info["seed_cost"]
                score = profit / days_needed
                if score > best_score:
                    best_score = score
                    best_crop = crop_name

    if best_crop is None and money >= 100:
        for crop_name, crop_info in CROPS.items():
            if crop_info["seed_cost"] <= money:
                days_needed = crop_info["first_yield_day"]
                if days_needed <= remaining_days:
                    profit = crop_info["base_price"] * 2 - crop_info["seed_cost"]
                    score = profit / days_needed
                    if score > best_score:
                        best_score = score
                        best_crop = crop_name

    return best_crop


def get_market_prices(obs: Dict) -> Dict[str, int]:
    """Get current market prices."""
    return obs.get("market", {})


def calculate_distance(x1: int, y1: int, x2: int, y2: int) -> int:
    """Manhattan distance between two points."""
    return abs(x2 - x1) + abs(y2 - y1)


def get_best_plant_position(
    tiles: List[List], start_x: int, start_y: int
) -> Tuple[int, int]:
    """Get the best position to plant (nearest empty)."""
    empty = find_nearest_empty_tile(tiles, start_x, start_y)
    if empty:
        return empty

    for y in range(len(tiles)):
        for x in range(len(tiles[0])):
            tile = tiles[y][x]
            if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                crop_type = tile.get("type", "WHEAT")
                crop_info = CROPS.get(crop_type, CROPS["WHEAT"])
                age = obs.get("day", 0) - tile.get("planted_day", 0)
                if age >= crop_info["first_yield_day"]:
                    return (x, y)

    return (start_x, start_y)


def get_plant_priority(tile: Dict, day: int) -> float:
    """Priority score for plant care (higher = more urgent)."""
    if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
        return -1

    plant_type = tile.get("type", "WHEAT")
    crop_info = CROPS.get(plant_type, CROPS["WHEAT"])
    age = day - tile.get("planted_day", 0)
    yield_day = crop_info["first_yield_day"]

    if age >= yield_day:
        return 1000

    if not tile.get("watered_today", False):
        return 500

    return 0


def decide_market_actions(
    private: Dict, money: int, day: int
) -> List[List]:
    """Decide what to buy/sell on market."""
    actions = []
    shed = private.get("shed", {})
    seeds = private.get("seeds", {})

    for crop_name, crop_info in CROPS.items():
        in_shed = shed.get(crop_name, 0)
        if in_shed > 0:
            actions.append(["SELL", crop_name, in_shed])

    remaining_days = 30 - day
    for crop_name, crop_info in CROPS.items():
        seed_count = seeds.get(crop_name, 0)
        if seed_count == 0 and money >= crop_info["seed_cost"]:
            if crop_info["first_yield_day"] <= remaining_days:
                actions.append(["BUY_SEED", crop_name, 1])

    if money > 500 and seeds.get("ANIMAL_FEED", 0) < 2:
        if money >= 20:
            actions.append(["BUY_SEED", "ANIMAL_FEED", 1])

    return actions
