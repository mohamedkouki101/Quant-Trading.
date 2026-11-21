"""Performance metrics (task E-7, PLAN §7 and §9.1). Hypothetical backtest, not investment advice.

All inputs are simple decimal returns (0.01 = 1%) on a ``DatetimeIndex``. ``freq`` is ``"D"``
(trading days, 252 a year) or ``"M"`` (months, 12 a year). Where ``rf`` is given it is the
per-period risk-free return, aligned on the index and subtracted first.

Conventions (DECISIONS 012):

- Sharpe: mean / sample sd (ddof 1) of excess returns, times √252 or √12.
- Sortino: mean excess / sqrt(mean(min(excess, 0)²)) over all periods, annualised the same way
  (the QuantStats definition, target 0).
- Annual return: compounded wealth ``W`` over ``n`` periods, ``W^(P/n) − 1``.
- Max drawdown: worst fall of wealth from its running peak, the starting wealth of 1 included.
- Skew and kurtosis: population moments; kurtosis is raw (Pearson, normal = 3), as the PSR/DSR
  formulas expect.
- Newey-West t: OLS of the series on a constant with statsmodels ``cov_type="HAC"``; default
  lags ``floor(4 (T/100)^(2/9))`` (Newey & West 1994).
- Lo (2002): ``SR_annual = SR_period · q / sqrt(q + 2 Σ_{k=1}^{q-1} (q − k) ρ_k)``.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Literal

import numpy as np
import pandas as pd
import statsmodels.api as sm

Freq = Literal["D", "M"]
Metrics = dict[str, float | int | None]
PERIODS: dict[str, int] = {"D": 252, "M": 12}


def _periods(freq: str) -> int:
    if freq not in PERIODS:
        raise ValueError(f"freq must be 'D' or 'M', got {freq!r}")
    return PERIODS[freq]


def excess(returns: pd.Series, rf: pd.Series | None = None) -> pd.Series:
    """Returns minus the risk-free return on the same dates (unchanged if ``rf`` is None);
    NaN rows are dropped."""
    r = returns.astype("float64")
    if rf is not None:
        r = r - rf.reindex(r.index).astype("float64")
    return r.dropna()


def monthly(returns: pd.Series) -> pd.Series:
    """Calendar-month compounded returns, indexed by month end."""
    r = returns.dropna()
    key = pd.DatetimeIndex(r.index).to_period("M")
    out = (1.0 + r).groupby(key).prod() - 1.0
    out.index = pd.PeriodIndex(out.index).to_timestamp(how="end").normalize()
    return out


def sharpe(returns: pd.Series, rf: pd.Series | None = None, freq: Freq = "D") -> float:
    """Annualised Sharpe ratio of excess returns."""
    p = _periods(freq)
    x = excess(returns, rf)
    return float(x.mean() / x.std(ddof=1) * math.sqrt(p))


def sortino(returns: pd.Series, rf: pd.Series | None = None, freq: Freq = "D") -> float:
    """Annualised Sortino ratio (target 0 on excess returns)."""
    p = _periods(freq)
    x = excess(returns, rf)
    downside = math.sqrt(float((np.minimum(x, 0.0) ** 2).mean()))
    return float(x.mean() / downside * math.sqrt(p)) if downside > 0 else math.nan


def annual_return(returns: pd.Series, freq: Freq = "D") -> float:
    """Compound annual growth rate, ``W^(P/n) − 1``."""
    p = _periods(freq)
    r = returns.dropna().to_numpy(dtype=np.float64)
    wealth = float(np.prod(1.0 + r))
    return float(wealth ** (p / len(r)) - 1.0)


def annual_vol(returns: pd.Series, freq: Freq = "D") -> float:
    """Sample standard deviation times √P."""
    return float(returns.dropna().std(ddof=1) * math.sqrt(_periods(freq)))


def drawdown_series(returns: pd.Series) -> pd.Series:
    """Wealth / running peak − 1 (≤ 0); the peak starts at the initial wealth of 1."""
    wealth = np.cumprod(1.0 + returns.fillna(0.0).to_numpy(dtype=np.float64))
    peak = np.maximum(np.maximum.accumulate(wealth), 1.0)
    return pd.Series(wealth / peak - 1.0, index=returns.index)


def max_drawdown(returns: pd.Series) -> float:
    """Largest drawdown as a negative decimal (−0.2 = −20%)."""
    return float(min(drawdown_series(returns).min(), 0.0))


def calmar(returns: pd.Series, freq: Freq = "D") -> float:
    """Annual return / |max drawdown| (NaN with no drawdown)."""
    mdd = max_drawdown(returns)
    return annual_return(returns, freq) / abs(mdd) if mdd < 0 else math.nan


def worst_month(returns: pd.Series) -> float:
    """Lowest calendar-month compounded return."""
    return float(monthly(returns).min())


def skew(returns: pd.Series) -> float:
    """Population skewness."""
    x = returns.dropna().to_numpy(dtype=np.float64)
    d = x - x.mean()
    return float((d**3).mean() / (d**2).mean() ** 1.5)


def kurt(returns: pd.Series) -> float:
    """Population kurtosis, raw (normal = 3)."""
    x = returns.dropna().to_numpy(dtype=np.float64)
    d = x - x.mean()
    return float((d**4).mean() / (d**2).mean() ** 2)


def nw_default_lags(n_obs: int) -> int:
    """Newey & West (1994) rule ``floor(4 (T/100)^(2/9))``."""
    return int(math.floor(4.0 * (n_obs / 100.0) ** (2.0 / 9.0)))


def newey_west_t(returns: pd.Series, lags: int | None = None) -> float:
    """t-statistic of the mean with Newey-West (HAC, Bartlett) standard errors."""
    y = returns.dropna().to_numpy(dtype=np.float64)
    lags = nw_default_lags(len(y)) if lags is None else lags
    fit = sm.OLS(y, np.ones((len(y), 1))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(fit.tvalues[0])


def lo_eta(q: int, rhos: Sequence[float]) -> float:
    """Lo (2002) scale factor ``q / sqrt(q + 2 Σ_{k=1}^{q-1} (q − k) ρ_k)``; ``rhos[k-1] = ρ_k``."""
    if len(rhos) != q - 1:
        raise ValueError(f"need q - 1 = {q - 1} autocorrelations, got {len(rhos)}")
    s = sum((q - k) * rho for k, rho in enumerate(rhos, start=1))
    return q / math.sqrt(q + 2.0 * s)


def lo_adjusted_sharpe(returns: pd.Series, rf: pd.Series | None = None, freq: Freq = "M") -> float:
    """Annual Sharpe with Lo's (2002) serial-correlation adjustment (q = 12 or 252)."""
    q = _periods(freq)
    x = excess(returns, rf)
    rhos = [float(x.autocorr(k)) for k in range(1, q)]
    return float(x.mean() / x.std(ddof=1)) * lo_eta(q, rhos)


