"""Merge both independent intelligence branches into strategic features."""

from __future__ import annotations

from .models import EconomyFeatures, FarmFeatures, GameState, StrategicFeatures


def build_strategic_features(
    state: GameState, farm: FarmFeatures, economy: EconomyFeatures
) -> StrategicFeatures:
    progress = state.day / max(1, state.total_days)
    phase = "early" if progress < 0.34 else "mid" if progress < 0.75 else "late"
    return StrategicFeatures(state=state, farm=farm, economy=economy, phase=phase)
