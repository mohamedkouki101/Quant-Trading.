"""D-2: PLAN §5.3 cleaning rules, each a named function returning a report."""

import math

import numpy as np
import pandas as pd
import pytest

from momlab.data import clean


def _wide(values: list[list[float]], dates: list[str]) -> pd.DataFrame:
    return pd.DataFrame(values, index=pd.DatetimeIndex(pd.to_datetime(dates)), columns=["A", "B"])


def test_rule1_missing_codes_and_percent() -> None:
    raw = _wide([[1.0, -99.99], [-999.0, 2.5]], ["2023-01-31", "2023-02-28"])
    out, rep = clean.rule1_missing_codes(raw, percent=True)
    assert rep.rule == "rule1_missing_codes" and rep.passed
    assert rep.details["n_missing_codes"] == 2
    assert out.iloc[0, 0] == pytest.approx(0.01, abs=1e-15)
    assert out.iloc[1, 1] == pytest.approx(0.025, abs=1e-15)
    assert math.isnan(out.iloc[0, 1]) and math.isnan(out.iloc[1, 0])
    # Input is not modified.
    assert raw.iloc[0, 1] == -99.99


def test_rule1_counts_not_scaled() -> None:
    out, _ = clean.rule1_missing_codes(_wide([[3.0, 40.0]], ["2023-01-31"]), percent=False)
    assert out.iloc[0].tolist() == [3.0, 40.0]


def test_rule2_monthly_ok_and_failures() -> None:
    idx = pd.DatetimeIndex(pd.to_datetime(["2023-01-31", "2023-02-28", "2023-03-31"]))
    assert clean.rule2_dates(idx, "M").passed
    with pytest.raises(clean.DataValidationError, match="month-end"):
        clean.rule2_dates(pd.DatetimeIndex(pd.to_datetime(["2023-01-30"])), "M")
    with pytest.raises(clean.DataValidationError, match="gap"):
        clean.rule2_dates(pd.DatetimeIndex(pd.to_datetime(["2023-01-31", "2023-03-31"])), "M")
    with pytest.raises(clean.DataValidationError, match="strictly increasing"):
        clean.rule2_dates(pd.DatetimeIndex(pd.to_datetime(["2023-02-28", "2023-01-31"])), "M")
    with pytest.raises(clean.DataValidationError, match="strictly increasing"):
        clean.rule2_dates(pd.DatetimeIndex(pd.to_datetime(["2023-01-31", "2023-01-31"])), "M")


def test_rule2_daily_weekends() -> None:
    # 1950-01-07 was a Saturday (NYSE traded Saturdays until 1952): allowed.
    ok = pd.DatetimeIndex(pd.to_datetime(["1950-01-06", "1950-01-07", "1950-01-09"]))
    rep = clean.rule2_dates(ok, "D")
    assert rep.details["n_saturdays"] == 1
    # 2023-01-07 is a Saturday after 1952: not a trading day.
    with pytest.raises(clean.DataValidationError, match="Saturday"):
        clean.rule2_dates(pd.DatetimeIndex(pd.to_datetime(["2023-01-06", "2023-01-07"])), "D")
    # 2023-01-08 is a Sunday: never a trading day.
    with pytest.raises(clean.DataValidationError, match="Sunday"):
        clean.rule2_dates(pd.DatetimeIndex(pd.to_datetime(["2023-01-06", "2023-01-08"])), "D")


def test_rule3_reports_missing_and_never_fills() -> None:
    w = _wide(
        [[0.01, np.nan], [np.nan, np.nan], [0.02, 0.03]], ["2023-01-31", "2023-02-28", "2023-03-31"]
    )
    rep = clean.rule3_missing_returns(w)
    assert rep.details["n_missing"] == 3
    assert rep.details["missing_by_asset"] == {"A": 1, "B": 2}
    assert int(w.isna().sum().sum()) == 3  # still NaN: nothing was filled


def test_rule5_flags_without_clipping() -> None:
    w = _wide([[0.01, 1.5], [-0.6, 0.2]], ["2023-01-03", "2023-01-04"])
    flags, rep = clean.rule5_flag_outliers(w, lo=-0.5, hi=1.0)
    assert rep.details["n_flagged"] == 2
    assert flags[["asset", "ret"]].to_numpy().tolist() == [["B", 1.5], ["A", -0.6]]
    assert w.iloc[0, 1] == 1.5  # not clipped
    assert rep.passed  # flags are for review, they do not fail the build


