"""Read-only git helpers with safe fallbacks (correction C12)."""

import subprocess
from typing import Any

import pytest

from momlab import gitinfo


class _Done:
    def __init__(self, out: str, code: int = 0) -> None:
        self.stdout = out
        self.returncode = code


def _fake(outputs: dict[str, _Done | Exception]) -> Any:
    def run(cmd: list[str], **kwargs: Any) -> _Done:
        assert cmd[0] == "git"
        assert kwargs["check"] is False
        key = " ".join(cmd[1:])
        out = outputs[key]
        if isinstance(out, Exception):
            raise out
        return out

    return run


ALLOWED = {"rev-parse HEAD", "status --porcelain", "tag -l prereg-v2"}


def test_only_read_only_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def run(cmd: list[str], **kwargs: Any) -> _Done:
        seen.append(" ".join(cmd[1:]))
        return _Done("")

    monkeypatch.setattr(subprocess, "run", run)
    gitinfo.git_sha()
    gitinfo.git_dirty()
    gitinfo.git_tag_exists("prereg-v2")
    assert set(seen) <= ALLOWED


def test_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        _fake(
            {
                "rev-parse HEAD": _Done("abc123\n"),
                "status --porcelain": _Done(" M src/x.py\n"),
                "tag -l prereg-v2": _Done("prereg-v2\n"),
            }
        ),
    )
    assert gitinfo.git_sha() == "abc123"
    assert gitinfo.git_dirty() is True
    assert gitinfo.git_tag_exists("prereg-v2") is True


def test_fallbacks_without_git(monkeypatch: pytest.MonkeyPatch) -> None:
    missing = FileNotFoundError("git")
    monkeypatch.setattr(
        subprocess,
        "run",
        _fake(
            {"rev-parse HEAD": missing, "status --porcelain": missing, "tag -l prereg-v2": missing}
        ),
    )
    assert gitinfo.git_sha() == "nogit"
    assert gitinfo.git_dirty() is None
    assert gitinfo.git_tag_exists("prereg-v2") is False


def test_fallbacks_outside_a_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    fail = _Done("", code=128)
    monkeypatch.setattr(
        subprocess,
        "run",
        _fake({"rev-parse HEAD": fail, "status --porcelain": fail, "tag -l prereg-v2": fail}),
    )
    assert gitinfo.git_sha() == "nogit"
    assert gitinfo.git_dirty() is None
    assert gitinfo.git_tag_exists("prereg-v2") is False
    clean = _Done("")
    monkeypatch.setattr(
        subprocess,
        "run",
        _fake({"status --porcelain": clean, "tag -l prereg-v2": clean}),
    )
    assert gitinfo.git_dirty() is False
    assert gitinfo.git_tag_exists("prereg-v2") is False
