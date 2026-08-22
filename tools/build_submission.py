"""Build the multi-file Kaggle submission archive."""

from __future__ import annotations

import argparse
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/submission.tar.gz")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    sources = [ROOT / "main.py"] + sorted((ROOT / "kaggriculture_agent").rglob("*.py"))
    with tarfile.open(output, "w:gz") as archive:
        for source in sources:
            archive.add(source, arcname=source.relative_to(ROOT))
    with tarfile.open(output, "r:gz") as archive:
        names = archive.getnames()
    if "main.py" not in names or "kaggriculture_agent/agent.py" not in names:
        raise RuntimeError("submission archive is incomplete")
    print(f"built={output} files={len(names)}")


if __name__ == "__main__":
    main()
