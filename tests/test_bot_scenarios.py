from __future__ import annotations

from bots.core.base import EconomyBot, FarmerBot, MiniBot
from bots.core.composer import compose_bots
from bots.economy.economy_v1 import EconomyV1, EconomyV1Config
from bots.farmer.farmer_v1 import FarmerV1, FarmerV1Config
from bots.runner import run_scenario


def test_melon_v1_only_returns_farm_actions():
    bot = FarmerV1(FarmerV1Config())

    action = bot(
        {
            "step": 0,
            "day": 0,
            "hour": 0,
            "player": 0,
            "farms": [{"money": 3000, "farmer": [4, 4], "hands": [], "tiles": []}],
            "private": {"seeds": {}, "shed": {}},
        },
        None,
    )

    assert action["market"] == [["HIRE"], ["HIRE"], ["HIRE"]]
    assert isinstance(bot, FarmerBot)
    assert isinstance(bot, MiniBot)


def test_melon_v1_only_handles_farm_actions():
    bot = FarmerV1(FarmerV1Config())
    base = {
        "step": 100,
        "hour": 4,
        "player": 0,
        "farms": [{"money": 3000, "farmer": [4, 4], "hands": [], "tiles": []}],
        "private": {"seeds": {}, "shed": {"MELON": 7}},
    }

    action = bot({**base, "day": 20}, None)

    assert action["market"] == []


def test_economy_v1_handles_selling():
    bot = EconomyV1(EconomyV1Config(sell_day=20))
    action = bot(
        {
            "step": 500,
            "day": 20,
            "hour": 4,
            "private": {"shed": {"MELON": 7}},
            "farms": [{"hands": []}],
        },
        None,
    )

    assert action["market"] == [["SELL", "MELON", 7]]
    assert isinstance(bot, EconomyBot)
    assert isinstance(bot, MiniBot)


def test_economy_v1_handles_opening_seed_purchase():
    bot = EconomyV1(EconomyV1Config())
    action = bot(
        {
            "step": 0,
            "day": 0,
            "hour": 0,
            "player": 0,
            "farms": [{"money": 3000}],
            "private": {"seeds": {}, "shed": {}},
        },
        None,
    )

    assert action["market"] == [
        ["BUY_LAND"],
        ["BUY_SEED", "MELON", 24],
    ]


def test_economy_v1_forecasts_market_snapshot():
    bot = EconomyV1(EconomyV1Config())
    analysis = bot.forecast_prices(
        {
            "market": {"prices": {"MELON": 250}},
            "town": {"unlocked_shops": ["YARN_STORE"]},
        },
        horizon=3,
    )

    assert analysis.prices["MELON"] == (250.0, 250.0, 250.0)
    assert analysis.shop_demand["WOOL"] == 2


def test_runner_can_run_two_configured_bots():
    result = run_scenario(
        agents=(
            compose_bots(FarmerV1(), EconomyV1()),
            compose_bots(FarmerV1(), EconomyV1()),
        ),
        steps=48,
        seed=20260822,
        name="opening smoke test",
    )

    assert result.name == "opening smoke test"
    assert result.steps == 48
    assert len(result.rewards) == 2
    assert result.first_prices["MELON"] == 250.0
