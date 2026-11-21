"""D-5 on the real daily panel: every rebalance date is a date in the panel."""

import pandas as pd
import pytest

from momlab import paths
from momlab.data.calendar import TradingCalendar

pytestmark = pytest.mark.data


def test_rebalance_dates_are_panel_dates() -> None:
    panel = pd.read_parquet(paths.PROCESSED_DIR / "industry_daily.parquet", columns=["date"])
    cal = TradingCalendar.from_panel(panel)
    reb = cal.month_end_rebalance_dates()
    assert reb.isin(cal.days).all()
    # One rebalance per calendar month from 1926-07 to the last complete month.
    months = reb.to_period("M")
    assert months.is_unique
    assert months[0] == pd.Period("1926-07", "M")
    assert len(reb) == len(pd.period_range(months[0], months[-1], freq="M"))
