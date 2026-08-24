import pytest

from dashboard.app import _economy_schema_is_current
from dashboard.replay import LocalReplay, run_local_match
from dashboard.view_models import analyze_turn, crop_score_breakdown


@pytest.fixture(scope="module")
def replay() -> LocalReplay:
    # Thirteen simulated days keep every crop feasible without paying the cost
    # of a full-season replay in this focused dashboard test.
    return run_local_match(seed=7, opponent="pass", steps=312)


def test_short_replay_can_be_analyzed(replay: LocalReplay) -> None:
    assert replay.turn_count == 312
    analysis = analyze_turn(replay, 0)
    assert analysis.state.day == 0
    assert analysis.plan.selected_crop is not None
    assert analysis.expected_action == analysis.recorded_action


def test_crop_breakdown_reconstructs_score(replay: LocalReplay) -> None:
    analysis = analyze_turn(replay, 0)
    detail = crop_score_breakdown(analysis, analysis.plan.selected_crop or "MELON")

    reconstructed = detail.expected_profit / detail.occupied_days
    assert detail.score == reconstructed
    assert len(detail.expected_unit_prices) == detail.expected_units
    assert detail.price_curve.quoted_price == detail.expected_unit_prices[0]


def test_dashboard_detects_current_economy_schema(replay: LocalReplay) -> None:
    analysis = analyze_turn(replay, 0)

    assert _economy_schema_is_current(analysis)

    # Reproduce the shape retained by the Streamlit process that caused the
    # reported AttributeError, without calling the rendering code.
    old_opportunity = type("OldCropOpportunity", (), {})()
    old_economy = type(
        "OldEconomyFeatures",
        (),
        {"crop_opportunities": [old_opportunity], "sell_opportunities": []},
    )()
    old_analysis = type("OldTurnAnalysis", (), {"economy": old_economy})()

    assert not _economy_schema_is_current(old_analysis)
