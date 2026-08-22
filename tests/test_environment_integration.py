from kaggle_environments import make


def test_real_environment_accepts_modular_agent() -> None:
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": 48, "seed": 20260822},
        debug=True,
    )
    env.run(["main.py", "starter"])
    assert all(state.status == "DONE" for state in env.steps[-1])
    assert all(state.reward is not None for state in env.steps[-1])
