"""Trading-day calendar built from the daily panel (task D-5).

The clock of the engine is the set of dates in the Ken French daily panel (PLAN §3.2), so
holidays, Saturday sessions before 1952 and market closures are whatever the data says. The
monthly rebalance date is the last trading day of each calendar month.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


class TradingCalendar:
    """Trading days and month-based rebalance dates.

    Parameters
    ----------
    days:
        Trading days, strictly increasing and unique.
    drop_incomplete_last_month:
        If True (default), the final month is dropped from month-based schedules unless the
        panel's last day is followed by a weekday in the next month (i.e. the month looks
        complete). A panel that stops mid-month must not invent a month-end rebalance. A
        holiday on the last weekday of the final month makes that month look incomplete, which
        only drops a rebalance; it never adds one.
    """

    def __init__(self, days: pd.DatetimeIndex, *, drop_incomplete_last_month: bool = True) -> None:
        idx = pd.DatetimeIndex(days)
        if len(idx) > 1 and not bool((idx[1:] > idx[:-1]).all()):
            raise ValueError("trading days must be strictly increasing and unique")
        self.days: pd.DatetimeIndex = idx
        self._drop_last = drop_incomplete_last_month

    @classmethod
    def from_panel(cls, panel: pd.DataFrame, **kwargs: Any) -> TradingCalendar:
        """Calendar from the unique ``date`` values of a long panel."""
        days = pd.DatetimeIndex(pd.Series(panel["date"]).drop_duplicates().sort_values())
        return cls(days, **kwargs)

    def _months(self) -> pd.Series:
        """Map each trading day to its calendar month, minus an incomplete final month."""
        months = pd.Series(self.days.to_period("M"), index=self.days)
        if self._drop_last and len(self.days):
            last = self.days[-1]
            next_weekday = last + pd.offsets.BDay(1)
            if next_weekday.to_period("M") == last.to_period("M"):
                months = months[months != last.to_period("M")]
        return months

    def nth_trading_day(self, n: int) -> pd.DatetimeIndex:
        """The ``n``-th trading day of each month (``n=1`` first, ``n=-1`` last).

        Months with fewer than ``|n|`` trading days are skipped.
        """
        if n == 0:
            raise ValueError("n must not be 0 (use 1 for the first day, -1 for the last)")
        out = []
        for _, group in self._months().groupby(self._months(), sort=True):
            days = group.index
            if len(days) >= abs(n):
                out.append(days[n - 1] if n > 0 else days[n])
        return pd.DatetimeIndex(out, name="date")

    def month_end_rebalance_dates(
        self, start: str | pd.Timestamp | None = None, end: str | pd.Timestamp | None = None
    ) -> pd.DatetimeIndex:
        """Last trading day of each month, optionally limited to ``start <= date <= end``."""
        dates = self.nth_trading_day(-1)
        if start is not None:
            dates = dates[dates >= pd.Timestamp(start)]
        if end is not None:
            dates = dates[dates <= pd.Timestamp(end)]
        return dates

    def is_rebalance_date(self, ts: pd.Timestamp) -> bool:
        """True when ``ts`` is a month-end rebalance date."""
        return bool(ts in set(self.nth_trading_day(-1)))
