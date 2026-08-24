from tools.animal_trial import run_trial


def test_goose_can_be_placed_fed_and_harvested():
    result = run_trial(steps=120)

    assert result.animal_alive is True
    assert result.harvested_eggs >= 1
    assert result.fed_days >= 4
