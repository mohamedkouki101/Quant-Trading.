"""Read-only git queries for the ledger and the test vault (correction C12).

Only ``git rev-parse HEAD``, ``git status --porcelain`` and ``git tag -l <tag>`` are ever run.
Nothing here changes the repository. When git is missing or the folder is not a repository,
the functions fall back to safe values: sha ``"nogit"``, dirty ``None``, tag absent (so the
test vault stays locked).
"""

from __future__ import annotations

import subprocess

from momlab import paths


def _git(*args: str) -> str | None:
    try:
        res = subprocess.run(
            ["git", *args], cwd=paths.ROOT, capture_output=True, text=True, check=False, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if res.returncode != 0:
        return None
    return str(res.stdout)


def git_sha() -> str:
    """Current commit sha, or ``"nogit"``."""
    out = _git("rev-parse", "HEAD")
    return out.strip() if out else "nogit"


def git_dirty() -> bool | None:
    """True if the working tree has uncommitted changes; None when unknown."""
    out = _git("status", "--porcelain")
    return None if out is None else bool(out.strip())


def git_tag_exists(tag: str) -> bool:
    """True only if ``git tag -l <tag>`` lists exactly that tag."""
    out = _git("tag", "-l", tag)
    return out is not None and tag in out.split()
