"""V-1: synthetic markets with a known answer (PLAN §9.2 S1–S3). Hypothetical backtests only."""

import math

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from momlab import engine, synthetic
from momlab.costs import FlatBps
from momlab.data.handler import AsOfView, DataHandler
from momlab.events import MarketEvent, SignalEvent
from momlab.portfolio import NoRisk


def test_null_market_shape_and_moments() -> None:
    m = synthetic.null_market(n_assets=49, n_years=30, seed=1)
    assert m.returns.shape == (len(m.dates), 49) and len(m.assets) == 49
    assert m.dates[0] == pd.Timestamp("1950-01-02") and m.dates[-1] < pd.Timestamp("1980-01-01")
    assert abs(m.returns.mean()) < 3 * 0.01 / math.sqrt(m.returns.size)
    assert m.returns.std() == pytest.approx(0.01, rel=0.01)
    assert (m.rf == 0).all()
    again = synthetic.null_market(n_assets=49, n_years=30, seed=1)
    np.testing.assert_array_equal(m.returns, again.returns)


def test_planted_momentum_generator_is_consistent() -> None:
    """Every period's expected return is the hand formula from the generator's own picks."""
    p = synthetic.planted_momentum(n_assets=12, n_years=3, beta=0.02, n_per_leg=3, seed=2)
    assert len(p.periods) == 36 - 12 - 1  # signals from month 12 on, last one has no full period
    first = p.periods[0]
    # The first signal is at the end of month 12 (index 11): its fill is the first day of month 13.
    month13 = p.dates[(p.dates.year == 1902) & (p.dates.month == 1)]
    assert p.dates[first.fill_row] == month13[0]
    n = len(month13)
    g = (1 + 0.02 * first.z / (n - 1)) ** (n - 1) - 1
    exp = g[list(first.long)].mean() - g[list(first.short)].mean()
    assert first.expected == pytest.approx(exp, rel=1e-12)
    # Picks are the top / bottom n of the score computed from realised monthly returns.
    assert set(first.long) == set(np.argsort(-first.score)[:3])
    assert set(first.short) == set(np.argsort(-first.score)[-3:])


@pytest.mark.slow
def test_s1_null_market() -> None:
    """200 null markets: |HAC t| > 2 in about 5% of seeds; mean Sharpe about 0."""
    res = synthetic.run_trials(synthetic.s1_trial, seed=101, n=200)
    t = np.array([r[0] for r in res])
    sr = np.array([r[1] for r in res])
    lo, hi = stats.binom.interval(0.95, 200, 0.05)
    n_reject = int((np.abs(t) > 2).sum())
    print(
        f"S1: {n_reject}/200 seeds with |t| > 2 (band {lo:.0f}-{hi:.0f}); mean SR {sr.mean():.4f}"
    )
    assert lo <= n_reject <= hi
    assert abs(sr.mean()) < 3 * sr.std(ddof=1) / math.sqrt(200)


@pytest.mark.slow
def test_s2_planted_momentum_ci_coverage() -> None:
    """50 planted markets over 100 years: the engine's mean holding-period return minus the
    generator's expected value has a 95% CI containing 0 in at least 90% of seeds."""
    res = synthetic.run_trials(synthetic.s2_trial, seed=202, n=50)
    covered = np.array([r[0] for r in res])
    picks_ok = np.array([r[1] for r in res])
    print(f"S2: CI covers 0 in {covered.sum()}/50 seeds; picks match in {picks_ok.sum()}/50")
    assert picks_ok.all()
    assert covered.mean() >= 0.9


class _Alternating:
    """Targets +a and −a on alternate month ends (S3)."""

    def __init__(self, dates: pd.DatetimeIndex, a: list[float]) -> None:
        month_end = pd.Series(dates, index=dates).groupby(dates.to_period("M")).max()
        self.schedule = {ts: (1 if k % 2 == 0 else -1) for k, ts in enumerate(month_end[:-1])}
        self.a = np.array(a)

    def on_market(self, ev: MarketEvent, view: AsOfView) -> SignalEvent | None:
        sign = self.schedule.get(ev.ts)
        return None if sign is None else SignalEvent(ts=ev.ts, weights=sign * self.a)


@pytest.mark.parametrize("bps", [0.0, 10.0])
@pytest.mark.parametrize("r", [0.0, 0.0004])
def test_s3_deterministic_cost_market(bps: float, r: float) -> None:
    m = synthetic.cost_market(n_assets=4, n_months=6, r=r)
    sig = _Alternating(m.dates, [0.5, -0.5, 0.25, -0.25])
    dh = DataHandler(m.dates, m.assets, m.returns, rf=m.rf)
    res = engine.run_with(dh, sig, NoRisk(), FlatBps(bps), fill_lag=1)
    d = res.daily
    # Hand values: first fill trades Σ|a| = 1.5; every later fill flips the book, 2 × 1.5 = 3.0.
    to = d["turnover"][d["turnover"] > 0].to_numpy()
    assert len(to) == 5 and to[0] == 1.5
    np.testing.assert_allclose(to[1:], 3.0, rtol=0, atol=1e-15)
    cost = bps * 1e-4 * d["turnover"]
    if r == 0.0:
        np.testing.assert_allclose(d["net"], -cost, rtol=0, atol=1e-15)
    expected = (1 + r) * (1 - cost) - 1
    np.testing.assert_allclose(d["net"], expected, rtol=0, atol=1e-15)
