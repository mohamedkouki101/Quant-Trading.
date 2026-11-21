"""E-2: DataHandler, AsOfView and the test vault (synthetic data only)."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momlab import gitinfo
from momlab.data import handler as h
from momlab.data.handler import AsOfView, DataHandler, LookAheadError

DATES = pd.DatetimeIndex(pd.to_datetime(["2005-12-29", "2005-12-30", "2006-01-03", "2006-01-04"]))
RETS = np.array([[0.01, 0.02], [0.03, -0.01], [0.05, 0.05], [0.07, 0.07]])


def _handler(**kw: object) -> DataHandler:
    return DataHandler(DATES, ["A", "B"], RETS, **kw)  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def _no_unlock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("MOMLAB_UNLOCK_TEST", raising=False)
    monkeypatch.setattr(h, "UNLOCK_LOG", tmp_path / "unlock_log.jsonl")


def test_vault_locked(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """L8: rows from 2006-01-01 are invisible by default and the env var alone is not enough."""
    dh = _handler()
    assert list(dh.dates) == list(DATES[:2])
    monkeypatch.setenv("MOMLAB_UNLOCK_TEST", "1")
    monkeypatch.setattr(gitinfo, "git_tag_exists", lambda tag: False)
    assert len(_handler().dates) == 2
    assert not (tmp_path / "unlock_log.jsonl").exists()
    # The tag alone is not enough either.
    monkeypatch.delenv("MOMLAB_UNLOCK_TEST")
    monkeypatch.setattr(gitinfo, "git_tag_exists", lambda tag: tag == "prereg-v2")
    assert len(_handler().dates) == 2


def test_vault_unlocks_with_env_and_tag_and_logs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MOMLAB_UNLOCK_TEST", "1")
    monkeypatch.setattr(gitinfo, "git_tag_exists", lambda tag: tag == "prereg-v2")
    monkeypatch.setattr(gitinfo, "git_sha", lambda: "deadbeef")
    dh = _handler(unlock_reason="unit test")
    assert len(dh.dates) == 4
    lines = (tmp_path / "unlock_log.jsonl").read_text(encoding="utf-8").splitlines()
    entry = json.loads(lines[0])
    assert entry["git_sha"] == "deadbeef" and entry["reason"] == "unit test"
    assert entry["ts"].endswith("Z")


def test_cursor_and_view_bounds() -> None:
    dh = _handler()
    assert dh.now is None
    with pytest.raises(LookAheadError):
        dh.view()
    ev = dh.advance()
    assert ev is not None and ev.ts == DATES[0]
    v = dh.view()
    assert v.now == DATES[0] and dh.now == DATES[0] and dh.cursor == 0
    np.testing.assert_array_equal(v.returns(), RETS[:1])
    assert v.returns_at(0).tolist() == [0.01, 0.02]
    with pytest.raises(LookAheadError):
        v.returns_at(1)
    with pytest.raises(IndexError):
        v.returns_at(-1)
    dh.advance()
    # The old view is a snapshot: it still cannot see the new bar.
    with pytest.raises(LookAheadError):
        v.returns_at(1)
    v2 = dh.view()
    np.testing.assert_array_equal(v2.returns(lookback=1), RETS[1:2])
    np.testing.assert_array_equal(v2.returns(lookback=5), RETS[:2])
    assert list(v2.dates(lookback=1)) == [DATES[1]]
    assert v2.assets == ("A", "B")
    with pytest.raises(ValueError, match="lookback"):
        v2.returns(lookback=0)
    assert dh.advance() is None  # vault removed the 2006 rows: data ends here
    assert dh.advance() is None


def test_bar_returns_and_rf() -> None:
    dh = _handler(rf=np.array([0.0001, 0.0002, 0.0003, 0.0004]))
    dh.advance()
    assert dh.bar_returns(DATES[0]).tolist() == [0.01, 0.02]
    assert dh.bar_rf(DATES[0]) == 0.0001
    with pytest.raises(LookAheadError):
        dh.bar_returns(DATES[1])
    with pytest.raises(KeyError):
        dh.bar_returns(pd.Timestamp("2005-12-31"))
    out = dh.bar_returns(DATES[0])
    with pytest.raises(ValueError, match="read-only"):
        out[0] = 1.0


def test_default_rf_is_zero() -> None:
    dh = _handler()
    dh.advance()
    assert dh.bar_rf(DATES[0]) == 0.0


def test_field_drops_rows_not_yet_available() -> None:
    nf = np.array([[3.0, 40.0], [4.0, 41.0], [5.0, 42.0], [6.0, 43.0]])
    # Row 1's value becomes available only one day later (row 2's date).
    avail = np.array(DATES.to_numpy(), copy=True)
    avail[1] = DATES[2].to_datetime64()
    dh = DataHandler(
        DATES[:2],
        ["A", "B"],
        RETS[:2],
        fields={"n_firms": nf[:2]},
        field_available_at={"n_firms": avail[:2]},
    )
    dh.advance()
    dh.advance()
    v = dh.view()
    np.testing.assert_array_equal(v.field("n_firms"), nf[:1])
    np.testing.assert_array_equal(v.field("n_firms", lookback=1), np.empty((0, 2)))
    with pytest.raises(KeyError):
        v.field("missing")


def test_field_default_available_at_is_date() -> None:
    dh = _handler(fields={"x": np.ones((4, 2))})
    dh.advance()
    assert dh.view().field("x").shape == (1, 2)


def test_month_returns_compound_daily_within_months() -> None:
    dates = pd.DatetimeIndex(
        pd.to_datetime(["2001-01-30", "2001-01-31", "2001-02-27", "2001-02-28", "2001-03-01"])
    )
    rets = np.array([[0.10, 0.0], [0.10, np.nan], [-0.5, 0.01], [0.2, 0.02], [0.3, 0.3]])
    dh = DataHandler(dates, ["A", "B"], rets)
    for _ in range(4):
        dh.advance()
    m = dh.view().month_returns(2)
    # Jan: A 1.1*1.1-1 = 0.21, B has a missing day -> NaN ; Feb: A 0.5*1.2-1 = -0.4, B 1.01*1.02-1
    np.testing.assert_allclose(m[0], [0.21, np.nan], rtol=0, atol=1e-15)
    np.testing.assert_allclose(m[1], [-0.4, 0.0302], rtol=0, atol=1e-15)
    assert dh.view().month_returns(5).shape == (2, 2)  # only two months exist so far
    assert list(dh.view().month_ends(2)) == [pd.Timestamp("2001-01-31"), pd.Timestamp("2001-02-28")]
    with pytest.raises(ValueError, match="n_months"):
        dh.view().month_returns(0)


def test_validation() -> None:
    with pytest.raises(ValueError, match="shape"):
        DataHandler(DATES, ["A"], RETS)
    with pytest.raises(ValueError, match="increasing"):
        DataHandler(DATES[::-1], ["A", "B"], RETS)
    with pytest.raises(ValueError, match="shape"):
        DataHandler(DATES, ["A", "B"], RETS, rf=np.zeros(3))
    with pytest.raises(ValueError, match="shape"):
        DataHandler(DATES, ["A", "B"], RETS, fields={"x": np.zeros((4, 3))})


def test_no_dataframe_attribute() -> None:
    dh = _handler()
    dh.advance()
    v = dh.view()
    public = [a for a in dir(v) if not a.startswith("_")]
    assert sorted(public) == [
        "assets",
        "dates",
        "field",
        "month_ends",
        "month_returns",
        "now",
        "returns",
        "returns_at",
    ]
    for name in public:
        assert not isinstance(getattr(v, name), pd.DataFrame)
    assert isinstance(v, AsOfView)


def test_from_processed(tmp_path: Path) -> None:
    rows = []
    for d in DATES:
        for a, base in (("A", 0.01), ("B", 0.02)):
            for w in ("vw", "ew"):
                rows.append(
                    {
                        "date": d,
                        "asset": a,
                        "weighting": w,
                        "ret": base if w == "vw" else -base,
                        "available_at": d,
                        "n_firms": 5,
                        "avg_size": 1.5,
                        "source_vintage": "v",
                    }
                )
    panel = pd.DataFrame(rows)
    panel["asset"] = pd.Categorical(panel["asset"], categories=["A", "B"])
    panel["n_firms"] = panel["n_firms"].astype("Int64")
    panel.to_parquet(tmp_path / "industry_daily.parquet", index=False)
    fac = pd.DataFrame({"date": DATES, "rf": [0.0001, 0.0002, 0.0003, 0.0004]})
    fac.to_parquet(tmp_path / "factors_daily.parquet", index=False)

    dh = DataHandler.from_processed("ew", processed_dir=tmp_path, fields=("n_firms",))
    assert list(dh.dates) == list(DATES[:2])  # vault
    dh.advance()
    assert dh.bar_returns(DATES[0]).tolist() == [-0.01, -0.02]
    assert dh.bar_rf(DATES[0]) == 0.0001
    assert dh.view().field("n_firms").tolist() == [[5.0, 5.0]]
    dh2 = DataHandler.from_processed(
        "vw", processed_dir=tmp_path, start="2005-12-30", end="2005-12-30"
    )
    assert list(dh2.dates) == [DATES[1]]
