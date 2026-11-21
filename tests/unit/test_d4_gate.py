"""D-4: the vectorised 12-1 long-short used by scripts/d4_momentum_gate.py (hand values)."""

import importlib.util

import numpy as np
import pandas as pd
import pytest

from momlab import paths

_spec = importlib.util.spec_from_file_location(
    "d4_momentum_gate", paths.ROOT / "scripts" / "d4_momentum_gate.py"
)
assert _spec is not None and _spec.loader is not None
d4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(d4)


def _toy() -> pd.DataFrame:
    """15 months, 4 assets. Asset A earns +1%/month, B +2%, C −1%, D 0% except a huge month
    13 (the skip month for holding month 14) and NaN in month 3."""
    idx = pd.date_range("2000-01-31", periods=15, freq="ME")
    w = pd.DataFrame({"A": 0.01, "B": 0.02, "C": -0.01, "D": 0.0}, index=idx)
    w.iloc[12, 3] = 5.0  # month 13: in no 12-1 window that ends before it is held
    return w


def test_mom_12_1_window_is_t_minus_12_to_t_minus_2() -> None:
    s = d4.mom_12_1(_toy())
    # Score for holding month 13 (index 12) uses months 1..11 (index 0..10): 11 months.
    assert s.iloc[12]["A"] == pytest.approx(1.01**11 - 1, abs=1e-15)
    assert s.iloc[12]["B"] == pytest.approx(1.02**11 - 1, abs=1e-15)
    # Holding month 14 (index 13) uses months 2..12: month 13's +500% is skipped.
    assert s.iloc[13]["D"] == pytest.approx(0.0, abs=1e-15)
    # Holding month 15 (index 14) uses months 3..13, which includes the +500% month.
    assert s.iloc[14]["D"] == pytest.approx(5.0, abs=1e-15)
    assert s.iloc[:12].isna().all().all()  # not enough history before month 13


def test_missing_month_excludes_the_asset() -> None:
    w = _toy()
    extra = pd.DataFrame(
        {"A": [0.01], "B": [0.02], "C": [-0.01], "D": [0.0]},
        index=[pd.Timestamp("2001-04-30")],
    )
    w = pd.concat([w, extra])  # 16 months
    w.iloc[2, 0] = np.nan  # A missing in month 3
    s = d4.mom_12_1(w)
    # Month 3 is in the windows of holding months 13, 14 and 15 (months 1-11, 2-12, 3-13).
    assert s.iloc[12:15]["A"].isna().all()
    # Holding month 16 uses months 4..14: month 3 has left the window.
    assert s.iloc[15]["A"] == pytest.approx(1.01**11 - 1, abs=1e-15)


def test_long_short_return() -> None:
    w = _toy()
    ls = d4.long_short(w, n=1)
    # Holding month 13: best score B (+2%/m), worst C (−1%/m); return = R_B − R_C in month 13.
    assert ls.iloc[0] == pytest.approx(0.02 - (-0.01), abs=1e-15)
    assert ls.index[0] == w.index[12]
    # Holding month 15: D has the best score (+500% in its window), C still worst.
    assert ls.iloc[2] == pytest.approx(0.0 - (-0.01), abs=1e-15)
    assert len(ls) == 3
