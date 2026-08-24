from __future__ import annotations

from types import SimpleNamespace

from kaggriculture_agent.farm import optimize_farm_plan as exported_optimizer
from kaggriculture_agent.farm.planner import (
    build_hardcoded_farm_plans,
    farm_plan_to_dict,
    OFFICIAL_CROPS,
    PlantState,
    days_until_first_yield,
    days_until_harvest,
    extract_farm_snapshot,
    optimize_farm_plan,
    project_crop,
)


def test_farm_package_exports_planner_entrypoint() -> None:
    assert exported_optimizer is optimize_farm_plan


def test_official_crop_rules_match_kaggriculture() -> None:
    assert OFFICIAL_CROPS["WHEAT"].seed_cost == 10
    assert OFFICIAL_CROPS["WHEAT"].first_yield_day == 2
    assert OFFICIAL_CROPS["TOMATO"].interval == 1
    assert OFFICIAL_CROPS["STRAWBERRY"].interval == 2
    assert OFFICIAL_CROPS["MELON"].max_yield == 6


def test_days_until_first_yield_uses_current_plant_age() -> None:
    melon = OFFICIAL_CROPS["MELON"]

    assert days_until_first_yield(melon, planted_day=3, current_day=8) == 5
    assert days_until_first_yield(melon, planted_day=3, current_day=13) == 0


def test_days_until_harvest_returns_zero_for_ready_existing_yield() -> None:
    plant = PlantState("MELON", planted_day=1, yield_units=2)

    assert days_until_harvest(plant, current_day=11) == 0
    assert days_until_harvest(PlantState("MELON", planted_day=1), current_day=5) == 6


def test_project_one_time_crop_uses_best_harvest_day_in_forecast() -> None:
    prices = [250.0] * 10 + [500.0, 500.0, 500.0]

    projection = project_crop(
        OFFICIAL_CROPS["MELON"],
        planted_day=0,
        current_day=0,
        horizon_days=13,
        prices=prices,
    )

    assert projection.total_units == 6
    assert projection.harvest_day == 10
    assert projection.revenue == 3000.0


def test_project_ongoing_crop_emits_interval_harvests() -> None:
    projection = project_crop(
        OFFICIAL_CROPS["STRAWBERRY"],
        planted_day=0,
        current_day=0,
        horizon_days=18,
        prices=[120.0] * 18,
    )

    assert projection.harvest_days == (10, 12, 14, 16)
    assert projection.total_units == 4
    assert projection.revenue == 480.0


def test_optimizer_respects_capacity_and_current_forecast() -> None:
    plan = optimize_farm_plan(
        current_day=0,
        remaining_days=30,
        free_tiles=3,
        price_forecast={
            "CARROT": [35.0] * 30,
            "MELON": [250.0] * 10 + [500.0] * 20,
        },
        candidate_crops=("CARROT", "MELON"),
    )

    assert plan.seed_targets == {"MELON": 3}
    assert sum(plan.seed_targets.values()) <= 3


def test_optimizer_changes_crop_when_forecast_changes() -> None:
    plan = optimize_farm_plan(
        current_day=0,
        remaining_days=30,
        free_tiles=1,
        price_forecast={
            "CARROT": [100.0] * 30,
            "MELON": [50.0] * 30,
        },
        candidate_crops=("CARROT", "MELON"),
    )

    assert plan.seed_targets == {"CARROT": 1}


def test_hardcoded_planner_builds_both_horizons_without_forecast() -> None:
    plans = build_hardcoded_farm_plans(current_day=1, free_tiles=2)

    assert set(plans) == {5, 10}
    assert plans[5].seed_targets == {"WHEAT": 2}
    assert plans[10].seed_targets == {"WHEAT": 2}
    assert plans[5].planting_days == {"WHEAT": (1, 1)}
    assert all(projection.harvest_day == 5 for projection in plans[5].projections)


def test_farm_plan_serialization_keeps_schedule_and_value() -> None:
    plan = build_hardcoded_farm_plans(current_day=1, free_tiles=1)[5]

    payload = farm_plan_to_dict(plan)

    assert payload["seed_targets"] == {"WHEAT": 1}
    assert payload["planting_days"] == {"WHEAT": [1]}
    assert payload["projections"][0]["harvest_events"][0]["day"] == 5
    assert payload["projected_profit"] == 90.0


def test_extract_farm_snapshot_reads_current_plants_and_free_tiles() -> None:
    observation = {
        "day": 7,
        "farms": [
            {
                "tiles": [
                    [
                        None,
                        {
                            "kind": "PLANT",
                            "crop": "MELON",
                            "planted_day": 1,
                            "yield_units": 4,
                        },
                        "LOCKED",
                    ]
                ]
            }
        ],
    }

    snapshot = extract_farm_snapshot(observation, remaining_days=23)

    assert snapshot.current_day == 7
    assert snapshot.remaining_days == 23
    assert snapshot.free_tiles == 1
    assert snapshot.existing_plants[0].crop == "MELON"
    assert snapshot.existing_plants[0].yield_units == 4


def test_optimizer_uses_snapshot_capacity_without_replacing_existing_plants() -> None:
    observation = {
        "day": 0,
        "farms": [{"tiles": [[{"kind": "PLANT", "crop": "CARROT", "planted_day": 0}]]}],
    }
    snapshot = extract_farm_snapshot(observation, remaining_days=30)

    plan = optimize_farm_plan(
        current_day=snapshot.current_day,
        remaining_days=snapshot.remaining_days,
        free_tiles=snapshot.free_tiles,
        price_forecast={"MELON": [500.0] * 30},
        existing_plants=snapshot.existing_plants,
        candidate_crops=("MELON",),
    )

    assert plan.seed_targets == {}


def test_extract_farm_snapshot_accepts_kaggle_style_objects() -> None:
    observation = SimpleNamespace(
        day=4,
        farms=[
            SimpleNamespace(
                tiles=[
                    [
                        SimpleNamespace(
                            kind="PLANT", crop="CARROT", planted_day=2, yield_units=1
                        )
                    ]
                ]
            )
        ],
    )

    snapshot = extract_farm_snapshot(observation, remaining_days=26)  # type: ignore[arg-type]

    assert snapshot.existing_plants == (PlantState("CARROT", 2, 1),)
