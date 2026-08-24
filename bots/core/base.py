"""Base classes for independent farm and economy policies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from .types import BotAction, MarketAnalysis


class MiniBot(ABC):
    """Common callable contract and observation helpers."""

    def __call__(self, observation: Mapping[str, Any], configuration: Any = None) -> BotAction:
        return self.act(observation, configuration)

    @abstractmethod
    def act(self, observation: Mapping[str, Any], configuration: Any = None) -> BotAction:
        raise NotImplementedError

    @staticmethod
    def step(observation: Mapping[str, Any]) -> int:
        return int(observation.get("step", 0))

    @staticmethod
    def day(observation: Mapping[str, Any]) -> int:
        return int(observation.get("day", 0))

    @classmethod
    def hour(cls, observation: Mapping[str, Any]) -> int:
        return int(observation.get("hour", cls.step(observation) % 24))

    @staticmethod
    def action(
        *,
        farmer: list[Any] | None = None,
        hands: list[list[Any]] | None = None,
        market: list[list[Any]] | None = None,
    ) -> BotAction:
        return {
            "farmer": farmer or ["PASS"],
            "hands": hands or [],
            "market": market or [],
        }


class FarmerBot(MiniBot):
    """Base class for unit control and hiring."""

    def act(self, observation: Mapping[str, Any], configuration: Any = None) -> BotAction:
        farmer, hands = self.build_unit_commands(observation, self.plan_routes(observation))
        return self.action(
            farmer=farmer,
            hands=hands,
            market=self.build_hire_orders(observation),
        )

    @abstractmethod
    def plan_routes(self, observation: Mapping[str, Any]) -> Any:
        raise NotImplementedError

    @abstractmethod
    def build_unit_commands(
        self, observation: Mapping[str, Any], routes: Any
    ) -> tuple[list[Any], list[list[Any]]]:
        raise NotImplementedError

    def build_hire_orders(self, observation: Mapping[str, Any]) -> list[list[Any]]:
        return []


class EconomyBot(MiniBot):
    """Base class for market analysis and market orders."""

    def act(self, observation: Mapping[str, Any], configuration: Any = None) -> BotAction:
        horizon = max(1, int(observation.get("remaining_days", 1) or 1))
        analysis = self.forecast_prices(observation, horizon)
        return self.action(market=self._build_market_orders(observation, analysis))

    @abstractmethod
    def forecast_prices(self, observation: Mapping[str, Any], horizon: int) -> MarketAnalysis:
        raise NotImplementedError

    @abstractmethod
    def _build_market_orders(
        self, observation: Mapping[str, Any], analysis: MarketAnalysis
    ) -> list[list[Any]]:
        raise NotImplementedError
