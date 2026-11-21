"""E-8: append-only trial ledger with a sha256 hash chain (PLAN §7.5)."""

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momlab import engine, ledger
from momlab.config import RunConfig
from momlab.data.handler import DataHandler
from momlab.ledger import GENESIS, Ledger, LedgerError

SCHEMA_KEYS = {
    "trial_id",
    "ts",
    "git_sha",
    "dirty",
    "config_hash",
    "config",
    "data_manifest_hash",
    "phase",
    "strategy",
    "family",
    "period",
    "cost_bps",
    "seed",
    "metrics",
    "counts_toward_budget",
    "notes",
}
METRIC_KEYS = {
    "ann_ret",
    "ann_vol",
    "sharpe",
    "sharpe_hac_t",
    "sortino",
    "mdd",
    "calmar",
    "worst_month",
    "skew",
    "kurt",
    "turnover_1way_monthly",
    "rank_ic_mean",
    "rank_ic_t",
    "n_months",
}


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _filled(tmp_path: Path, n: int = 3) -> Ledger:
    led = Ledger(tmp_path / "ledger.jsonl")
    for i in range(n):
        led.append({"trial_id": f"t{i}", "metrics": {"sharpe": 0.1 * i}, "notes": "x"})
    return led


def test_chain_links_each_line_to_the_previous_one(tmp_path: Path) -> None:
    led = _filled(tmp_path)
    raw = (tmp_path / "ledger.jsonl").read_bytes()
    assert raw.endswith(b"\n") and b"\r" not in raw
    lines = raw.split(b"\n")[:-1]
    assert json.loads(lines[0])["prev_sha256"] == GENESIS == "0" * 64
    assert json.loads(lines[1])["prev_sha256"] == _sha(lines[0])
    assert json.loads(lines[2])["prev_sha256"] == _sha(lines[1])
    head = json.loads((tmp_path / "ledger_head.json").read_text())
    assert head == {"n_lines": 3, "last_sha256": _sha(lines[2])}
    assert led.verify() == 3 and len(led) == 3
    assert [e["trial_id"] for e in led.read()] == ["t0", "t1", "t2"]


def _tamper_edit_first(p: Path) -> None:
    p.write_bytes(p.read_bytes().replace(b'"sharpe":0.0', b'"sharpe":9.0', 1))


def _tamper_edit_last(p: Path) -> None:
    p.write_bytes(p.read_bytes().replace(b'"sharpe":0.2', b'"sharpe":0.3', 1))


def _tamper_delete(i: int):  # type: ignore[no-untyped-def]
    def f(p: Path) -> None:
        lines = p.read_bytes().split(b"\n")[:-1]
        del lines[i]
        p.write_bytes(b"".join(x + b"\n" for x in lines))

    return f


def _tamper_swap(p: Path) -> None:
    lines = p.read_bytes().split(b"\n")[:-1]
    lines[0], lines[1] = lines[1], lines[0]
    p.write_bytes(b"".join(x + b"\n" for x in lines))


def _tamper_raw_append(p: Path) -> None:
    lines = p.read_bytes().split(b"\n")[:-1]
    extra = json.dumps({"prev_sha256": _sha(lines[-1]), "trial_id": "sneaky"}).encode()
    p.write_bytes(p.read_bytes() + extra + b"\n")


def _tamper_crlf(p: Path) -> None:
    p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))


@pytest.mark.parametrize(
    "tamper",
    [
        _tamper_edit_first,
        _tamper_edit_last,
        _tamper_delete(0),
        _tamper_delete(1),
        _tamper_delete(2),
        _tamper_swap,
        _tamper_raw_append,
        _tamper_crlf,
    ],
    ids=[
        "edit-first",
        "edit-last",
        "delete-first",
        "delete-middle",
        "delete-last",
        "swap",
        "append-without-api",
        "crlf",
    ],
)
def test_ledger_append_only(tmp_path: Path, tamper) -> None:  # type: ignore[no-untyped-def]
    led = _filled(tmp_path)
    tamper(tmp_path / "ledger.jsonl")
    with pytest.raises(LedgerError):
        led.verify()
    # A broken ledger refuses further appends.
    with pytest.raises(LedgerError):
        led.append({"trial_id": "after"})


