"""Compose a farmer policy and an economy policy."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .base import EconomyBot, FarmerBot
from .types import BotAction


def compose_bots(farmer: FarmerBot, economy: EconomyBot):
    def bot(observation: Mapping[str, Any], configuration: Any = None) -> BotAction:
        farmer_action = farmer(observation, configuration)
        economy_action = economy(observation, configuration)
        return {
            "farmer": farmer_action["farmer"],
            "hands": farmer_action["hands"],
            "market": [*farmer_action["market"], *economy_action["market"]],
        }

    return bot
