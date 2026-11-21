"""Append-only trial ledger ``experiments/ledger.jsonl`` with a sha256 hash chain (task E-8).

Every strategy run from P4 on is one line (PLAN §7.5 schema) and counts toward the trial budget
and the deflated Sharpe ratio. Integrity (DECISIONS 013):

- Each line is canonical JSON (sorted keys, no spaces, LF ending) with a ``prev_sha256`` field:
  the sha256 of the previous line's bytes, or 64 zeros for the first line.
- ``ledger_head.json`` next to it records the line count and the sha256 of the last line, so
  deleting or adding a line at the end is caught too.
- :meth:`Ledger.verify` checks both and raises :class:`LedgerError`; :meth:`Ledger.append`
  refuses to write onto a broken ledger. There is no way to change or remove a line.

Git information is read-only (correction C12).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from momlab import gitinfo, paths, periods
from momlab.analytics import metrics
from momlab.config import RunConfig

if TYPE_CHECKING:
    from momlab.engine import RunResult

LEDGER: Path = paths.ROOT / "experiments" / "ledger.jsonl"
GENESIS = "0" * 64


class LedgerError(RuntimeError):
    """The ledger's hash chain or head record does not match its lines."""


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _clean(x: Any) -> Any:
    """JSON-safe copy: NumPy scalars to Python, non-finite floats to None, dates to ISO text."""
    if isinstance(x, Mapping):
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, list | tuple):
        return [_clean(v) for v in x]
    if isinstance(x, bool | np.bool_):
        return bool(x)
    if isinstance(x, int | np.integer):
        return int(x)
    if isinstance(x, float | np.floating):
        return float(x) if math.isfinite(float(x)) else None
    if isinstance(x, dt.date):
        return x.isoformat()
    return x


class Ledger:
    """Append-only JSON-lines ledger at ``path`` (default ``experiments/ledger.jsonl``)."""

    __slots__ = ("_path",)

    def __init__(self, path: Path | None = None) -> None:
        self._path = Path(path) if path is not None else LEDGER

    @property
    def path(self) -> Path:
        """The ``.jsonl`` file."""
        return self._path

    @property
    def head_path(self) -> Path:
        """The head record (line count and last line's sha256)."""
        return self._path.with_name(self._path.stem + "_head.json")

    def _lines(self) -> list[bytes]:
        has_file, has_head = self._path.exists(), self.head_path.exists()
        if not has_file and not has_head:
            return []
        if not has_file:
            raise LedgerError(f"ledger file missing: {self._path}")
        if not has_head:
            raise LedgerError(f"ledger head file missing: {self.head_path}")
        raw = self._path.read_bytes()
        if b"\r" in raw:
            raise LedgerError("ledger contains CR bytes (line endings must be LF)")
        if raw and not raw.endswith(b"\n"):
            raise LedgerError("ledger does not end with a newline")
        lines = raw.split(b"\n")[:-1]
        prev = GENESIS
        for i, line in enumerate(lines, start=1):
            try:
                obj = json.loads(line)
            except ValueError as exc:
                raise LedgerError(f"line {i} is not valid JSON") from exc
            if not isinstance(obj, dict) or obj.get("prev_sha256") != prev:
                raise LedgerError(f"line {i}: hash chain broken")
            prev = _sha(line)
        head = json.loads(self.head_path.read_text(encoding="utf-8"))
        if head != {"n_lines": len(lines), "last_sha256": prev}:
            raise LedgerError("ledger head does not match the lines (line added or removed)")
        return lines

    def verify(self) -> int:
        """Check the chain and the head; return the number of lines or raise ``LedgerError``."""
        return len(self._lines())

    def __len__(self) -> int:
        return self.verify()

    def read(self) -> list[dict[str, Any]]:
        """All entries, oldest first (after verifying)."""
        return [json.loads(line) for line in self._lines()]

    def append(self, entry: Mapping[str, Any]) -> dict[str, Any]:
        """Verify, then add ``entry`` as a new last line; returns the stored record."""
        if "prev_sha256" in entry:
            raise ValueError("'prev_sha256' is set by the ledger")
        lines = self._lines()
        prev = _sha(lines[-1]) if lines else GENESIS
        record: dict[str, Any] = {"prev_sha256": prev, **_clean(entry)}
        line = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("ab") as fh:
            fh.write(line + b"\n")
        tmp = self.head_path.with_suffix(".tmp")
        head = {"n_lines": len(lines) + 1, "last_sha256": _sha(line)}
        tmp.write_bytes(json.dumps(head, sort_keys=True).encode() + b"\n")
        os.replace(tmp, self.head_path)
        return record


def manifest_hash(path: Path | None = None) -> str | None:
    """sha256 of the data manifest (default ``data/manifest.json``); None if it is missing."""
    p = paths.MANIFEST if path is None else path
    return _sha(p.read_bytes()) if p.exists() else None


def make_entry(
    config: RunConfig,
    result: RunResult,
    rf: pd.Series | None,
    *,
    manifest_hash: str | None,
    notes: str = "",
    counts_toward_budget: bool = True,
) -> dict[str, Any]:
    """One ledger entry (PLAN §7.5) for a finished run; metrics from daily net returns."""
    daily = result.daily
    perf = metrics.performance(daily["net"], rf, "D", turnover=daily["turnover"])
    perf.update(rank_ic_mean=None, rank_ic_t=None)
    test = pd.Timestamp(config.end) >= pd.Timestamp(periods.TEST_START)
    return {
        "trial_id": str(uuid.uuid4()),
        "ts": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": gitinfo.git_sha(),
        "dirty": gitinfo.git_dirty(),
        "config_hash": result.config_hash,
        "config": json.loads(config.canonical_json()),
        "data_manifest_hash": manifest_hash,
        "phase": "test" if test else "research",
        "strategy": config.strategy,
        "family": "rules",
        "period": [config.start.isoformat(), config.end.isoformat()],
        "cost_bps": config.cost.bps if config.cost.model == "flat" else None,
        "seed": config.seed,
        "metrics": perf,
        "counts_toward_budget": counts_toward_budget,
        "notes": notes,
    }
