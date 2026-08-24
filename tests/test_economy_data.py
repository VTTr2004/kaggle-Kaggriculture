import json
from pathlib import Path

from kaggriculture_agent.domain import BASE_PRICES, CROPS, SHOP_DEMAND

DATA_DIR = Path(__file__).parents[1] / "data" / "economy"


def test_economy_data_files_exist_and_match_runtime_constants() -> None:
    crop_rules = json.loads((DATA_DIR / "crop_rules.json").read_text())
    market_prices = json.loads((DATA_DIR / "market_prices.json").read_text())
    shop_demand = json.loads((DATA_DIR / "shop_demand.json").read_text())

    assert set(crop_rules) == set(CROPS)
    assert market_prices == BASE_PRICES
    assert {key: tuple(value) for key, value in shop_demand.items()} == SHOP_DEMAND
