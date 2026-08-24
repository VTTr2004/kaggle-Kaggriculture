"""Version 1 farmer policy: fixed routes, planting, care and harvesting."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from kaggriculture_agent.strategy.day_one import PLANTER_ROUTES

from ..core.base import FarmerBot
from ..core.helpers import daily_hire_orders, fixed_route_unit_commands


@dataclass(frozen=True)
class FarmerV1Config:
    crop: str = "MELON"
    harvest_after_days: int = 10
    hire_count: int = 3


class FarmerV1(FarmerBot):
    def __init__(self, config: FarmerV1Config | None = None):
        self.config = config or FarmerV1Config()

    def plan_routes(self, observation: Mapping[str, Any]):
        return PLANTER_ROUTES

    def build_unit_commands(self, observation, routes):
        return fixed_route_unit_commands(
            observation,
            crop=self.config.crop,
            routes=routes,
            harvest_after_days=self.config.harvest_after_days,
        )

    def build_hire_orders(self, observation):
        return daily_hire_orders(self.hour(observation), self.config.hire_count)