def test_rule4_reconcile_hand_example() -> None:
    days = pd.to_datetime(["2023-01-30", "2023-01-31", "2023-02-01", "2023-02-28"])
    daily = pd.DataFrame(
        {
            # Jan: 1.01 * 1.02 - 1 = 0.0302 ; Feb: 0.99 * 1.00 - 1 = -0.01
            "A": [0.01, 0.02, -0.01, 0.0],
            # Jan has a missing day -> no compounded value ; Feb: 1.05 * 0.98 - 1 = 0.029
            "B": [np.nan, 0.03, 0.05, -0.02],
        },
        index=pd.DatetimeIndex(days),
    )
    monthly = pd.DataFrame(
        {"A": [0.0302, -0.00995], "B": [0.033, 0.029]},
        index=pd.DatetimeIndex(pd.to_datetime(["2023-01-31", "2023-02-28"])),
    )
    table, rep = clean.rule4_reconcile(daily, monthly, tol=1e-4)
    assert list(table.columns) == ["asset", "month", "daily_compounded", "monthly", "difference"]
    a = table[table["asset"] == "A"].set_index("month")
    assert a.loc["2023-01-31", "daily_compounded"] == pytest.approx(0.0302, abs=1e-15)
    # Feb A: -0.01 vs -0.00995 -> difference (daily minus monthly) -0.00005, within 1e-4.
    assert a.loc["2023-02-28", "difference"] == pytest.approx(-0.00005, abs=1e-15)
    b = table[table["asset"] == "B"].set_index("month")
    assert math.isnan(b.loc["2023-01-31", "daily_compounded"])
    assert rep.details["n_compared"] == 4
    assert rep.details["n_within_tol"] == 3  # A Jan, A Feb, B Feb
    assert rep.details["n_one_side_missing"] == 1  # B Jan
    assert rep.details["share_within_tol"] == pytest.approx(0.75)
    assert rep.passed is False  # 75% < 99.5%


def test_rule4_both_missing_not_compared() -> None:
    idx_d = pd.DatetimeIndex(pd.to_datetime(["2023-01-31"]))
    idx_m = pd.DatetimeIndex(pd.to_datetime(["2023-01-31"]))
    daily = pd.DataFrame({"A": [np.nan], "B": [0.01]}, index=idx_d)
    monthly = pd.DataFrame({"A": [np.nan], "B": [0.01]}, index=idx_m)
    _, rep = clean.rule4_reconcile(daily, monthly)
    assert rep.details["n_compared"] == 1
    assert rep.details["n_both_missing"] == 1
    assert rep.passed is True


def _long(dates: list[str], rets: dict[str, list[float]], weighting: str) -> pd.DataFrame:
    rows = [
        {"date": pd.Timestamp(d), "asset": a, "weighting": weighting, "ret": r[i]}
        for a, r in rets.items()
        for i, d in enumerate(dates)
    ]
    return pd.DataFrame(rows)


def test_reconcile_panels_hides_test_period_rows() -> None:
    days = ["2005-12-29", "2005-12-30", "2006-01-30", "2006-01-31"]
    # A: Dec 1.01*1.01-1 = 0.0201 ; Jan 1.02*0.99-1 = 0.0098
    daily = pd.concat([_long(days, {"A": [0.01, 0.01, 0.02, -0.01]}, w) for w in ("vw", "ew")])
    monthly = pd.concat(
        [_long(["2005-12-31", "2006-01-31"], {"A": [0.0201, 0.0500]}, w) for w in ("vw", "ew")]
    )
    rows, summary = clean.reconcile_panels(daily, monthly, tol=1e-4, min_share=0.995)
    # Row-level output covers the research period only.
    assert rows["month"].tolist() == [pd.Timestamp("2005-12-31")] * 2
    assert rows["weighting"].tolist() == ["vw", "ew"]
    assert summary["vw"]["research"]["n_within_tol"] == 1
    # Test period: counts only, no values.
    assert summary["vw"]["test_period"] == {
        "n_compared": 1,
        "n_within_tol": 0,
        "n_outside_tol": 1,
        "n_one_side_missing": 0,
        "n_both_missing": 0,
    }
    assert summary["n_research_mismatches"] == 0
    assert summary["largest_research_mismatches"] == []
    assert rows["within_tol"].tolist() == [True, True]
    # Criterion as written: all dates, all weightings -> 2 of 4 within -> fails.
    assert summary["overall"] == {
        "n_compared": 4,
        "n_within_tol": 2,
        "share_within_tol": 0.5,
        "passed": False,
    }
