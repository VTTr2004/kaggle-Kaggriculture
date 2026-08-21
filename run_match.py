"""
Test Kaggriculture Agent locally using kaggle-environments

Run: python run_match.py
"""
import json
from typing import Dict
from agent import agent

try:
    from kaggle_environments import make, evaluate
except ImportError:
    print("Installing kaggle-environments...")
    import subprocess
    subprocess.run(["pip", "install", "kaggle-environments"], check=True)
    from kaggle_environments import make, evaluate


def run_match(
    my_agent=agent,
    opponent="random",
    steps: int = 200,
    verbose: bool = True,
):
    """
    Run a single match between two agents.

    Args:
        my_agent: Your agent function
        opponent: Opponent agent ("random", "starter", or another function)
        steps: Number of steps to run
        verbose: Whether to print progress
    """
    env = make(
        "kaggriculture",
        configuration={
            "episodeSteps": steps,
            "agent_timeout": 60,
        }
    )

    # Run the match
    result = env.run([my_agent, opponent])

    if verbose:
        print("\n" + "=" * 60)
        print("MATCH RESULT")
        print("=" * 60)

        # Get final scores
        for i, agent_name in enumerate(["Your Agent", "Opponent"]):
            final_obs = result[-1][i]
            money = final_obs.get("rewards", [0, 0])[i]
            print(f"{agent_name}: ${money if money is not None else 'N/A'}")

        # Print rewards over time
        rewards = [r[i] for r in env.steps if r[i] is not None and "rewards" in r[i] for i in [0, 1]]
        print(f"\nTotal turns played: {len(result)}")
        print("=" * 60)

        # Render the game
        print("\nRendering game visualization...")
        try:
            html = env.render(mode="html")
            with open("match_replay.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("Saved to match_replay.html")
        except Exception as e:
            print(f"Could not render: {e}")

    return result


def run_multiple_matches(n: int = 10, opponent: str = "random"):
    """
    Run multiple matches and calculate win rate.
    """
    print(f"\nRunning {n} matches against {opponent}...")

    wins = 0
    losses = 0
    ties = 0
    total_score = 0
    total_opponent = 0

    for i in range(n):
        result = run_match(agent, opponent, verbose=False)
        final = result[-1]

        my_reward = final[0].get("rewards", [0])[0] if final[0].get("rewards") else 0
        opp_reward = final[1].get("rewards", [0])[0] if len(final) > 1 and final[1].get("rewards") else 0

        total_score += my_reward or 0
        total_opponent += opp_reward or 0

        if (my_reward or 0) > (opp_reward or 0):
            wins += 1
        elif (my_reward or 0) < (opp_reward or 0):
            losses += 1
        else:
            ties += 1

        if (i + 1) % 5 == 0:
            print(f"  Completed {i + 1}/{n} matches...")

    print("\n" + "=" * 50)
    print("STATISTICS")
    print("=" * 50)
    print(f"Wins:   {wins}/{n} ({100*wins/n:.1f}%)")
    print(f"Losses: {losses}/{n} ({100*losses/n:.1f}%)")
    print(f"Ties:   {ties}/{n} ({100*ties/n:.1f}%)")
    print(f"Avg Score: {total_score/n:.1f} vs Opponent: {total_opponent/n:.1f}")
    print("=" * 50)

    return {"wins": wins, "losses": losses, "ties": ties}


def test_agent_structure():
    """Test that agent returns correct structure."""
    print("Testing agent output structure...")

    mock_obs = {
        "player": 0,
        "day": 0,
        "step": 0,
        "farms": [
            {
                "farmer": [0, 0],
                "money": 100,
                "tiles": [[None] * 10 for _ in range(10)],
            }
        ],
        "private": {
            "seeds": {"WHEAT": 5},
            "shed": {},
        },
        "market": {},
    }

    result = agent(mock_obs)

    assert isinstance(result, dict), "Agent must return dict"
    assert "farmer" in result, "Agent must have 'farmer' key"
    assert "hands" in result, "Agent must have 'hands' key"
    assert "market" in result, "Agent must have 'market' key"
    assert isinstance(result["farmer"], list), "'farmer' must be list"
    assert isinstance(result["hands"], list), "'hands' must be list"
    assert isinstance(result["market"], list), "'market' must be list"

    print("Agent structure: OK")


if __name__ == "__main__":
    print("Kaggriculture Agent - Local Testing")
    print("=" * 50)

    # Test agent structure first
    test_agent_structure()
    print()

    # Run a single match
    print("Running a single match against 'random' opponent...")
    run_match(agent, "random")

    # Run multiple matches for statistics
    print("\n" + "=" * 50)
    print("Would you like to run more matches? (y/n): ", end="")
    try:
        response = input()
        if response.lower() == "y":
            run_multiple_matches(10, "random")
    except EOFError:
        print("(Skipping interactive mode)")
