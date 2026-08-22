"""Stable strategy interface for rule -> ML -> RL -> self-play upgrades."""

from __future__ import annotations

from typing import Protocol

from ..models import StrategicFeatures, StrategyPlan


class Strategy(Protocol):
    def decide(self, features: StrategicFeatures) -> StrategyPlan:
        """Return intentions, not raw Kaggle output."""
        ...
