"""Kaggriculture submission agent.

The file is intentionally self-contained: Kaggle submissions only need an
``agent`` function at the repository root.
"""

from typing import Any, Dict, List, Optional, Tuple


CROPS = {
    "WHEAT": {"seed": 10, "days": 4, "value": 25, "yield": 6},
    "CARROT": {"seed": 20, "days": 3, "value": 35, "yield": 4},
    "TOMATO": {"seed": 50, "days": 11, "value": 60, "yield": 4},
    "STRAWBERRY": {"seed": 100, "days": 16, "value": 120, "yield": 4},
    "MELON": {"seed": 80, "days": 10, "value": 250, "yield": 6},
}


def _step(fx: int, fy: int, tx: int, ty: int) -> Optional[str]:
    """Return one legal movement command toward a target."""
    if fx < tx:
        return "EAST"
    if fx > tx:
        return "WEST"
    if fy < ty:
        return "SOUTH"
    if fy > ty:
        return "NORTH"
    return None


def _targets(farm: Dict[str, Any], day: int, crop: str) -> List[Tuple[int, int, str]]:
    tiles = farm.get("tiles", [])
    result: List[Tuple[int, int, str]] = []
    for y, row in enumerate(tiles):
        for x, tile in enumerate(row):
            if isinstance(tile, dict) and tile.get("kind") == "WEED":
                result.append((x, y, "weed"))
                continue
            if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                if tile.get("yield_units", 0) > 0:
                    result.append((x, y, "harvest"))
                elif not tile.get("watered_today", False):
                    result.append((x, y, "water"))
            elif tile is None:
                result.append((x, y, "plant"))
    return result


def agent(obs: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, List]:
    farms = obs.get("farms") or []
    player = int(obs.get("player", 0))
    if player >= len(farms):
        return {"farmer": ["PASS"], "hands": [], "market": []}

    farm = farms[player]
    private = obs.get("private") or {}
    day = int(obs.get("day", 0))
    hour = int(obs.get("hour", 0))
    money = float(farm.get("money", 0))
    seeds = private.get("seeds") or {}
    shed = private.get("shed") or {}
    prices = (obs.get("market") or {}).get("prices") or {}
    config = config or {}
    fx, fy = (farm.get("farmer") or [0, 0])[:2]

    # Sell harvested goods when the town price is at least the base price.
    market: List[List[Any]] = []
    for item, amount in shed.items():
        sell_threshold = float(config.get("sell_threshold", CROPS[item]["value"]))
        if amount and item in CROPS and prices.get(item, CROPS[item]["value"]) >= sell_threshold:
            market.append(["SELL", item, int(amount)])

    # Melon has the best one-time return. Near the end, use fast crops so the
    # farmer does not spend money on a crop that cannot mature this season.
    remaining = 30 - day
    preferred_crop = config.get("preferred_crop", "MELON")
    late_crop = config.get("late_crop", "CARROT")
    if remaining >= int(config.get("preferred_min_days", 12)):
        crop = preferred_crop if preferred_crop in CROPS else "MELON"
    elif remaining >= 5:
        crop = late_crop if late_crop in CROPS else "CARROT"
    else:
        crop = "WHEAT"
    seed_cost = CROPS[crop]["seed"]
    reserve = float(config.get("reserve_money", 20))
    if seeds.get(crop, 0) == 0 and remaining >= CROPS[crop]["days"] and money >= seed_cost + reserve:
        market.append(["BUY_SEED", crop, 1])

    tile = (farm.get("tiles") or [[None]])[fy][fx]
    if isinstance(tile, dict) and tile.get("kind") == "WEED":
        return {"farmer": ["WEED"], "hands": [], "market": market}
    if isinstance(tile, dict) and tile.get("kind") == "PLANT":
        if tile.get("yield_units", 0) > 0:
            return {"farmer": ["HARVEST"], "hands": [], "market": market}
        if not tile.get("watered_today", False):
            return {"farmer": ["WATER"], "hands": [], "market": market}

    have_seed = seeds.get(crop, 0) > 0
    candidates = _targets(farm, day, crop)
    # Harvest/water/weed before planting; nearest target reduces travel time.
    rank = {"harvest": 0, "water": 1, "weed": 2, "plant": 3}
    candidates = [t for t in candidates if t[2] != "plant" or have_seed]
    candidates.sort(key=lambda t: (rank[t[2]], abs(t[0] - fx) + abs(t[1] - fy)))
    if candidates:
        tx, ty, purpose = candidates[0]
        if (move := _step(fx, fy, tx, ty)):
            return {"farmer": [move], "hands": [], "market": market}
        command = {"harvest": "HARVEST", "water": "WATER", "weed": "WEED"}.get(purpose)
        if command:
            return {"farmer": [command], "hands": [], "market": market}
        if purpose == "plant":
            return {"farmer": ["PLANT", crop], "hands": [], "market": market}

    return {"farmer": ["PASS"], "hands": [], "market": market}


if __name__ == "__main__":
    print("Kaggriculture agent ready")
