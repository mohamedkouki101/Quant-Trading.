"""Rule signals (task E-5): B1 equal weight, B3 12-1 momentum, B5 1-month signal.

B4 is B3 plus the vol-targeting risk rule (``momlab.risk.VolTargetRisk``); the signal is the
same. Every signal reads data only through ``AsOfView`` and emits only on month-end rebalance
dates. Long-short signals hold the top ``n`` and bottom ``n`` assets by score with weights
+1/n and −1/n (gross 2, net 0); fewer than ``2n`` valid assets means cash (all zeros).
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from momlab.data.calendar import TradingCalendar
from momlab.data.handler import AsOfView
from momlab.events import MarketEvent, SignalEvent

FloatArray = npt.NDArray[np.float64]


def momentum_score(view: AsOfView, lookback_months: int, skip_months: int) -> FloatArray | None:
    """Cumulative return over the lookback window, skipping the most recent months.

    At the end of month M (holding month t = M + 1) the window is months
    ``M − lookback + 1 … M − skip``; for 12-1 that is t−12 … t−2 (leakage item L2). Month
    returns are compounded from daily returns in the view. An asset with a missing month in the
    window scores NaN (rule 3). Returns None until ``lookback`` months of history exist.
    """
    if skip_months >= lookback_months:
        raise ValueError("skip_months must be smaller than lookback_months")
    months = view.month_returns(lookback_months)
    if months.shape[0] < lookback_months:
        return None
    window = months[: lookback_months - skip_months]
    return np.prod(1.0 + window, axis=0) - 1.0


def long_short_weights(score: FloatArray, n_per_leg: int) -> FloatArray:
    """+1/n on the n highest scores, −1/n on the n lowest; NaN scores are never held.
    Ties keep asset order (stable sort). Fewer than 2n valid scores gives all zeros."""
    w = np.zeros(score.shape[0])
    valid = np.flatnonzero(~np.isnan(score))
    if valid.size < 2 * n_per_leg:
        return w
    order = valid[np.argsort(-score[valid], kind="stable")]
    w[order[:n_per_leg]] = 1.0 / n_per_leg
    w[order[-n_per_leg:]] = -1.0 / n_per_leg
    return w


class _MonthEndSignal:
    def __init__(self, calendar: TradingCalendar) -> None:
        self._rebalance = set(calendar.month_end_rebalance_dates())


class MomentumSignal(_MonthEndSignal):
    """B3 (12, 1), B5 (1, 0) and any lookback/skip; ``sign=-1`` reverses the ranking."""

    def __init__(
        self,
        calendar: TradingCalendar,
        lookback_months: int,
        skip_months: int,
        n_per_leg: int,
        sign: int = 1,
    ) -> None:
        super().__init__(calendar)
        self.lookback_months = lookback_months
        self.skip_months = skip_months
        self.n_per_leg = n_per_leg
        self.sign = sign

    def on_market(self, ev: MarketEvent, view: AsOfView) -> SignalEvent | None:
        """Emit the target on rebalance dates once enough history exists."""
        if ev.ts not in self._rebalance:
            return None
        score = momentum_score(view, self.lookback_months, self.skip_months)
        if score is None:
            return None
        return SignalEvent(ts=ev.ts, weights=long_short_weights(self.sign * score, self.n_per_leg))


class EqualWeightSignal(_MonthEndSignal):
    """B1: equal weight across assets with a return on the rebalance day (long only)."""

    def on_market(self, ev: MarketEvent, view: AsOfView) -> SignalEvent | None:
        """Emit 1/N weights on rebalance dates."""
        if ev.ts not in self._rebalance:
            return None
        valid = ~np.isnan(view.returns(lookback=1)[-1])
        w = np.zeros(valid.shape[0])
        if valid.any():
            w[valid] = 1.0 / valid.sum()
        return SignalEvent(ts=ev.ts, weights=w)
