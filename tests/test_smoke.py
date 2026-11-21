"""Smoke test: the package imports and reports the installed version."""

from importlib.metadata import version

import momlab


def test_version_string() -> None:
    assert momlab.__version__ == "0.1.0"
    assert momlab.__version__ == version("momlab")
