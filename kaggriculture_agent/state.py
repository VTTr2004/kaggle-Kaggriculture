"""Observation -> immutable state model."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from .models import GameState


def _get(value: Any, key: str, default: Any) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def build_state(observation: Any, configuration: Any = None) -> GameState:
    """Normalize Kaggle dictionaries/Struct objects behind one stable contract."""
    farms = _get(observation, "farms", ()) or ()
    player = int(_get(observation, "player", 0) or 0)
    if not farms or player < 0 or player >= len(farms):
        raise ValueError("observation does not contain the current player's farm")

    turns_per_day = max(1, int(_get(configuration, "turnsPerDay", 24) or 24))
    episode_steps = max(1, int(_get(configuration, "episodeSteps", 720) or 720))
    board_size = int(_get(configuration, "boardSize", 0) or 0)
    if board_size <= 0:
        board_size = len(_get(farms[player], "tiles", ()) or ()) or 10

    opponent_index = 1 - player if len(farms) == 2 else player
    return GameState(
        player=player,
        step=int(_get(observation, "step", 0) or 0),
        day=int(_get(observation, "day", 0) or 0),
        hour=int(_get(observation, "hour", 0) or 0),
        turns_per_day=turns_per_day,
        total_days=int(math.ceil(episode_steps / turns_per_day)),
        board_size=board_size,
        max_market_orders=max(1, int(_get(configuration, "maxMarketOrdersPerTurn", 10) or 10)),
        shed_capacity=max(1, int(_get(configuration, "shedCapacity", 100) or 100)),
        farm_hand_cost_mult=max(0, int(_get(configuration, "farmHandCostMult", 1) or 0)),
        town_shop_unlock_interval=max(
            1, int(_get(configuration, "townShopUnlockInterval", 3) or 3)
        ),
        town_shop_sell_interval=max(1, int(_get(configuration, "townShopSellInterval", 4) or 4)),
        town_center_sell_interval=max(
            1, int(_get(configuration, "townCenterSellInterval", 24) or 24)
        ),
        farms=farms,
        me=farms[player],
        opponent=farms[opponent_index],
        private=_get(observation, "private", {}) or {},
        market=_get(observation, "market", {}) or {},
        town=_get(observation, "town", {}) or {},
    )
