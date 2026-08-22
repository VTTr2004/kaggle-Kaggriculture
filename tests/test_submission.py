import subprocess
import sys
import tarfile
from pathlib import Path


def test_submission_builder_has_root_entrypoint(tmp_path: Path) -> None:
    output = tmp_path / "submission.tar.gz"
    subprocess.run(
        [sys.executable, "tools/build_submission.py", "--output", str(output)],
        check=True,
    )
    with tarfile.open(output, "r:gz") as archive:
        names = archive.getnames()
    assert "main.py" in names
    assert "kaggriculture_agent/agent.py" in names
