"""Known-answer synthetic markets for verification (task V-1, PLAN §9.2).

Hypothetical data only. Every generator is seeded through ``numpy.random.SeedSequence`` and
works out its known answer (picks, expected returns) itself, without engine code:

- :func:`null_market` (S1): i.i.d. Student-t daily returns with mean 0, so any momentum
  "signal" is noise.
- :func:`planted_momentum` (S2): daily noise plus a planted drift. At the end of month ``m``
  the generator scores each asset on its compounded returns of months ``m−11 … m−1`` (the 12-1
  window), standardises the score across assets (z) and adds ``β·z/(n−1)`` to the asset's
  return on days 2 … n of month ``m+1``. A book bought at the close of day 1 of month ``m+1``
  (``fill_lag = 1``) and held to the close of day 1 of month ``m+2`` has buy-and-hold value
  ``Π(1 + r)``, whose expectation is ``(1 + β z/(n−1))^(n−1)`` because the noise is independent
  with mean 0. The long-short expected return of each holding period follows from the picks.
- :func:`cost_market` (S3): every asset and the risk-free rate return the same constant, so
  weights never drift and the only P&L besides ``r`` is the trading cost.

``s1_trial`` and ``s2_trial`` run one seed through the engine; :func:`run_trials` runs many in
a process pool (they live here, not in the tests, so spawned workers can import them).
"""

from __future__ import annotations

import math
import os
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd

FloatArray = npt.NDArray[np.float64]
Seed = int | np.random.SeedSequence


@dataclass(frozen=True)
class Market:
    """Daily panel: ``returns`` (days × assets, decimal) and daily ``rf``."""

    dates: pd.DatetimeIndex
    assets: list[str]
    returns: FloatArray
    rf: FloatArray


@dataclass(frozen=True)
class HoldingPeriod:
    """One S2 holding period: bought at the close of ``fill_row``, valued at ``end_row``."""

    fill_row: int
    end_row: int
    score: FloatArray
    z: FloatArray
    long: tuple[int, ...]
    short: tuple[int, ...]
    expected: float


@dataclass(frozen=True)
class PlantedMarket(Market):
    """S2 market plus the generator's own holding periods and expected returns."""

    periods: tuple[HoldingPeriod, ...] = ()
    n_per_leg: int = 10


def _rng(seed: Seed) -> np.random.Generator:
    ss = seed if isinstance(seed, np.random.SeedSequence) else np.random.SeedSequence(seed)
    return np.random.default_rng(ss)


def _days(start: str, n_years: int) -> pd.DatetimeIndex:
    first = pd.Timestamp(start)
    return pd.bdate_range(first, first + pd.DateOffset(years=n_years) - pd.Timedelta(days=1))


def _names(n: int) -> list[str]:
    return [f"S{i:02d}" for i in range(n)]


def null_market(
    n_assets: int = 49,
    n_years: int = 30,
    seed: Seed = 0,
    *,
    df: float = 5.0,
    daily_vol: float = 0.01,
    start: str = "1950-01-01",
) -> Market:
    """S1: i.i.d. Student-t returns scaled to ``daily_vol``, mean 0, RF 0."""
    dates = _days(start, n_years)
    t = _rng(seed).standard_t(df, (len(dates), n_assets))
    rets = t * math.sqrt((df - 2.0) / df) * daily_vol
    return Market(dates, _names(n_assets), rets, np.zeros(len(dates)))


