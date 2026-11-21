"""D-5: trading calendar and month-end rebalance dates (expected dates written by hand)."""

import pandas as pd
import pytest

from momlab.data.calendar import TradingCalendar


def _weekdays(start: str, end: str, holidays: tuple[str, ...] = ()) -> pd.DatetimeIndex:
    days = pd.bdate_range(start, end)
    return days.difference(pd.DatetimeIndex(pd.to_datetime(list(holidays))))


def test_month_end_on_weekend() -> None:
    # 2023-09-30 is a Saturday -> last trading day of September is Friday 2023-09-29.
    cal = TradingCalendar(_weekdays("2023-08-01", "2023-10-31", holidays=("2023-09-04",)))
    assert list(cal.month_end_rebalance_dates()) == [
        pd.Timestamp("2023-08-31"),
        pd.Timestamp("2023-09-29"),
        pd.Timestamp("2023-10-31"),
    ]


def test_month_end_on_holiday() -> None:
    # Good Friday 2018-03-30 (market closed) -> last trading day of March is 2018-03-29.
    cal = TradingCalendar(_weekdays("2018-03-01", "2018-04-30", holidays=("2018-03-30",)))
    assert list(cal.month_end_rebalance_dates()) == [
        pd.Timestamp("2018-03-29"),
        pd.Timestamp("2018-04-30"),
    ]


def test_short_months() -> None:
    # February 2023 ends Tuesday the 28th; leap-year February 2024 ends Thursday the 29th.
    cal = TradingCalendar(_weekdays("2023-02-01", "2023-03-31"))
    assert cal.month_end_rebalance_dates()[0] == pd.Timestamp("2023-02-28")
    cal = TradingCalendar(_weekdays("2024-02-01", "2024-03-31"))
    assert cal.month_end_rebalance_dates()[0] == pd.Timestamp("2024-02-29")


def test_saturday_sessions_count() -> None:
    # 1950-09-30 was a Saturday session (NYSE traded Saturdays until 1952).
    days = pd.DatetimeIndex(
        pd.to_datetime(["1950-09-28", "1950-09-29", "1950-09-30", "1950-10-02"])
    )
    cal = TradingCalendar(days, drop_incomplete_last_month=False)
    assert cal.month_end_rebalance_dates()[0] == pd.Timestamp("1950-09-30")


def test_incomplete_last_month_is_dropped() -> None:
    # Panel stops on Wednesday 2023-10-18: October's last trading day is unknown.
    cal = TradingCalendar(_weekdays("2023-09-01", "2023-10-18"))
    assert list(cal.month_end_rebalance_dates()) == [pd.Timestamp("2023-09-29")]
    cal = TradingCalendar(_weekdays("2023-09-01", "2023-10-18"), drop_incomplete_last_month=False)
    assert list(cal.month_end_rebalance_dates())[-1] == pd.Timestamp("2023-10-18")


def test_range_filter() -> None:
    cal = TradingCalendar(_weekdays("2023-01-01", "2023-06-30"))
    got = cal.month_end_rebalance_dates(start="2023-03-01", end="2023-04-30")
    assert list(got) == [pd.Timestamp("2023-03-31"), pd.Timestamp("2023-04-28")]


def test_nth_trading_day() -> None:
    # September 2023 trading days: Sep 1 (Fri), Labor Day Sep 4 closed, then Sep 5, 6, 7, 8, 11,
    # 12, 13, 14, 15 -> the 10th trading day is Friday 2023-09-15.
    # October 2023: Oct 2-6 and 9-13 -> the 10th is Friday 2023-10-13.
    cal = TradingCalendar(_weekdays("2023-09-01", "2023-10-31", holidays=("2023-09-04",)))
    tenth = cal.nth_trading_day(10)
    assert tenth[0] == pd.Timestamp("2023-09-15")
    assert tenth[1] == pd.Timestamp("2023-10-13")
    assert cal.nth_trading_day(1)[0] == pd.Timestamp("2023-09-01")
    assert list(cal.nth_trading_day(-1)) == list(cal.month_end_rebalance_dates())
    with pytest.raises(ValueError, match="n must not be 0"):
        cal.nth_trading_day(0)


def test_nth_skips_months_that_are_too_short() -> None:
    cal = TradingCalendar(_weekdays("2023-09-01", "2023-10-03"), drop_incomplete_last_month=False)
    # No holiday here: Sep 1, 4, 5, 6, 7 -> 5th is 2023-09-07. October has only 2 trading days
    # in this panel (Oct 2 and 3), so it is skipped.
    assert list(cal.nth_trading_day(5)) == [pd.Timestamp("2023-09-07")]


def test_is_rebalance_date_and_validation() -> None:
    cal = TradingCalendar(_weekdays("2023-09-01", "2023-10-31"))
    assert cal.is_rebalance_date(pd.Timestamp("2023-09-29"))
    assert not cal.is_rebalance_date(pd.Timestamp("2023-09-28"))
    with pytest.raises(ValueError, match="strictly increasing"):
        TradingCalendar(pd.DatetimeIndex(pd.to_datetime(["2023-01-03", "2023-01-02"])))


def test_from_panel() -> None:
    panel = pd.DataFrame(
        {"date": pd.to_datetime(["2023-09-28", "2023-09-28", "2023-09-29", "2023-10-02"])}
    )
    cal = TradingCalendar.from_panel(panel)
    assert list(cal.days) == list(pd.to_datetime(["2023-09-28", "2023-09-29", "2023-10-02"]))