def monthly_one_way_turnover(turnover: pd.Series) -> float:
    """Average monthly one-way turnover from daily ``Σ|Δw|`` (half the two-way sum)."""
    return float((monthly_sum(turnover) / 2.0).mean())


def monthly_sum(values: pd.Series) -> pd.Series:
    """Sum per calendar month."""
    return values.groupby(pd.DatetimeIndex(values.index).to_period("M")).sum()


def performance(
    returns: pd.Series,
    rf: pd.Series | None = None,
    freq: Freq = "D",
    turnover: pd.Series | None = None,
) -> Metrics:
    """The ledger's metric set (PLAN §7.5). Sharpe, Sortino and volatility are at ``freq``;
    the HAC t and Lo Sharpe use calendar-month *excess* returns (DECISIONS 012)."""
    r = returns.dropna()
    m_ret = monthly(r)
    m_x = m_ret - monthly(rf.reindex(r.index).fillna(0.0)) if rf is not None else m_ret
    return {
        "ann_ret": annual_return(r, freq),
        "ann_vol": annual_vol(r, freq),
        "sharpe": sharpe(r, rf, freq),
        "sharpe_hac_t": newey_west_t(m_x),
        "sharpe_lo": lo_adjusted_sharpe(m_x, freq="M") if len(m_x) > 12 else None,
        "sortino": sortino(r, rf, freq),
        "mdd": max_drawdown(r),
        "calmar": calmar(r, freq),
        "worst_month": float(m_ret.min()),
        "skew": skew(r),
        "kurt": kurt(r),
        "turnover_1way_monthly": None if turnover is None else monthly_one_way_turnover(turnover),
        "n_months": len(m_ret),
    }
