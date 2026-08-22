"""Pure end-to-end observation -> action pipeline."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .economy import analyze_economy
from .execution import to_kaggle_action
from .farm import analyze_farm
from .features import build_strategic_features
from .fusion import fuse_decisions
from .models import AgentSettings
from .state import build_state
from .strategy import RuleBasedStrategy

DEFAULT_SETTINGS = AgentSettings()


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
    try:
        state = build_state(observation, configuration)
        farm_features = analyze_farm(state)
        economy_features = analyze_economy(state, DEFAULT_SETTINGS)
        features = build_strategic_features(state, farm_features, economy_features)
        plan = RuleBasedStrategy(DEFAULT_SETTINGS).decide(features)
        return to_kaggle_action(fuse_decisions(state, plan))
    except Exception:
        # A malformed observation should lose one turn, not the whole episode.
        return _safe_action(observation)