def test_missing_or_mismatched_files(tmp_path: Path) -> None:
    led = Ledger(tmp_path / "ledger.jsonl")
    assert led.verify() == 0 and led.read() == [] and len(led) == 0
    _filled(tmp_path, 1)
    (tmp_path / "ledger_head.json").unlink()
    with pytest.raises(LedgerError, match="head"):
        led.verify()
    led2 = _filled(tmp_path / "b", 1)
    (tmp_path / "b" / "ledger.jsonl").unlink()
    with pytest.raises(LedgerError, match="missing"):
        led2.verify()
    led3 = Ledger(tmp_path / "c" / "ledger.jsonl")
    (tmp_path / "c").mkdir()
    (tmp_path / "c" / "ledger.jsonl").write_bytes(b"not json\n")
    (tmp_path / "c" / "ledger_head.json").write_text(
        json.dumps({"n_lines": 1, "last_sha256": _sha(b"not json")})
    )
    with pytest.raises(LedgerError, match="line 1"):
        led3.verify()


def test_append_rejects_reserved_key_and_nonfinite(tmp_path: Path) -> None:
    led = Ledger(tmp_path / "ledger.jsonl")
    with pytest.raises(ValueError, match="prev_sha256"):
        led.append({"prev_sha256": "x"})
    led.append({"metrics": {"calmar": math.nan, "x": math.inf, "y": np.float64(0.5)}})
    m = led.read()[0]["metrics"]
    assert m == {"calmar": None, "x": None, "y": 0.5}
    led.append({"when": pd.Timestamp("2001-02-03").date(), "ids": (np.int64(1), True)})
    assert led.read()[1] == {
        "prev_sha256": hashlib.sha256(led.path.read_bytes().split(b"\n")[0]).hexdigest(),
        "when": "2001-02-03",
        "ids": [1, True],
    }


def test_truncated_last_line_fails(tmp_path: Path) -> None:
    led = _filled(tmp_path, 2)
    led.path.write_bytes(led.path.read_bytes()[:-1])  # drop the final newline
    with pytest.raises(LedgerError, match="newline"):
        led.verify()


def test_ledger_api_has_no_update_or_delete() -> None:
    public = {n for n in dir(Ledger) if not n.startswith("_")}
    assert public == {"append", "read", "verify", "path", "head_path"}
    banned = ("update", "delete", "remove", "rewrite", "edit", "clear", "pop", "truncate")
    names = public | {n for n in dir(ledger) if not n.startswith("_")}
    assert not [n for n in names if any(b in n.lower() for b in banned)]


def _market() -> tuple[pd.DatetimeIndex, list[str], np.ndarray, np.ndarray]:
    rng = np.random.default_rng(11)
    dates = pd.bdate_range("1990-01-01", "1993-12-31")
    rets = rng.normal(0.0004, 0.01, (len(dates), 24))
    return dates, [f"A{i}" for i in range(24)], rets, np.full(len(dates), 0.0001)


def _cfg() -> RunConfig:
    return RunConfig(
        strategy="b3",
        start="1990-01-01",
        end="1993-12-31",
        n_per_leg=5,
        cost={"model": "flat", "bps": 10.0},
    )


