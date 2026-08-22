from __future__ import annotations

from typing import Any


def observation(
    *,
    farmer: tuple[int, int] = (4, 4),
    hands: list[list[int]] | None = None,
    tiles: list[list[Any]] | None = None,
    seeds: dict[str, int] | None = None,
    shed: dict[str, int] | None = None,
    inventories: list[dict[str, int]] | None = None,
    money: float = 3000,
    day: int = 0,
    hour: int = 0,
) -> dict[str, Any]:
    board = tiles or [[None for _ in range(5)] for _ in range(5)]
    hand_positions = hands or []
    inv = inventories or [{} for _ in range(1 + len(hand_positions))]
    return {
        "player": 0,
        "step": day * 24 + hour,
        "day": day,
        "hour": hour,
        "farms": [
            {
                "money": money,
                "farmer": list(farmer),
                "hands": hand_positions,
                "tiles": board,
                "unlocked_quadrants": ["NW"],
                "hires_today": len(hand_positions),
            },
            {
                "money": money,
                "farmer": [4, 4],
                "hands": [],
                "tiles": [[None for _ in range(5)] for _ in range(5)],
                "unlocked_quadrants": ["NW"],
                "hires_today": 0,
            },
        ],
        "private": {"seeds": seeds or {}, "shed": shed or {}, "inventories": inv},
        "market": {
            "inventory": {},
            "prices": {
                "WHEAT": 25,
                "CARROT": 35,
                "TOMATO": 60,
                "STRAWBERRY": 120,
                "MELON": 250,
                "EGG": 50,
                "MILK": 160,
                "WOOL": 200,
                "FERTILIZER": 100,
            },
        },
        "town": {"unlocked_shops": []},
    }
