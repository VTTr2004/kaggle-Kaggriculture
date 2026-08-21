"""Run one full local Kaggriculture match."""
import sys
import os
from pathlib import Path

# Use packages installed inside this project's virtual environment.
venv_packages = Path(__file__).parent / ".venv" / "Lib" / "site-packages"
if venv_packages.exists():
    sys.path.insert(0, str(venv_packages))

# This dependency prints an unrelated OpenSpiel game catalogue directly from
# native code while loading. Silence the process handles temporarily.
stdout_fd, stderr_fd = os.dup(1), os.dup(2)
null = open(os.devnull, "w")
os.dup2(null.fileno(), 1)
os.dup2(null.fileno(), 2)
try:
    from kaggle_environments import make
    env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=True)
finally:
    os.dup2(stdout_fd, 1)
    os.dup2(stderr_fd, 2)
    os.close(stdout_fd)
    os.close(stderr_fd)
    null.close()
from main import agent

env.run([agent, "random"])
print("steps:", len(env.steps))
print("final scores:", [state.reward for state in env.steps[-1]])
