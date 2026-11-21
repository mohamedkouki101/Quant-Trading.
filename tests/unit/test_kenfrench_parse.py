"""D-2: Ken French CSV parsing on hand-written fixtures (expected values typed in by hand)."""

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momlab.data import kenfrench as kf

FIX = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture
def monthly_text() -> str:
    return (FIX / "kf_sample.csv").read_bytes().decode("latin-1")


@pytest.fixture
def daily_text() -> str:
    return (FIX / "kf_sample_daily.csv").read_bytes().decode("latin-1")


def test_kenfrench_parse_lists_blocks(monthly_text: str) -> None:
    blocks = kf.split_blocks(monthly_text)
    titles = [(b.title, b.freq, len(b.rows)) for b in blocks]
    assert titles == [
        ("Average Value Weighted Returns -- Monthly", "M", 4),
        ("Average Equal Weighted Returns -- Monthly", "M", 4),
        ("Average Value Weighted Returns -- Annual", "A", 1),
        ("Number of Firms in Portfolios", "M", 4),
        ("Average Firm Size", "M", 4),
        ("Sum of BE / Sum of ME", "A", 1),
    ]
    # Trailing spaces in Ken French headers are stripped.
    assert blocks[0].columns == ["Agric", "Food", "Fun"]


def test_kenfrench_parse_monthly_returns(monthly_text: str) -> None:
    wide = kf.read_block(monthly_text, "Average Value Weighted Returns -- Monthly", percent=True)
    assert list(wide.columns) == ["Agric", "Food", "Fun"]
    # Month-end dates.
    assert list(wide.index) == [
        pd.Timestamp("2023-01-31"),
        pd.Timestamp("2023-02-28"),
        pd.Timestamp("2023-03-31"),
        pd.Timestamp("2023-04-30"),
    ]
    # Decimals, not percents: 1.00% -> 0.01, -2.50% -> -0.025, 10.00% -> 0.10.
    assert wide.loc["2023-01-31", "Agric"] == pytest.approx(0.01, abs=1e-15)
    assert wide.loc["2023-01-31", "Food"] == pytest.approx(-0.025, abs=1e-15)
    assert wide.loc["2023-02-28", "Food"] == pytest.approx(0.10, abs=1e-15)
    # NaN where the -99.99 and -999 codes were.
    assert math.isnan(wide.loc["2023-01-31", "Fun"])
    assert math.isnan(wide.loc["2023-03-31", "Food"])
    assert int(wide.isna().sum().sum()) == 2
    # 0.00 is a real zero return, not missing.
    assert wide.loc["2023-04-30", "Fun"] == 0.0


def test_kenfrench_parse_daily_dates(daily_text: str) -> None:
    wide = kf.read_block(daily_text, "Average Value Weighted Returns -- Daily", percent=True)
    assert list(wide.index) == list(
        pd.to_datetime(["2023-01-30", "2023-01-31", "2023-02-01", "2023-02-28", "2023-03-01"])
    )
    assert math.isnan(wide.iloc[0, 2]) and math.isnan(wide.iloc[1, 2])
    assert wide.iloc[2, 1] == pytest.approx(1.50, abs=1e-15)


def test_kenfrench_parse_counts_are_not_scaled(monthly_text: str) -> None:
    nf = kf.read_block(monthly_text, "Number of Firms in Portfolios", percent=False)
    assert nf.loc["2023-02-28"].tolist() == [4.0, 41.0, 5.0]
    size = kf.read_block(monthly_text, "Average Firm Size", percent=False)
    assert size.loc["2023-01-31", "Agric"] == 99.80
    assert math.isnan(size.loc["2023-01-31", "Fun"])


def test_kenfrench_parse_factor_file_picks_first_block() -> None:
    text = (FIX / "kf_factor_sample.csv").read_bytes().decode("latin-1")
    wide = kf.read_first_block(text, freq="M", percent=True)
    assert list(wide.columns) == ["Mom"]
    assert wide["Mom"].iloc[0] == pytest.approx(0.015, abs=1e-15)
    assert math.isnan(wide["Mom"].iloc[1])
    assert len(wide) == 3


def test_missing_block_raises(monthly_text: str) -> None:
    with pytest.raises(kf.ParseError, match="no block"):
        kf.read_block(monthly_text, "Average Value Weighted Returns -- Daily", percent=True)


def test_ragged_row_raises() -> None:
    bad = "  T -- Monthly\r\n,A,B\r\n202301, 1.0\r\n"
    with pytest.raises(kf.ParseError, match="columns"):
        kf.split_blocks(bad)


def test_crsp_vintage() -> None:
    assert kf.crsp_vintage("This file was created using the 202609 CRSP database.\n") == "202609"
    assert kf.crsp_vintage("no vintage here") == "unknown"


def test_build_industry_panels(monthly_text: str, daily_text: str) -> None:
    monthly, daily = kf.build_industry_panels(monthly_text, daily_text, source_vintage="v1")
    assert list(monthly.columns) == [
        "date",
        "asset",
        "weighting",
        "ret",
        "available_at",
        "n_firms",
        "avg_size",
        "source_vintage",
    ]
    assert list(daily.columns) == list(monthly.columns)
    # 4 months x 3 assets x 2 weightings; 5 days x 3 assets x 2 weightings.
    assert len(monthly) == 24
    assert len(daily) == 30
    assert set(monthly["weighting"]) == {"vw", "ew"}
    assert (monthly["available_at"] == monthly["date"]).all()
    assert monthly["source_vintage"].unique().tolist() == ["v1"]
    ew = monthly[(monthly["weighting"] == "ew") & (monthly["asset"] == "Agric")]
    assert ew["ret"].tolist() == pytest.approx([0.02, 0.0025, -0.0075, 0.01], abs=1e-15)
    assert monthly["asset"].dtype == "category"
    assert np.issubdtype(monthly["date"].dtype, np.datetime64)


def test_available_at_lag(monthly_text: str, daily_text: str) -> None:
    """L3: n_firms / avg_size reported for month m are only visible from month m+1."""
    monthly, daily = kf.build_industry_panels(monthly_text, daily_text, source_vintage="v1")
    vw = monthly[(monthly["weighting"] == "vw") & (monthly["asset"] == "Food")].set_index("date")
    # Raw n_firms for Food: Jan 40, Feb 41, Mar 42, Apr 43 -> panel shows the previous month.
    assert vw["n_firms"].isna().iloc[0]
    assert vw["n_firms"].iloc[1:].tolist() == [40, 41, 42]
    assert vw["avg_size"].iloc[1:].tolist() == [31.19, 32.00, 33.00]
    d = daily[(daily["weighting"] == "vw") & (daily["asset"] == "Food")].set_index("date")
    # Jan days carry Dec 2022 (not in fixture: missing); Feb days carry Jan; Mar 1 carries Feb.
    assert d.loc["2023-01-30", "n_firms"] is pd.NA
    assert d.loc["2023-02-01", "n_firms"] == 40
    assert d.loc["2023-02-28", "n_firms"] == 40
    assert d.loc["2023-03-01", "n_firms"] == 41
    # Fun's Jan avg_size was -99.99 -> missing in February.
    fun = monthly[(monthly["weighting"] == "vw") & (monthly["asset"] == "Fun")].set_index("date")
    assert math.isnan(fun.loc["2023-02-28", "avg_size"])