def test_make_entry_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ledger.gitinfo, "git_sha", lambda: "abc123")
    monkeypatch.setattr(ledger.gitinfo, "git_dirty", lambda: True)
    cfg = _cfg()
    dates, assets, rets, rf = _market()
    res = engine.run(cfg, DataHandler(dates, assets, rets, rf=rf))
    e = ledger.make_entry(cfg, res, pd.Series(rf, index=dates), notes="unit", manifest_hash=None)
    assert set(e) == SCHEMA_KEYS and set(e["metrics"]) >= METRIC_KEYS
    assert e["git_sha"] == "abc123" and e["dirty"] is True
    assert e["config_hash"] == cfg.config_hash() == res.config_hash
    assert e["config"] == json.loads(cfg.canonical_json())
    assert e["phase"] == "research" and e["family"] == "rules" and e["strategy"] == "b3"
    assert e["period"] == ["1990-01-01", "1993-12-31"] and e["cost_bps"] == 10.0
    assert e["seed"] == 7 and e["counts_toward_budget"] is True and e["notes"] == "unit"
    assert e["metrics"]["rank_ic_mean"] is None and e["metrics"]["n_months"] == 48
    assert len(e["trial_id"]) == 36 and e["ts"].endswith("Z")
    test_cfg = cfg.model_copy(
        update={
            "start": pd.Timestamp("2006-01-01").date(),
            "end": pd.Timestamp("2007-12-31").date(),
        }
    )
    assert ledger.make_entry(test_cfg, res, None, manifest_hash="m")["phase"] == "test"
    spread = cfg.model_copy(
        update={"cost": cfg.cost.model_copy(update={"model": "spread_impact_borrow"})}
    )
    assert ledger.make_entry(spread, res, None, manifest_hash="m")["cost_bps"] is None


def test_manifest_hash(tmp_path: Path) -> None:
    assert ledger.manifest_hash(tmp_path / "nope.json") is None
    (tmp_path / "m.json").write_bytes(b"{}\n")
    assert ledger.manifest_hash(tmp_path / "m.json") == _sha(b"{}\n")


def test_engine_run_logs_one_trial(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ledger.gitinfo, "git_sha", lambda: "abc123")
    monkeypatch.setattr(ledger.gitinfo, "git_dirty", lambda: False)
    dates, assets, rets, rf = _market()
    led = Ledger(tmp_path / "ledger.jsonl")
    plain = engine.run(_cfg(), DataHandler(dates, assets, rets, rf=rf))
    assert not led.path.exists()  # log=False is the default: nothing written
    res = engine.run(
        _cfg(), DataHandler(dates, assets, rets, rf=rf), log=True, ledger=led, notes="synthetic"
    )
    assert led.verify() == 1
    entry = led.read()[0]
    assert entry["config_hash"] == res.config_hash and entry["notes"] == "synthetic"
    assert entry["data_manifest_hash"] is None  # synthetic handler, not data/processed
    pd.testing.assert_frame_equal(plain.daily, res.daily)
    from momlab.analytics import metrics

    exp = metrics.sharpe(res.daily["net"], pd.Series(rf, index=dates), freq="D")
    assert entry["metrics"]["sharpe"] == pytest.approx(exp, rel=1e-12)
    engine.run(_cfg(), DataHandler(dates, assets, rets, rf=rf), log=True, ledger=led)
    assert led.verify() == 2


def test_engine_run_default_ledger_and_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no handler the run reads data/processed (faked here), records the manifest hash and
    logs to the default ledger path (redirected to tmp)."""
    dates, assets, rets, rf = _market()
    monkeypatch.setattr(
        DataHandler,
        "from_processed",
        staticmethod(lambda weighting, **kw: DataHandler(dates, assets, rets, rf=rf)),
    )
    monkeypatch.setattr(ledger, "LEDGER", tmp_path / "default.jsonl")
    (tmp_path / "manifest.json").write_bytes(b"{}\n")
    monkeypatch.setattr(ledger.paths, "MANIFEST", tmp_path / "manifest.json")
    engine.run(_cfg(), log=True)
    led = Ledger(tmp_path / "default.jsonl")
    assert led.verify() == 1 and led.read()[0]["data_manifest_hash"] == _sha(b"{}\n")