def planted_momentum(
    n_assets: int = 49,
    n_years: int = 100,
    beta: float = 0.01,
    seed: Seed = 0,
    *,
    n_per_leg: int = 10,
    noise: float = 0.01,
    start: str = "1901-01-01",
) -> PlantedMarket:
    """S2: normal noise plus the planted 12-1 drift described in the module docstring."""
    dates = _days(start, n_years)
    rets = _rng(seed).normal(0.0, noise, (len(dates), n_assets))
    key = np.asarray(dates.year * 12 + dates.month)
    starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    bounds = np.r_[starts, len(dates)]
    n_months = len(starts)
    monthly = np.empty((n_months, n_assets))
    periods: list[HoldingPeriod] = []
    for m in range(n_months):
        rows = slice(bounds[m], bounds[m + 1])
        monthly[m] = np.prod(1.0 + rets[rows], axis=0) - 1.0
        if m < 11 or m + 1 >= n_months:
            continue
        score = np.prod(1.0 + monthly[m - 11 : m], axis=0) - 1.0
        z = (score - score.mean()) / score.std()
        a, b = bounds[m + 1], bounds[m + 2]
        n = b - a
        rets[a + 1 : b] += beta * z / (n - 1)
        if m + 2 >= n_months:
            continue  # no complete holding period: the book is never re-valued at day 1 of m+2
        order = np.argsort(-score, kind="stable")
        long, short = order[:n_per_leg], order[-n_per_leg:]
        g = (1.0 + beta * z / (n - 1)) ** (n - 1) - 1.0
        expected = float(g[long].mean() - g[short].mean())
        periods.append(
            HoldingPeriod(
                fill_row=int(a),
                end_row=int(bounds[m + 2]),
                score=score,
                z=z,
                long=tuple(int(i) for i in long),
                short=tuple(int(i) for i in short),
                expected=expected,
            )
        )
    return PlantedMarket(
        dates, _names(n_assets), rets, np.zeros(len(dates)), tuple(periods), n_per_leg
    )


def cost_market(
    n_assets: int = 4, n_months: int = 6, r: float = 0.0, start: str = "1990-01-01"
) -> Market:
    """S3: every asset and RF return ``r`` every day."""
    first = pd.Timestamp(start)
    dates = pd.bdate_range(first, first + pd.DateOffset(months=n_months) - pd.Timedelta(days=1))
    return Market(
        dates, _names(n_assets), np.full((len(dates), n_assets), r), np.full(len(dates), r)
    )


def _run_b3(market: Market, n_per_leg: int) -> Any:
    from momlab import engine
    from momlab.config import RunConfig
    from momlab.data.handler import DataHandler

    cfg = RunConfig(
        strategy="b3",
        start=market.dates[0].date(),
        end=market.dates[-1].date(),
        n_per_leg=n_per_leg,
        cost={"model": "flat", "bps": 0.0},
    )
    dh = DataHandler(market.dates, market.assets, market.returns, rf=market.rf)
    return engine.run(cfg, dh)


def s1_trial(seed: Seed) -> tuple[float, float]:
    """One S1 seed: (HAC t of monthly returns, annualised daily Sharpe) of B3 at 0 bp."""
    from momlab.analytics import metrics

    res = _run_b3(null_market(seed=seed), 10)
    first = int(np.flatnonzero(res.daily["turnover"].to_numpy() > 0)[0])
    net = res.daily["net"].iloc[first + 1 :]
    return metrics.newey_west_t(metrics.monthly(net)), metrics.sharpe(net, freq="D")


def s2_trial(seed: Seed) -> tuple[bool, bool]:
    """One S2 seed: (95% CI of mean(realised − expected) contains 0, engine picks match)."""
    mkt = planted_momentum(seed=seed)
    res = _run_b3(mkt, mkt.n_per_leg)
    nav = res.daily["nav"].to_numpy()
    w = res.weights.to_numpy()
    d = np.array([nav[p.end_row] / nav[p.fill_row] - 1.0 - p.expected for p in mkt.periods])
    half = 1.959963984540054 * d.std(ddof=1) / math.sqrt(len(d))
    picks = all(
        set(np.flatnonzero(w[p.fill_row] > 0)) == set(p.long)
        and set(np.flatnonzero(w[p.fill_row] < 0)) == set(p.short)
        for p in mkt.periods
    )
    return bool(abs(d.mean()) <= half), picks


def run_trials(
    fn: Callable[[np.random.SeedSequence], Any], seed: int, n: int, workers: int | None = None
) -> list[Any]:
    """``fn`` on ``SeedSequence(seed).spawn(n)`` in a process pool (results in seed order)."""
    seeds = np.random.SeedSequence(seed).spawn(n)
    workers = workers or min(n, os.cpu_count() or 1)
    if workers == 1:
        return [fn(s) for s in seeds]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(fn, seeds))
