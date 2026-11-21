"""D-2 acceptance on the real Ken French data (run `uv run python tasks.py data` first)."""

import json

import pandas as pd
import pytest

from momlab import paths

pytestmark = pytest.mark.data

CODES_AS_DECIMAL = [-0.9999, -9.99, -99.99, -999.0]


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(paths.MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def daily() -> pd.DataFrame:
    return pd.read_parquet(paths.PROCESSED_DIR / "industry_daily.parquet")


@pytest.fixture(scope="module")
def monthly() -> pd.DataFrame:
    return pd.read_parquet(paths.PROCESSED_DIR / "industry_monthly.parquet")


def test_49_assets(daily: pd.DataFrame, monthly: pd.DataFrame) -> None:
    assert daily["asset"].nunique() == 49
    assert monthly["asset"].nunique() == 49
    assert list(daily["asset"].cat.categories)[:3] == ["Agric", "Food", "Soda"]


def test_daily_date_range_matches_manifest(daily: pd.DataFrame, manifest: dict) -> None:
    dates = pd.DatetimeIndex(daily["date"].unique())
    assert dates[0] == pd.Timestamp("1926-07-01")
    assert dates[-1] >= pd.Timestamp("2026-09-30")  # C8: at least, and equal to the manifest
    assert (
        dates[-1].date().isoformat() == manifest["processed"]["industry_daily.parquet"]["last_date"]
    )
    assert dates.is_monotonic_increasing and dates.is_unique


def test_no_missing_codes_left(daily: pd.DataFrame, monthly: pd.DataFrame) -> None:
    for df in (daily, monthly):
        assert not df["ret"].isin(CODES_AS_DECIMAL).any()
        assert not df["avg_size"].isin([-99.99, -999.0]).any()
        assert df["ret"].min() > -1.0  # a simple return can never be below -100%


def test_one_row_per_date_asset_weighting(daily: pd.DataFrame, monthly: pd.DataFrame) -> None:
    for df in (daily, monthly):
        assert not df.duplicated(["date", "asset", "weighting"]).any()
        for _, g in df.groupby(["asset", "weighting"], observed=True):
            assert g["date"].is_monotonic_increasing


def test_monthly_dates_are_month_ends(monthly: pd.DataFrame) -> None:
    dates = pd.DatetimeIndex(monthly["date"].unique())
    assert dates.is_month_end.all()
    assert dates[0] == pd.Timestamp("1926-07-31")


def test_available_at_lag_real(monthly: pd.DataFrame) -> None:
    """L3 on real data: Agric reports 3 firms for 1926-07 (first row of the raw block); the
    panel shows it on 1926-08-31, and 1926-07-31 has no value."""
    agric = monthly[(monthly["asset"] == "Agric") & (monthly["weighting"] == "vw")].set_index(
        "date"
    )
    assert agric.loc["1926-07-31", "n_firms"] is pd.NA
    assert agric.loc["1926-08-31", "n_firms"] == 3


def test_factors(manifest: dict) -> None:
    fd = pd.read_parquet(paths.PROCESSED_DIR / "factors_daily.parquet")
    fm = pd.read_parquet(paths.PROCESSED_DIR / "factors_monthly.parquet")
    cols = ["date", "mkt_rf", "smb", "hml", "rf", "mom", "st_rev"]
    assert list(fd.columns) == cols and list(fm.columns) == cols
    assert fd["rf"].notna().all() and fm["rf"].notna().all()
    assert fm["rf"].abs().max() < 0.02  # RF in decimals: never above 2% a month
    assert manifest["processed"]["factors_monthly.parquet"]["rows"] == len(fm)
