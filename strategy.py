"""
Strategy module for Kaggriculture Agent
"""
from typing import List, Tuple, Dict, Optional
from utils import (
    CROPS,
    get_tile_at,
    find_nearest_empty_tile,
    find_crop_to_harvest,
    find_crop_to_water,
    find_weeds,
    get_plant_priority,
    calculate_distance,
    should_plant_crop,
    decide_market_actions,
)


class FarmStrategy:
    def __init__(self, day: int, remaining_days: int, money: int):
        self.day = day
        self.remaining_days = remaining_days
        self.money = money
        self.day_phase = self._get_day_phase(day)

    def _get_day_phase(self, day: int) -> str:
        """Determine phase of the game."""
        if day < 10:
            return "early"
        elif day < 20:
            return "mid"
        else:
            return "late"

    def get_farming_priority(self) -> List[str]:
        """Get priority order for farming actions."""
        if self.day_phase == "early":
            return ["plant", "water", "weed", "harvest"]
        elif self.day_phase == "mid":
            return ["harvest", "water", "plant", "weed"]
        else:
            return ["harvest", "water", "weed", "plant"]

    def should_buy_seeds(self) -> bool:
        """Whether to buy seeds."""
        if self.money < 50:
            return False
        if self.day_phase == "early":
            return True
        if self.day_phase == "mid" and self.money > 300:
            return True
        return False

    def should_expand_farm(self) -> bool:
        """Whether to invest in farm expansion."""
        return self.day_phase == "early" and self.money > 500

    def select_crop_to_plant(self, seeds: Dict) -> Optional[str]:
        """Select best crop based on game phase."""
        if self.day_phase == "early":
            for crop in ["WHEAT", "CORN"]:
                if seeds.get(crop, 0) > 0:
                    return crop
        elif self.day_phase == "mid":
            for crop in ["CORN", "TOMATO"]:
                if seeds.get(crop, 0) > 0:
                    return crop
        else:
            for crop in ["TOMATO", "POTATO"]:
                if seeds.get(crop, 0) > 0:
                    return crop

        for crop, count in seeds.items():
            if count > 0 and crop in CROPS:
                return crop

        return None


def get_next_action(
    obs: Dict,
    me: Dict,
    private: Dict,
    farmer_x: int,
    farmer_y: int,
) -> Tuple[List, List, List]:
    """
    Main strategy function - decides what the agent should do next.

    Returns: (farmer_action, hands_action, market_actions)
    """
    day = obs.get("day", 0)
    remaining_days = 30 - day
    tiles = me.get("tiles", [[None] * 10 for _ in range(10)])
    money = me.get("money", 100)
    seeds = private.get("seeds", {})

    strategy = FarmStrategy(day, remaining_days, money)
    priorities = strategy.get_farming_priority()

    farmer_actions = []
    hands_actions = []
    market_actions = decide_market_actions(private, money, day)

    # Check for weeds first (quick action)
    weeds = find_weeds(tiles)
    if weeds and farmer_x < len(tiles[0]) and farmer_y < len(tiles):
        current_tile = get_tile_at(tiles, farmer_x, farmer_y)
        if isinstance(current_tile, dict) and current_tile.get("kind") == "WEED":
            return ["WEED"], hands_actions, market_actions

    # Check for crops ready to harvest
    harvest_list = find_crop_to_harvest(tiles, day)
    if harvest_list:
        harvest_list.sort(
            key=lambda item: calculate_distance(
                item[0], item[1], farmer_x, farmer_y
            )
        )
        target_x, target_y, _ = harvest_list[0]

        if target_x == farmer_x and target_y == farmer_y:
            return ["HARVEST"], hands_actions, market_actions
        else:
            return move_toward(farmer_x, farmer_y, target_x, target_y)

    # Check for crops needing water
    water_list = find_crop_to_water(tiles, day)
    if water_list:
        water_list.sort(
            key=lambda item: get_plant_priority(item[2], day)
        )
        target_x, target_y, _ = water_list[0]

        if target_x == farmer_x and target_y == farmer_y:
            return ["WATER"], hands_actions, market_actions
        else:
            return move_toward(farmer_x, farmer_y, target_x, target_y)

    # Check for weeds to remove
    if weeds:
        weeds.sort(
            key=lambda pos: calculate_distance(pos[0], pos[1], farmer_x, farmer_y)
        )
        target_x, target_y = weeds[0]

        if target_x == farmer_x and target_y == farmer_y:
            return ["WEED"], hands_actions, market_actions
        else:
            return move_toward(farmer_x, farmer_y, target_x, target_y)

    # Check for empty tiles to plant
    crop_to_plant = strategy.select_crop_to_plant(seeds)
    if crop_to_plant:
        empty_pos = find_nearest_empty_tile(tiles, farmer_x, farmer_y)

        if empty_pos:
            target_x, target_y = empty_pos

            if target_x == farmer_x and target_y == farmer_y:
                hands_actions.append(["PLANT", crop_to_plant])
                return ["PASS"], hands_actions, market_actions
            else:
                return move_toward(farmer_x, farmer_y, target_x, target_y)

    # Check barn for harvested goods to sell
    shed = private.get("shed", {})
    for item, count in shed.items():
        if count > 0 and item in CROPS:
            pass

    # Default: pass or roam
    return ["PASS"], hands_actions, market_actions


def move_toward(
    from_x: int, from_y: int, to_x: int, to_y: int
) -> Tuple[List, List, List]:
    """Generate movement action toward target."""
    dx = to_x - from_x
    dy = to_y - from_y

    if dx != 0:
        action = "RIGHT" if dx > 0 else "LEFT"
    elif dy != 0:
        action = "DOWN" if dy > 0 else "UP"
    else:
        action = "PASS"

    return [action], [], []


def get_strategy_summary(obs: Dict, me: Dict, private: Dict) -> str:
    """Get a summary of current strategy status."""
    day = obs.get("day", 0)
    money = me.get("money", 100)
    tiles = me.get("tiles", [])
    seeds = private.get("seeds", {})
    shed = private.get("shed", {})

    total_plants = sum(
        1 for row in tiles
        for tile in row
        if isinstance(tile, dict) and tile.get("kind") == "PLANT"
    )

    harvest_ready = len(find_crop_to_harvest(tiles, day))
    need_water = len(find_crop_to_water(tiles, day))

    summary = f"""
Day {day} | Money: ${money}
Plants: {total_plants} | Ready: {harvest_ready} | Need water: {need_water}
Seeds: {dict(seeds)} | Shed: {dict(shed)}
    """.strip()

    return summary
