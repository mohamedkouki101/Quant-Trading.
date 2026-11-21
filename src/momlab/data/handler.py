"""DataHandler, AsOfView and the test vault (task E-2, PLAN §3.2).

``DataHandler`` holds the daily panel as read-only NumPy arrays (dates x assets) with an
integer cursor. Strategy code never receives the handler: it gets an :class:`AsOfView`, a
snapshot of the cursor that can only return rows at or before it and raises
:class:`LookAheadError` for anything later. Values are simple decimal returns.

Test vault (leakage item L8): rows dated on or after ``periods.TEST_START`` are removed when the
handler is built, unless ``MOMLAB_UNLOCK_TEST=1`` **and** the git tag ``prereg-v2`` exists
(read-only check). Every unlock appends a line to ``experiments/unlock_log.jsonl``.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pandas as pd

from momlab import gitinfo, paths, periods
from momlab.events import MarketEvent

FloatArray = npt.NDArray[np.float64]
UNLOCK_LOG: Path = paths.ROOT / "experiments" / "unlock_log.jsonl"
UNLOCK_ENV = "MOMLAB_UNLOCK_TEST"
UNLOCK_TAG = "prereg-v2"


class LookAheadError(RuntimeError):
    """Strategy code asked for data after the current bar."""


def _ro_float(a: npt.ArrayLike) -> FloatArray:
    out: FloatArray = np.array(a, dtype=np.float64, copy=True)
    out.flags.writeable = False
    return out


def _ro_int(a: npt.ArrayLike) -> npt.NDArray[np.int64]:
    out: npt.NDArray[np.int64] = np.array(a, dtype=np.int64, copy=True)
    out.flags.writeable = False
    return out


def _vault_unlocked(reason: str) -> bool:
    """True only when the env var is set and the ``prereg-v2`` tag exists; logs every unlock."""
    if os.environ.get(UNLOCK_ENV) != "1" or not gitinfo.git_tag_exists(UNLOCK_TAG):
        return False
    entry = {
        "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": gitinfo.git_sha(),
        "reason": reason,
    }
    UNLOCK_LOG.parent.mkdir(parents=True, exist_ok=True)
    with UNLOCK_LOG.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
    return True


class AsOfView:
    """Read-only, cursor-bounded access to the panel at one bar (the only data accessor that
    strategy code receives)."""

    __slots__ = ("__avail", "__assets", "__c", "__dates", "__fields", "__month_id", "__rets")
    __rets: FloatArray
    __fields: Mapping[str, FloatArray]
    __month_id: npt.NDArray[np.int64]

    def __init__(
        self,
        dates: pd.DatetimeIndex,
        assets: tuple[str, ...],
        rets: FloatArray,
        fields: Mapping[str, FloatArray],
        avail: Mapping[str, npt.NDArray[np.datetime64]],
        month_id: npt.NDArray[np.int64],
        cursor: int,
    ) -> None:
        self.__dates = dates
        self.__assets = assets
        self.__rets = rets
        self.__fields = fields
        self.__avail = avail
        self.__month_id = month_id
        self.__c = cursor

    @property
    def now(self) -> pd.Timestamp:
        """Timestamp of the current bar."""
        return pd.Timestamp(self.__dates[self.__c])

    @property
    def assets(self) -> tuple[str, ...]:
        """Asset names in column order."""
        return self.__assets

    def __lo(self, lookback: int | None) -> int:
        if lookback is None:
            return 0
        if lookback < 1:
            raise ValueError("lookback must be >= 1 (or None for all rows up to now)")
        return max(0, self.__c - lookback + 1)

    def returns(self, lookback: int | None = None) -> FloatArray:
        """Daily returns of the last ``lookback`` bars up to and including now (rows x assets)."""
        return self.__rets[self.__lo(lookback) : self.__c + 1]

    def dates(self, lookback: int | None = None) -> pd.DatetimeIndex:
        """Dates of the rows that :meth:`returns` gives for the same ``lookback``."""
        return self.__dates[self.__lo(lookback) : self.__c + 1]

    def returns_at(self, index: int) -> FloatArray:
        """Returns of row ``index`` (absolute); raises ``LookAheadError`` past the cursor."""
        if index > self.__c:
            raise LookAheadError(f"row {index} is after the current bar {self.__c}")
        if index < 0:
            raise IndexError("row index must be >= 0")
        return np.asarray(self.__rets[index], dtype=np.float64)

    def field(self, name: str, lookback: int | None = None) -> FloatArray:
        """Rows of a characteristic up to now, minus rows whose ``available_at`` is after now."""
        values = self.__fields[name]
        lo = self.__lo(lookback)
        ok = self.__avail[name][lo : self.__c + 1] <= self.now.to_datetime64()
        return values[lo : self.__c + 1][ok]

    def __month_rows(self, n_months: int) -> tuple[int, npt.NDArray[np.intp]]:
        if n_months < 1:
            raise ValueError("n_months must be >= 1")
        ids = self.__month_id[: self.__c + 1]
        lo = int(np.searchsorted(ids, ids[-1] - n_months + 1, side="left"))
        starts = np.flatnonzero(np.r_[True, ids[lo + 1 :] != ids[lo:-1]])
        return lo, starts

    def month_returns(self, n_months: int) -> FloatArray:
        """Calendar-month returns compounded from daily returns, for the last ``n_months``
        months up to and including the month of now (oldest first). A month with any missing
        day is NaN (returns are never filled). Fewer rows come back if fewer months exist."""
        lo, starts = self.__month_rows(n_months)
        growth = 1.0 + self.__rets[lo : self.__c + 1]
        return np.multiply.reduceat(growth, starts, axis=0) - 1.0

    def month_ends(self, n_months: int) -> pd.DatetimeIndex:
        """Last available date of each month that :meth:`month_returns` covers."""
        lo, starts = self.__month_rows(n_months)
        ends = np.r_[starts[1:] - 1, self.__c - lo]
        return self.__dates[lo:][ends]


class DataHandler:
    """Daily panel with an integer cursor (PLAN §3.3).

    Parameters: ``dates`` (strictly increasing trading days), ``assets``, ``returns``
    (dates x assets, simple decimal returns, NaN = missing), optional ``rf`` (daily risk-free
    return per date, default 0), ``fields`` (name -> dates x assets) and
    ``field_available_at`` (name -> per-row availability timestamps, default = the row date).
    """

    def __init__(
        self,
        dates: pd.DatetimeIndex,
        assets: Sequence[str],
        returns: npt.ArrayLike,
        *,
        rf: npt.ArrayLike | None = None,
        fields: Mapping[str, npt.ArrayLike] | None = None,
        field_available_at: Mapping[str, npt.ArrayLike] | None = None,
        unlock_reason: str = "",
    ) -> None:
        idx = pd.DatetimeIndex(dates)
        rets = np.asarray(returns, dtype=np.float64)
        n_t, n_a = len(idx), len(assets)
        if rets.shape != (n_t, n_a):
            raise ValueError(f"returns shape {rets.shape} != {(n_t, n_a)}")
        if n_t > 1 and not bool((idx[1:] > idx[:-1]).all()):
            raise ValueError("dates must be strictly increasing")
        rf_arr = np.zeros(n_t) if rf is None else np.asarray(rf, dtype=np.float64)
        if rf_arr.shape != (n_t,):
            raise ValueError(f"rf shape {rf_arr.shape} != {(n_t,)}")
        fields = dict(fields or {})
        avail_in = dict(field_available_at or {})
        for name, arr in fields.items():
            if np.shape(arr) != (n_t, n_a):
                raise ValueError(f"field {name!r} shape {np.shape(arr)} != {(n_t, n_a)}")

        keep = np.ones(n_t, dtype=bool)
        if not _vault_unlocked(unlock_reason):
            keep = np.asarray(idx < periods.TEST_START)
        self.dates: pd.DatetimeIndex = idx[keep]
        self.assets: tuple[str, ...] = tuple(str(a) for a in assets)
        self.__rets = _ro_float(rets[keep])
        self.__rf = _ro_float(rf_arr[keep])
        self.__fields = {
            k: _ro_float(np.asarray(v, dtype=np.float64)[keep]) for k, v in fields.items()
        }
        self.__avail: dict[str, npt.NDArray[np.datetime64]] = {}
        for k in fields:
            if k in avail_in:
                a = np.asarray(avail_in[k], dtype="datetime64[ns]")[keep].copy()
            else:
                a = self.dates.to_numpy().astype("datetime64[ns]")
            a.flags.writeable = False
            self.__avail[k] = a
        self.__month_id = _ro_int(self.dates.year.to_numpy() * 12 + self.dates.month.to_numpy())
        self.__pos = {ts: i for i, ts in enumerate(self.dates)}
        self.cursor = -1

    @classmethod
    def from_processed(
        cls,
        weighting: str = "vw",
        *,
        processed_dir: Path = paths.PROCESSED_DIR,
        start: str | dt.date | None = None,
        end: str | dt.date | None = None,
        fields: Sequence[str] = (),
        unlock_reason: str = "",
    ) -> DataHandler:
        """Build a handler from ``industry_daily.parquet`` (one weighting) and the daily RF in
        ``factors_daily.parquet``."""
        panel = pd.read_parquet(processed_dir / "industry_daily.parquet")
        panel = panel[panel["weighting"] == weighting]
        if start is not None:
            panel = panel[panel["date"] >= pd.Timestamp(start)]
        if end is not None:
            panel = panel[panel["date"] <= pd.Timestamp(end)]
        wide = panel.pivot(index="date", columns="asset", values="ret")  # noqa: PD010
        rf = pd.read_parquet(processed_dir / "factors_daily.parquet").set_index("date")["rf"]
        extra = {
            f: panel.pivot(index="date", columns="asset", values=f)  # noqa: PD010
            .astype("float64")
            .to_numpy()
            for f in fields
        }
        return cls(
            pd.DatetimeIndex(wide.index),
            [str(c) for c in wide.columns],
            wide.to_numpy(dtype=np.float64),
            rf=rf.reindex(wide.index).to_numpy(dtype=np.float64),
            fields=extra,
            unlock_reason=unlock_reason,
        )

    @property
    def now(self) -> pd.Timestamp | None:
        """Timestamp of the current bar (None before the first ``advance``)."""
        return None if self.cursor < 0 else pd.Timestamp(self.dates[self.cursor])

    def advance(self) -> MarketEvent | None:
        """Move to the next bar and return its ``MarketEvent``; None when the data is done."""
        if self.cursor + 1 >= len(self.dates):
            return None
        self.cursor += 1
        return MarketEvent(ts=pd.Timestamp(self.dates[self.cursor]))

    def view(self) -> AsOfView:
        """Snapshot view bounded by the current cursor."""
        if self.cursor < 0:
            raise LookAheadError("no bar yet: call advance() first")
        return AsOfView(
            self.dates,
            self.assets,
            self.__rets,
            self.__fields,
            self.__avail,
            self.__month_id,
            self.cursor,
        )

    def __row(self, ts: pd.Timestamp) -> int:
        i = self.__pos[pd.Timestamp(ts)]
        if i > self.cursor:
            raise LookAheadError(f"{ts} is after the current bar")
        return i

    def bar_returns(self, ts: pd.Timestamp) -> FloatArray:
        """Returns realised on bar ``ts`` (read-only); ``ts`` must not be after now."""
        return np.asarray(self.__rets[self.__row(ts)], dtype=np.float64)

    def bar_rf(self, ts: pd.Timestamp) -> float:
        """Daily risk-free return on bar ``ts``."""
        return float(self.__rf[self.__row(ts)])
