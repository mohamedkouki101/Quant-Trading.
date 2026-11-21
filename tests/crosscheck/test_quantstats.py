"""V-4: analytics.metrics vs QuantStats 0.0.86 on the same series (PLAN §9.3 step 3).

Definitions aligned: RF = 0 in QuantStats (excess returns passed in when RF matters), 252
periods for daily and 12 for monthly data. purgedcv parity for DSR/PBO moves to B-2 (C18).
"""

import warnings

import numpy as np
import pandas as pd
import pytest

from momlab.analytics import metrics

qs = pytest.importorskip("quantstats")
TOL = 1e-6


def _series(freq: str, n: int, seed: int, first: float | None = None) -> pd.Series:
    rng = np.random.default_rng(seed)
    scale = 0.01 if freq == "B" else 0.045
    r = rng.standard_t(4, n) * scale + 0.0003
    if first is not None:
        r[0] = first
    idx = pd.date_range("1990-01-01", periods=n, freq=freq)
    return pd.Series(r, index=idx)


CASES = [
    ("D", _series("B", 2520, 1)),
    ("D", _series("B", 750, 2, first=-0.05)),  # loss on day one: drawdown from the start
    ("M", _series("ME", 240, 3)),
    ("M", _series("ME", 120, 4, first=-0.12)),
]


@pytest.mark.parametrize(
    ("freq", "r"), CASES, ids=["daily", "daily-first-loss", "monthly", "monthly-first-loss"]
)
def test_metrics_match_quantstats(freq: str, r: pd.Series) -> None:
    periods = 252 if freq == "D" else 12
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        exp = {
            "sharpe": qs.stats.sharpe(r, rf=0.0, periods=periods),
            "sortino": qs.stats.sortino(r, rf=0.0, periods=periods),
            "mdd": qs.stats.max_drawdown(r),
            "cagr": qs.stats.cagr(r, rf=0.0, periods=periods),
        }
    got = {
        "sharpe": metrics.sharpe(r, freq=freq),
        "sortino": metrics.sortino(r, freq=freq),
        "mdd": metrics.max_drawdown(r),
        "cagr": metrics.annual_return(r, freq=freq),
    }
    for k in exp:
        assert got[k] == pytest.approx(float(exp[k]), abs=TOL), k


def test_rf_subtraction_matches_quantstats_on_excess_returns() -> None:
    r = _series("B", 1500, 5)
    rf = pd.Series(np.random.default_rng(6).uniform(0, 0.0003, len(r)), index=r.index)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        exp_sharpe = qs.stats.sharpe(r - rf, rf=0.0, periods=252)
        exp_sortino = qs.stats.sortino(r - rf, rf=0.0, periods=252)
    assert metrics.sharpe(r, rf, freq="D") == pytest.approx(float(exp_sharpe), abs=TOL)
    assert metrics.sortino(r, rf, freq="D") == pytest.approx(float(exp_sortino), abs=TOL)
