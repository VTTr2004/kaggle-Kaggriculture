"""Kaggle submission entry point.

Build ``submission.tar.gz`` with ``python tools/build_submission.py``. Kaggle
requires this file at the archive root and calls the exported ``agent``.
"""

from kaggriculture_agent.agent import agent

__all__ = ["agent"]
