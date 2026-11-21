"""Task runner for momentum-lab (standard library only; replaces a Makefile on Windows).

Usage: ``uv run python tasks.py <target>``. Run with no target to list the targets.
Tools are called as ``python -m <tool>`` with the interpreter that runs this file, so the
project virtual environment created by ``uv`` is always the one used.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable

COV_ARGS = ["--cov=momlab", "--cov-report=term-missing:skip-covered"]
# PLAN §9.4: these four files need 100% line coverage (checked after the test run).
CORE_FILES = "*/momlab/engine.py,*/momlab/execution.py,*/momlab/costs.py,*/momlab/data/handler.py"
CORE_COVERAGE = [PY, "-m", "coverage", "report", f"--include={CORE_FILES}", "--fail-under=100"]


def _run(cmd: list[str]) -> int:
    """Run one command from the repo root, echo it, and return its exit code."""
    print(f"\n>>> {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


def _seq(*cmds: list[str]) -> int:
    """Run commands in order and stop at the first failure."""
    for cmd in cmds:
        code = _run(cmd)
        if code != 0:
            return code
    return 0


def lint() -> int:
    """ruff check plus ruff format --check."""
    return _seq([PY, "-m", "ruff", "check", "."], [PY, "-m", "ruff", "format", "--check", "."])


def fmt() -> int:
    """Apply ruff formatting and safe lint fixes."""
    return _seq([PY, "-m", "ruff", "format", "."], [PY, "-m", "ruff", "check", "--fix", "."])


def typecheck() -> int:
    """mypy on the package."""
    return _run([PY, "-m", "mypy", "src"])


def test() -> int:
    """All tests except those that need real downloaded data; core files must be 100% covered."""
    return _seq([PY, "-m", "pytest", "-m", "not data", *COV_ARGS], CORE_COVERAGE)


def test_fast() -> int:
    """Unit tests only (no data, no slow tests)."""
    return _run(
        [PY, "-m", "pytest", "tests/unit", "tests/test_smoke.py", "-m", "not data and not slow"]
    )


def test_data() -> int:
    """Only tests that need the real Ken French data (run ``tasks.py data`` first)."""
    return _run([PY, "-m", "pytest", "-m", "data"])


def check() -> int:
    """lint + typecheck + test: the definition-of-done gate."""
    for step in (lint, typecheck, test):
        code = step()
        if code != 0:
            return code
    return 0


def ci() -> int:
    """The same steps as .github/workflows/ci.yml, run locally."""
    uv = shutil.which("uv")
    if uv is None:
        print("uv not found on PATH; it is needed for the `uv sync --frozen` step", file=sys.stderr)
        return 1
    return _seq(
        [uv, "sync", "--frozen"],
        [PY, "-m", "ruff", "check", "."],
        [PY, "-m", "ruff", "format", "--check", "."],
        [PY, "-m", "mypy", "src"],
        [
            PY,
            "-m",
            "pytest",
            "-m",
            "not data",
            "--cov=momlab",
            "--cov-report=html",
            "--cov-report=term",
            "--cov-fail-under=85",
        ],
        CORE_COVERAGE,
    )


def data() -> int:
    """Download the Ken French files (skipped when hashes match) and build processed panels."""
    return _seq(
        [PY, "-m", "momlab.data.kenfrench", "download"],
        [PY, "-m", "momlab.data.kenfrench", "process"],
    )


def profile() -> int:
    """Profile the engine on a synthetic full-size panel (reports/profile.html and .md)."""
    return _run([PY, "scripts/profile_engine.py"])


TARGETS: dict[str, Callable[[], int]] = {
    "test": test,
    "test-fast": test_fast,
    "test-data": test_data,
    "lint": lint,
    "format": fmt,
    "typecheck": typecheck,
    "check": check,
    "ci": ci,
    "data": data,
    "profile": profile,
}


def main(argv: list[str]) -> int:
    """Dispatch one target; print the target list and return 1 when it is missing or unknown."""
    if len(argv) != 1 or argv[0] not in TARGETS:
        if argv:
            print(f"unknown target: {' '.join(argv)}")
        print("usage: uv run python tasks.py <target>\n\ntargets:")
        for name, func in TARGETS.items():
            doc = (func.__doc__ or "").strip().splitlines()[0]
            print(f"  {name:<10} {doc}")
        return 1
    return TARGETS[argv[0]]()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
