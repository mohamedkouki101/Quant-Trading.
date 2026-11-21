"""Research and locked-test period boundaries, fixed in PREREGISTRATION.md §2.

Policy for data-integrity checks (Kouki, 2026-11-09, DECISIONS 009): checks run on all dates,
but for dates from ``TEST_START`` on only aggregate counts are reported; row-level lists, values
and plots are restricted to the research period.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
import pandas as pd

RESEARCH_START = pd.Timestamp("1926-07-01")
RESEARCH_END = pd.Timestamp("2005-12-31")
TEST_START = pd.Timestamp("2006-01-01")
TEST_END = pd.Timestamp("2026-09-30")
#: First month-end with a 12-1 signal (the lookback needs 12 months of returns).
FIRST_SIGNAL_MONTH = pd.Timestamp("1927-07-31")


def in_research(dates: pd.DatetimeIndex | pd.Series) -> npt.NDArray[np.bool_]:
    """Boolean mask: True for dates before ``TEST_START`` (the research period)."""
    return np.asarray(pd.DatetimeIndex(dates) < TEST_START, dtype=bool)
