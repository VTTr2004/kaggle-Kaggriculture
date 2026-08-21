"""
Kaggriculture Agent - Main Entry Point

Build an AI agent to manage a virtual farm:
- Plant and harvest crops
- Water plants
- Remove weeds
- Trade on the market
- Maximize profit over 30 days (720 turns)
"""
import logging
from pathlib import Path
from typing import Dict, List
from strategy import get_next_action, get_strategy_summary
from utils import get_my_state, get_farmer_pos


# Keep a persistent trace log for local runs and debugging.
TRACE_LOG = Path(__file__).with_name("tracelog.log")
logger = logging.getLogger("kaggriculture")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(TRACE_LOG, encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(handler)
    logger.propagate = False


def agent(obs: Dict, config: Dict = None) -> Dict:
    """
    Main agent function - called every turn.

    Args:
        obs: Game observation containing:
            - player: current player index (0 or 1)
            - day: current day (0-29)
            - farms: list of farm states
            - private: private player data (seeds, shed, etc.)
            - market: market prices

    Returns:
        Action dict with:
            - farmer: list of farmer actions (MOVE, PLANT, WATER, HARVEST, WEED, PASS)
            - hands: list of hand/tool actions
            - market: list of market transactions (BUY_SEED, SELL)
    """
    # Get my current state
    me, private, money = get_my_state(obs)

    # Get farmer position
    farmer_x, farmer_y = get_farmer_pos(me)

    # Get next action from strategy
    farmer_actions, hands_actions, market_actions = get_next_action(
        obs=obs,
        me=me,
        private=private,
        farmer_x=farmer_x,
        farmer_y=farmer_y,
    )

    # Build action response
    action = {
        "farmer": farmer_actions,
        "hands": hands_actions,
        "market": market_actions,
    }

    logger.info(
        "day=%s player=%s farmer=(%s,%s) action=%s",
        obs.get("day", 0), obs.get("player", 0), farmer_x, farmer_y, action,
    )

    # Debug output (can be removed for performance)
    if obs.get("day", 0) % 10 == 0 and farmer_x == 0 and farmer_y == 0:
        summary = get_strategy_summary(obs, me, private)
        print(summary)
        logger.info("strategy_summary=%s", summary)

    return action


def debug_agent(obs: Dict, config: Dict = None) -> Dict:
    """
    Debug version of agent - prints detailed info each turn.
    """
    logger.info("debug_turn_start day=%s", obs.get("day", 0))

    me, private, money = get_my_state(obs)
    logger.info("money=%s seeds=%s shed=%s", money, private.get("seeds", {}), private.get("shed", {}))

    farmer_x, farmer_y = get_farmer_pos(me)
    logger.info("farmer=(%s,%s)", farmer_x, farmer_y)

    tiles = me.get("tiles", [])
    plant_count = sum(
        1 for row in tiles
        for tile in row
        if isinstance(tile, dict) and tile.get("kind") == "PLANT"
    )
    logger.info("plants=%s", plant_count)

    action = agent(obs, config)

    logger.info("debug_action=%s", action)

    return action


# For local testing
if __name__ == "__main__":
    print("Kaggriculture Agent loaded successfully!")
    print("Use run_match.py to test the agent against other agents.")
