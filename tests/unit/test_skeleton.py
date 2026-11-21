"""The repository tree matches PLAN §4 (minus the Makefile, correction C3)."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# PLAN §4, written out by hand. MODEL_CARD.md and PREREGISTRATION.md are created by their own
# tasks (W-1 and S-4) and are not part of the skeleton.
EXPECTED_FILES = [
    "README.md",
    "LICENSE",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    "tasks.py",
    ".github/workflows/ci.yml",
    "data/README.md",
    "app/streamlit_app.py",
    "docs/DESIGN.md",
    "docs/DATA.md",
    "docs/DECISIONS.md",
    "docs/LIMITATIONS.md",
    "src/momlab/__init__.py",
    "src/momlab/config.py",
    "src/momlab/events.py",
    "src/momlab/queue.py",
    "src/momlab/data/kenfrench.py",
    "src/momlab/data/etf.py",
    "src/momlab/data/clean.py",
    "src/momlab/data/handler.py",
    "src/momlab/data/calendar.py",
    "src/momlab/features.py",
    "src/momlab/signals/rules.py",
    "src/momlab/signals/model_signal.py",
    "src/momlab/portfolio.py",
    "src/momlab/risk.py",
    "src/momlab/execution.py",
    "src/momlab/costs.py",
    "src/momlab/engine.py",
    "src/momlab/oracle.py",
    "src/momlab/analytics/metrics.py",
    "src/momlab/analytics/overfitting.py",
    "src/momlab/analytics/factors.py",
    "src/momlab/analytics/bootstrap.py",
    "src/momlab/validation.py",
    "src/momlab/models.py",
    "src/momlab/importance.py",
    "src/momlab/ledger.py",
    "src/momlab/synthetic.py",
]

EXPECTED_DIRS = [
    "configs/strategies",
    "configs/sweeps",
    "tests/unit",
    "tests/property",
    "tests/synthetic",
    "tests/crosscheck",
    "tests/regression",
    "tests/fixtures",
    "experiments",
    "results",
    "reports",
    "scripts",
    "notebooks",
    "app/pages",
]


@pytest.mark.parametrize("rel", EXPECTED_FILES)
def test_file_exists(rel: str) -> None:
    assert (ROOT / rel).is_file(), rel


@pytest.mark.parametrize("rel", EXPECTED_DIRS)
def test_dir_exists(rel: str) -> None:
    assert (ROOT / rel).is_dir(), rel


def test_no_makefile() -> None:
    assert not (ROOT / "Makefile").exists()


def test_raw_data_is_gitignored() -> None:
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    for entry in (".env", "data/raw/", "data/interim/", "data/processed/", ".venv/"):
        assert entry in ignored
    assert "data/manifest.json" not in ignored
