"""Research / locked-test period boundaries (PREREGISTRATION.md §2)."""

import pandas as pd

from momlab import periods


def test_boundaries_match_preregistration() -> None:
    assert periods.RESEARCH_START == pd.Timestamp("1926-07-01")
    assert periods.RESEARCH_END == pd.Timestamp("2005-12-31")
    assert periods.TEST_START == pd.Timestamp("2006-01-01")
    assert periods.TEST_END == pd.Timestamp("2026-09-30")
    assert periods.FIRST_SIGNAL_MONTH == pd.Timestamp("1927-07-31")


def test_in_research() -> None:
    d = pd.to_datetime(["2005-12-30", "2005-12-31", "2006-01-02", "2010-05-31"])
    assert periods.in_research(d).tolist() == [True, True, False, False]
    assert periods.in_research(pd.Series(d)).tolist() == [True, True, False, False]
