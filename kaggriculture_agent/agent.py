"""Pure end-to-end observation -> action pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from .economy import StatisticalMarketForecaster, analyze_economy
from .execution import to_kaggle_action
from .farm import analyze_farm
from .features import build_strategic_features
from .fusion import fuse_decisions
from .models import AgentSettings
from .state import build_state
from .strategy import RuleBasedStrategy

DEFAULT_SETTINGS = AgentSettings()
_ECONOMY_FORECASTER = StatisticalMarketForecaster()
_LAST_STEP = -1
_PREVIOUS_SHED: dict[str, int] = {}
_LAST_HARVEST_DAY: int | None = None


def _safe_action(observation: Any) -> dict[str, list[Any]]:
    try:
        farms = observation.get("farms", ()) if isinstance(observation, Mapping) else ()
        player = int(observation.get("player", 0)) if isinstance(observation, Mapping) else 0
        hands = farms[player].get("hands", ()) if farms and player < len(farms) else ()
    except (AttributeError, IndexError, TypeError, ValueError):
        hands = ()
    return {"farmer": ["PASS"], "hands": [["PASS"] for _ in hands], "market": []}


def agent(observation: Any, configuration: Any = None) -> dict[str, list[Any]]:
    """Kaggle entry point. It intentionally has no mutable episode-level state."""
    global _ECONOMY_FORECASTER, _LAST_STEP, _PREVIOUS_SHED, _LAST_HARVEST_DAY
    try:
        state = build_state(observation, configuration)
        if state.step <= _LAST_STEP or state.step == 0:
            _ECONOMY_FORECASTER = StatisticalMarketForecaster()
            _PREVIOUS_SHED = {}
            _LAST_HARVEST_DAY = None
        shed = state.private.get("shed", {}) or {}
        if any(
            int(shed.get(item, 0) or 0) > _PREVIOUS_SHED.get(item, 0)
            for item in shed
        ):
            _LAST_HARVEST_DAY = state.day
        harvested_previous_day = (
            state.hour == 0
            and state.day > 0
            and _LAST_HARVEST_DAY == state.day - 1
        )
        state = replace(state, harvested_previous_day=harvested_previous_day)
        _PREVIOUS_SHED = {
            str(item): int(count or 0) for item, count in shed.items()
        }
        _LAST_STEP = state.step
        farm_features = analyze_farm(state)
        economy_features = analyze_economy(state, DEFAULT_SETTINGS, _ECONOMY_FORECASTER)
        features = build_strategic_features(state, farm_features, economy_features)
        plan = RuleBasedStrategy(DEFAULT_SETTINGS).decide(features)
        return to_kaggle_action(fuse_decisions(state, plan))
    except Exception:
        # A malformed observation should lose one turn, not the whole episode.
        return _safe_action(observation)
