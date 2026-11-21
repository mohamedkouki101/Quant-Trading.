"""E-7: metrics, block bootstrap and factor regressions (hand-computed expected values)."""

import math

import numpy as np
import pandas as pd
import pytest

from momlab.analytics import bootstrap, factors, metrics


def _s(values: list[float], start: str = "2001-01-01", freq: str = "B") -> pd.Series:
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq=freq))


def test_sharpe_daily_and_rf() -> None:
    r = _s([0.01, 0.02, 0.03, 0.04])
    sd = math.sqrt(((0.015**2) * 2 + (0.005**2) * 2) / 3)  # sample sd of the series
    assert metrics.sharpe(r, freq="D") == pytest.approx(0.025 / sd * math.sqrt(252), rel=1e-12)
    # A constant RF of 0.01 lowers the mean to 0.015 and leaves the sd unchanged.
    rf = _s([0.01] * 4)
    assert metrics.sharpe(r, rf, freq="D") == pytest.approx(0.015 / sd * math.sqrt(252), rel=1e-12)


def test_sharpe_monthly_uses_sqrt12() -> None:
    r = _s([0.01, 0.02, 0.03, 0.04], freq="ME")
    d = metrics.sharpe(r, freq="D")
    m = metrics.sharpe(r, freq="M")
    assert m == pytest.approx(d * math.sqrt(12) / math.sqrt(252), rel=1e-12)
    with pytest.raises(ValueError, match="freq"):
        metrics.sharpe(r, freq="W")  # type: ignore[arg-type]


def test_max_drawdown_two_drawdowns() -> None:
    """Wealth from 1: 1.1, 0.88, 1.1, 1.21, 1.089, 0.9801, 1.47015.
    First drawdown 1.1 -> 0.88 = -20%; second 1.21 -> 0.9801 = -19%. Max is -20%."""
    r = _s([0.10, -0.20, 0.25, 0.10, -0.10, -0.10, 0.50])
    assert metrics.max_drawdown(r) == pytest.approx(-0.20, abs=1e-12)
    dd = metrics.drawdown_series(r)
    assert dd.iloc[5] == pytest.approx(0.9801 / 1.21 - 1, abs=1e-12)
    # A loss on the first day is a drawdown from the starting wealth of 1.
    assert metrics.max_drawdown(_s([-0.1, 0.05])) == pytest.approx(-0.1, abs=1e-12)


def test_sortino_calmar_annualised() -> None:
    r = _s([0.02, -0.01, 0.03, -0.02])
    # Downside deviation: sqrt(mean(min(r,0)^2)) = sqrt((0.0001 + 0.0004) / 4)
    dd = math.sqrt((0.0001 + 0.0004) / 4)
    assert metrics.sortino(r, freq="D") == pytest.approx(0.005 / dd * math.sqrt(252), rel=1e-12)
    wealth = 1.02 * 0.99 * 1.03 * 0.98
    cagr = wealth ** (252 / 4) - 1
    assert metrics.annual_return(r, freq="D") == pytest.approx(cagr, rel=1e-12)
    # Wealth 1.02, 1.0098, 1.040094, 1.01929212: drawdowns -1% then -2% (from the 1.040094 peak).
    assert metrics.max_drawdown(r) == pytest.approx(-0.02, abs=1e-12)
    assert metrics.calmar(r, freq="D") == pytest.approx(cagr / 0.02, rel=1e-10)
    sd = math.sqrt(sum((x - 0.005) ** 2 for x in [0.02, -0.01, 0.03, -0.02]) / 3)
    assert metrics.annual_vol(r, freq="D") == pytest.approx(sd * math.sqrt(252), rel=1e-12)


def test_worst_month_skew_kurt() -> None:
    days = pd.bdate_range("2001-01-01", "2001-03-30")
    r = pd.Series(0.0, index=days)
    r.loc["2001-02-01"] = -0.05
    r.loc["2001-02-02"] = -0.05
    # February: 0.95 * 0.95 - 1 = -0.0975
    assert metrics.worst_month(r) == pytest.approx(-0.0975, abs=1e-15)
    x = _s([1.0, 2.0, 3.0, 10.0])
    m = x.mean()
    m2, m3, m4 = ((x - m) ** 2).mean(), ((x - m) ** 3).mean(), ((x - m) ** 4).mean()
    assert metrics.skew(x) == pytest.approx(m3 / m2**1.5, rel=1e-12)
    assert metrics.kurt(x) == pytest.approx(m4 / m2**2, rel=1e-12)  # raw (Pearson), not excess


def test_newey_west_t() -> None:
    rng = np.random.default_rng(1)
    r = pd.Series(rng.normal(0.001, 0.01, 500))
    t0 = metrics.newey_west_t(r, lags=0)
    # With 0 lags HAC equals White; for an intercept-only model that is mean / (sd_pop / sqrt(n))
    sd_pop = r.std(ddof=0)
    assert t0 == pytest.approx(r.mean() / (sd_pop / math.sqrt(len(r))), rel=1e-10)
    assert isinstance(metrics.newey_west_t(r), float)  # default lag rule


