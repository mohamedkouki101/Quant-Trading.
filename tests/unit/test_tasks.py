"""Tests for the tasks.py task runner (only behaviour that needs no tools to run)."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "tasks.py"), *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )


def test_unknown_target_lists_targets_and_exits_1() -> None:
    res = _run("no-such-target")
    assert res.returncode == 1
    for target in ("test", "test-fast", "test-data", "lint", "format", "typecheck", "check", "ci"):
        assert target in res.stdout


def test_no_target_exits_1() -> None:
    assert _run().returncode == 1
