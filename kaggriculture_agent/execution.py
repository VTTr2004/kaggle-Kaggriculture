"""Serialize a validated decision into the official Kaggle action shape."""

from __future__ import annotations

from typing import Any

from .models import FinalDecision


def to_kaggle_action(decision: FinalDecision) -> dict[str, list[Any]]:
    commands = decision.unit_commands or (("PASS",),)
    return {
        "farmer": list(commands[0]),
        "hands": [list(command) for command in commands[1:]],
        "market": [list(command) for command in decision.market_commands],
    }