def test_lo_eta_and_adjusted_sharpe() -> None:
    # q = 3, rho1 = 0.5, rho2 = 0.25: eta = 3 / sqrt(3 + 2*(2*0.5 + 1*0.25)) = 3 / sqrt(5.5)
    assert metrics.lo_eta(3, [0.5, 0.25]) == pytest.approx(3 / math.sqrt(5.5), rel=1e-12)
    # No autocorrelation: eta = sqrt(q), i.e. the usual annualisation.
    assert metrics.lo_eta(12, [0.0] * 11) == pytest.approx(math.sqrt(12), rel=1e-12)
    with pytest.raises(ValueError, match="autocorrelations"):
        metrics.lo_eta(12, [0.0] * 5)
    rng = np.random.default_rng(2)
    r = _s(list(rng.normal(0.01, 0.04, 240)), freq="ME")
    lo = metrics.lo_adjusted_sharpe(r, freq="M")
    rhos = [r.autocorr(k) for k in range(1, 12)]
    per = r.mean() / r.std(ddof=1)
    assert lo == pytest.approx(per * metrics.lo_eta(12, rhos), rel=1e-10)


def test_turnover_monthly_one_way() -> None:
    days = pd.bdate_range("2001-01-01", "2001-02-28")
    t = pd.Series(0.0, index=days)
    t.loc["2001-01-31"] = 1.0  # Σ|Δw| = 1.0 -> one-way 0.5
    t.loc["2001-02-28"] = 0.6  # one-way 0.3
    assert metrics.monthly_one_way_turnover(t) == pytest.approx(0.4, abs=1e-15)


def test_performance_bundle() -> None:
    rng = np.random.default_rng(3)
    r = _s(list(rng.normal(0.0005, 0.01, 600)))
    perf = metrics.performance(r, freq="D", turnover=pd.Series(0.0, index=r.index))
    for key in (
        "ann_ret",
        "ann_vol",
        "sharpe",
        "sharpe_hac_t",
        "sortino",
        "mdd",
        "calmar",
        "worst_month",
        "skew",
        "kurt",
        "turnover_1way_monthly",
        "n_months",
        "sharpe_lo",
    ):
        assert key in perf
    assert perf["sharpe"] == pytest.approx(metrics.sharpe(r, freq="D"), rel=1e-12)
    assert metrics.performance(r, freq="D")["turnover_1way_monthly"] is None


def test_bootstrap_reproducible_and_blocky() -> None:
    x = np.arange(1000, dtype=float)
    a = bootstrap.stationary_bootstrap(x, np.mean, n_boot=50, mean_block=20, seed=7)
    b = bootstrap.stationary_bootstrap(x, np.mean, n_boot=50, mean_block=20, seed=7)
    c = bootstrap.stationary_bootstrap(x, np.mean, n_boot=50, mean_block=20, seed=8)
    np.testing.assert_array_equal(a, b)
    assert not np.array_equal(a, c)
    idx = bootstrap.stationary_indices(1000, mean_block=20, rng=np.random.default_rng(0))
    # Within a block indices advance by one (wrapping): most steps are +1.
    steps = np.diff(idx) % 1000
    assert (steps == 1).mean() == pytest.approx(1 - 1 / 20, abs=0.03)
    with pytest.raises(ValueError):
        bootstrap.stationary_indices(10, mean_block=0.5, rng=np.random.default_rng(0))


def test_bootstrap_ci() -> None:
    x = np.random.default_rng(4).normal(size=500)
    lo, hi = bootstrap.confidence_interval(x, np.mean, level=0.9, n_boot=200, mean_block=10, seed=1)
    assert lo < x.mean() < hi


def test_factor_regression_recovers_exact_betas() -> None:
    rng = np.random.default_rng(5)
    idx = pd.date_range("2001-01-31", periods=120, freq="ME")
    f = pd.DataFrame({"mkt_rf": rng.normal(size=120), "mom": rng.normal(size=120)}, index=idx)
    y = 0.001 + 1.5 * f["mkt_rf"] - 0.5 * f["mom"]
    res = factors.factor_regression(y, f, hac_lags=3)
    assert res.alpha == pytest.approx(0.001, abs=1e-12)
    assert res.betas["mkt_rf"] == pytest.approx(1.5, abs=1e-12)
    assert res.betas["mom"] == pytest.approx(-0.5, abs=1e-12)
    assert res.nobs == 120 and res.r2 == pytest.approx(1.0, abs=1e-12)
    noisy = y + rng.normal(0, 0.01, 120)
    res2 = factors.factor_regression(noisy.iloc[5:], f, hac_lags=3)  # aligns on dates
    assert res2.nobs == 115 and set(res2.tstats) == {"const", "mkt_rf", "mom"}
