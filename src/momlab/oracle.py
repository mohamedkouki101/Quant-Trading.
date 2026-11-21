"""Vectorised reference implementation (task E-6), written independently of the engine.

It must not import the engine, portfolio, execution, data handler, signal or risk modules: a
timing bug would then have to be made twice, in two different styles, to go unnoticed. It
implements the same conventions (DECISIONS 010) another way: month returns by group-by, scores
by array products, and holdings valued per holding period from cumulative products
(``V_s = cash · Π(1+rf) + Σ w_i · Π(1+r_i)``) instead of a daily weight update.

Supports B1, B3, B4 and B5 with ``FlatBps`` costs and no caps (the E-6 acceptance set).
"""

from __future__ import annotations

import math

import numpy as np
import numpy.typing as npt
import pandas as pd

from momlab.config import RunConfig

FloatArray = npt.NDArray[np.float64]


def _rebalance_rows(dates: pd.DatetimeIndex) -> list[int]:
    """Row of the last trading day of each month; an apparently unfinished last month (the
    next weekday is in the same month) is dropped."""
    months = dates.to_period("M")
    last = pd.Series(np.arange(len(dates))).groupby(np.asarray(months.asi8)).max()
    rows = [int(r) for r in last.to_numpy()]
    final = dates[-1]
    if (final + pd.offsets.BDay(1)).to_period("M") == final.to_period("M"):
        rows = rows[:-1]
    return rows


def _month_table(dates: pd.DatetimeIndex, rets: FloatArray) -> tuple[FloatArray, FloatArray]:
    """Compounded calendar-month returns (NaN if any day is missing) and, per row, the
    position of its month."""
    key = np.asarray(dates.to_period("M").asi8)
    growth = pd.DataFrame(1.0 + rets)
    prod = growth.groupby(key, sort=True).prod()
    missing = growth.isna().groupby(key, sort=True).any()
    monthly = (prod - 1.0).where(~missing).to_numpy()
    month_pos = np.searchsorted(np.unique(key), key).astype(np.float64)
    return monthly, month_pos


def _pick(score: FloatArray, n: int) -> FloatArray:
    w = np.zeros(score.shape[0])
    ok = np.flatnonzero(~np.isnan(score))
    if ok.size < 2 * n:
        return w
    ranked = ok[np.argsort(-score[ok], kind="stable")]
    w[ranked[:n]] = 1.0 / n
    w[ranked[-n:]] = -1.0 / n
    return w


def _targets(
    cfg: RunConfig, dates: pd.DatetimeIndex, rets: FloatArray
) -> list[tuple[int, FloatArray]]:
    """(order row, unscaled target) for every rebalance that produces a signal."""
    monthly, month_pos = _month_table(dates, rets)
    out = []
    for row in _rebalance_rows(dates):
        if cfg.strategy == "b1":
            ok = ~np.isnan(rets[row])
            w = np.where(ok, 1.0 / ok.sum(), 0.0) if ok.any() else np.zeros(rets.shape[1])
            out.append((row, w))
            continue
        m = int(month_pos[row])
        lb, skip = cfg.lookback_months, cfg.skip_months
        if m < lb - 1:
            continue
        window = monthly[m - lb + 1 : m - skip + 1]
        score = np.prod(1.0 + window, axis=0) - 1.0
        sign = cfg.signal_sign if cfg.strategy == "b5" else 1
        out.append((row, _pick(sign * score, cfg.n_per_leg)))
    return out


def _simulate(
    rets0: FloatArray, rf: FloatArray, fills: list[tuple[int, FloatArray]], bps: float
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Daily gross and net returns and end-of-day weights for a book that trades to each
    target at the close of its fill row and holds it in between (value-based)."""
    n_t, n_a = rets0.shape
    gross = rf.copy()  # no position before the first fill: all cash
    net = rf.copy()
    weights = np.zeros((n_t, n_a))
    bounds = [f for f, _ in fills] + [n_t - 1]
    held = np.zeros(n_a)
    for k, (f, target) in enumerate(fills):
        # Pre-fill weights at the close of f: drifted from the previous period (or zero).
        drifted = weights[f] if k > 0 else np.zeros(n_a)
        cost = bps * 1e-4 * float(np.abs(target - drifted).sum())
        net[f] = (1.0 + gross[f]) * (1.0 - cost) - 1.0
        weights[f] = target
        held = target
        end = bounds[k + 1]
        if end <= f:
            continue
        seg = slice(f + 1, end + 1)
        p = np.cumprod(1.0 + rets0[seg], axis=0)
        cash = (1.0 - held.sum()) * np.cumprod(1.0 + rf[seg])
        value = cash + p @ held
        prev = np.r_[1.0, value[:-1]]
        gross[seg] = value / prev - 1.0
        net[seg] = gross[seg]
        weights[seg] = held * p / value[:, None]
    return gross, net, weights


def run_oracle(
    config: RunConfig, dates: pd.DatetimeIndex, returns: FloatArray, rf: FloatArray
) -> pd.DataFrame:
    """Daily ``gross``, ``net`` and end-of-day weights ``w_0 … w_{N-1}`` for the config."""
    if config.cost.model != "flat":
        raise NotImplementedError("the oracle supports FlatBps only")
    if any(c is not None for c in (config.gross_cap, config.net_cap, config.position_cap)):
        raise NotImplementedError("the oracle does not apply caps")
    dates = pd.DatetimeIndex(dates)
    rets = np.asarray(returns, dtype=np.float64)
    rets0 = np.where(np.isnan(rets), 0.0, rets)
    rf = np.asarray(rf, dtype=np.float64)
    n_t = len(dates)
    lag = config.fill_lag
    planned = [(row + lag, w) for row, w in _targets(config, dates, rets) if row + lag < n_t]

    if config.strategy == "b4":
        # Unscaled book: same fills, no costs, cash earns nothing; its daily returns from the
        # day after the first fill are the strategy returns the vol estimate uses.
        u_gross, _, _ = _simulate(rets0, np.zeros(n_t), planned, 0.0)
        first = planned[0][0] if planned else n_t
        scaled = []
        for fill_row, u_target in planned:
            order_row = fill_row - lag
            hist = u_gross[first + 1 : order_row + 1]
            if hist.size < config.vol_window:
                lev = 0.0
            else:
                sigma = float(np.std(hist[-config.vol_window :], ddof=1)) * math.sqrt(252)
                lev = (
                    config.leverage_cap
                    if sigma == 0.0
                    else min(config.vol_target / sigma, config.leverage_cap)
                )
            scaled.append((fill_row, u_target * lev))
        planned = scaled

    gross, net, weights = _simulate(rets0, rf, planned, config.cost.bps)
    out = pd.DataFrame({"gross": gross, "net": net}, index=pd.DatetimeIndex(dates, name="date"))
    for j in range(weights.shape[1]):
        out[f"w_{j}"] = weights[:, j]
    return out
