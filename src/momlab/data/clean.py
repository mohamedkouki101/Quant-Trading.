"""Cleaning and validation rules from PLAN §5.3 (tasks D-2 and D-3).

Each rule is a named function that returns a :class:`RuleReport`. Rules that find a hard error
raise :class:`DataValidationError`; rules that only find things to review (missing returns,
outliers) report them and never change the data.

Wide frames here have a ``DatetimeIndex`` (dates) and one column per asset; values are simple
decimal returns (0.01 = 1%) unless stated otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
import pandas as pd

#: Ken French missing-value codes ("Missing data are indicated by -99.99 or -999").
MISSING_CODES: tuple[float, ...] = (-99.99, -999.0)
#: Last date on which a Saturday session is accepted (NYSE Saturday trading ended in 1952).
LAST_SATURDAY_SESSION = pd.Timestamp("1952-05-31")


class DataValidationError(ValueError):
    """A dataset breaks a hard cleaning rule."""


@dataclass(frozen=True)
class RuleReport:
    """Outcome of one cleaning rule: its name, whether it passed and what it found."""

    rule: str
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)


def rule1_missing_codes(wide: pd.DataFrame, *, percent: bool) -> tuple[pd.DataFrame, RuleReport]:
    """Rule 1: replace -99.99 and -999 with NaN; divide by 100 when values are in percent.

    Returns a new frame (the input is not modified) and a report with the number of codes found.
    Counts and sizes (``percent=False``) are only cleaned of codes, never rescaled.
    """
    is_code = wide.isin(list(MISSING_CODES))
    out = wide.mask(is_code)
    if percent:
        out = out / 100.0
    n = int(is_code.to_numpy().sum())
    return out, RuleReport("rule1_missing_codes", True, {"n_missing_codes": n, "percent": percent})


def rule2_dates(index: pd.DatetimeIndex, freq: Literal["D", "M"]) -> RuleReport:
    """Rule 2: dates strictly increasing and unique; monthly dates are consecutive month-ends;
    daily dates are trading days (no Sundays, Saturdays only up to 1952-05-31).

    Raises ``DataValidationError`` on the first violation.
    """
    if len(index) > 1 and not bool((index[1:] > index[:-1]).all()):
        raise DataValidationError("dates are not strictly increasing and unique")
    details: dict[str, Any] = {"n_dates": len(index)}
    if len(index):
        details["first_date"] = index[0].date().isoformat()
        details["last_date"] = index[-1].date().isoformat()
    if freq == "M":
        if not bool(index.is_month_end.all()):
            raise DataValidationError("monthly dates must be month-ends")
        periods = index.to_period("M")
        steps = np.diff(periods.asi8)
        if len(steps) and not bool((steps == 1).all()):
            raise DataValidationError("monthly dates have a gap (a missing month)")
    else:
        weekday = index.day_of_week
        if bool((weekday == 6).any()):
            raise DataValidationError("daily dates include a Sunday")
        late_saturday = (weekday == 5) & (index > LAST_SATURDAY_SESSION)
        if bool(late_saturday.any()):
            raise DataValidationError("daily dates include a Saturday after May 1952")
        details["n_saturdays"] = int((weekday == 5).sum())
    return RuleReport("rule2_dates", True, details)


def rule3_missing_returns(wide: pd.DataFrame) -> RuleReport:
    """Rule 3: report missing returns per asset. Missing returns are never forward-filled;
    consumers exclude an asset from any rebalance whose lookback window contains a NaN.
    """
    by_asset = wide.isna().sum()
    missing = {str(k): int(v) for k, v in by_asset.items() if v > 0}
    return RuleReport(
        "rule3_missing_returns",
        True,
        {"n_missing": int(by_asset.sum()), "missing_by_asset": missing},
    )


def rule5_flag_outliers(
    wide: pd.DataFrame, lo: float = -0.5, hi: float = 1.0
) -> tuple[pd.DataFrame, RuleReport]:
    """Rule 5: flag returns outside ``[lo, hi]`` for review. Values are never clipped.

    Returns a frame of flags (``date``, ``asset``, ``ret``) in date then column order.
    """
    arr = wide.to_numpy()
    with np.errstate(invalid="ignore"):
        hit = (arr < lo) | (arr > hi)
    rows, cols = np.nonzero(hit)
    flags = pd.DataFrame(
        {
            "date": wide.index[rows],
            "asset": wide.columns[cols].astype(str),
            "ret": arr[rows, cols],
        }
    )
    return flags, RuleReport(
        "rule5_flag_outliers", True, {"n_flagged": len(flags), "lo": lo, "hi": hi}
    )


def rule4_reconcile(
    daily: pd.DataFrame, monthly: pd.DataFrame, tol: float = 1e-4, min_share: float = 0.995
) -> tuple[pd.DataFrame, RuleReport]:
    """Rule 4: compound daily returns to calendar months and compare with the monthly file.

    ``daily`` and ``monthly`` are wide frames of simple decimal returns with the same asset
    columns. A month with any missing day has no compounded value (returns are never filled).
    Returns a long table (``asset, month, daily_compounded, monthly, difference``, difference =
    daily minus monthly) over the months both files cover, and a report. An industry-month is
    *compared* unless both sides are missing; it is *within tolerance* when both sides exist and
    ``|difference| <= tol``. The rule passes when the within share is at least ``min_share``.
    """
    month_key = pd.DatetimeIndex(daily.index) + pd.offsets.MonthEnd(0)
    growth = (1.0 + daily).groupby(month_key)
    compounded = growth.prod(min_count=1) - 1.0
    complete = daily.notna().groupby(month_key).all()
    compounded = compounded.where(complete)
    months = compounded.index.intersection(monthly.index)
    comp = compounded.loc[months, list(monthly.columns)]
    mon = monthly.loc[months]
    table = pd.DataFrame(
        {
            "asset": np.repeat(np.asarray(mon.columns, dtype=object), len(months)),
            "month": np.tile(months.to_numpy(), len(mon.columns)),
            "daily_compounded": comp.to_numpy().T.ravel(),
            "monthly": mon.to_numpy().T.ravel(),
        }
    )
    table["difference"] = table["daily_compounded"] - table["monthly"]
    d_na = table["daily_compounded"].isna()
    m_na = table["monthly"].isna()
    both = d_na & m_na
    one = d_na ^ m_na
    within = (~d_na & ~m_na) & (table["difference"].abs() <= tol)
    n_compared = int((~both).sum())
    share = float(within.sum() / n_compared) if n_compared else 1.0
    details = {
        "tol": tol,
        "min_share": min_share,
        "n_months": len(months),
        "first_month": months[0].date().isoformat() if len(months) else None,
        "last_month": months[-1].date().isoformat() if len(months) else None,
        "n_compared": n_compared,
        "n_within_tol": int(within.sum()),
        "n_outside_tol": int((~both & ~one & ~within).sum()),
        "n_one_side_missing": int(one.sum()),
        "n_both_missing": int(both.sum()),
        "share_within_tol": share,
        "max_abs_difference": float(table["difference"].abs().max()) if n_compared else 0.0,
    }
    return table, RuleReport("rule4_reconcile", share >= min_share, details)


_COUNT_KEYS = (
    "n_compared",
    "n_within_tol",
    "n_outside_tol",
    "n_one_side_missing",
    "n_both_missing",
)


def reconcile_panels(
    daily: pd.DataFrame,
    monthly: pd.DataFrame,
    tol: float = 1e-4,
    min_share: float = 0.995,
    row_level_before: pd.Timestamp | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run rule 4 on long panels (``date, asset, weighting, ret``) for each weighting.

    Returns the row-level table (``weighting, asset, month, daily_compounded, monthly,
    difference, within_tol``) for months before ``row_level_before`` (default: the locked test
    start); every mismatch is a row with ``within_tol`` False. The summary holds full details
    for the research period, counts only for the test period (DECISIONS 009), the number of
    research mismatches with the 20 largest, and the criterion as written (all dates, all
    weightings) under ``overall``.
    """
    from momlab import periods  # local import keeps the cleaning rules free of project config

    cutoff = periods.TEST_START if row_level_before is None else row_level_before
    summary: dict[str, Any] = {"tol": tol, "min_share": min_share}
    rows = []
    n_comp = n_within = 0
    for w in ("vw", "ew"):
        dw = daily[daily["weighting"] == w].pivot(index="date", columns="asset", values="ret")  # noqa: PD010
        mw = monthly[monthly["weighting"] == w].pivot(  # noqa: PD010
            index="date", columns="asset", values="ret"
        )
        early_d, early_m = dw[dw.index < cutoff], mw[mw.index < cutoff]
        late_d, late_m = dw[dw.index >= cutoff], mw[mw.index >= cutoff]
        table, rep_r = rule4_reconcile(early_d, early_m, tol, min_share)
        _, rep_t = rule4_reconcile(late_d, late_m, tol, min_share)
        table.insert(0, "weighting", w)
        rows.append(table)
        summary[w] = {
            "research": rep_r.details,
            "test_period": {k: rep_t.details[k] for k in _COUNT_KEYS},
        }
        for rep in (rep_r, rep_t):
            n_comp += rep.details["n_compared"]
            n_within += rep.details["n_within_tol"]
    out = pd.concat(rows, ignore_index=True)
    out["within_tol"] = out["difference"].abs() <= tol
    compared = out[~(out["daily_compounded"].isna() & out["monthly"].isna())]
    bad = compared[~compared["within_tol"]].copy()
    bad["month"] = pd.DatetimeIndex(bad["month"]).strftime("%Y-%m")
    bad["abs_difference"] = bad["difference"].abs()
    summary["n_research_mismatches"] = len(bad)
    top = bad.sort_values("abs_difference", ascending=False, kind="stable").head(20)
    summary["largest_research_mismatches"] = top.drop(columns="abs_difference").to_dict("records")
    share = n_within / n_comp if n_comp else 1.0
    summary["overall"] = {
        "n_compared": n_comp,
        "n_within_tol": n_within,
        "share_within_tol": share,
        "passed": share >= min_share,
    }
    return out, summary
