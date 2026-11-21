"""V-6: golden metrics of B1, B3, B4, B5 on a seeded synthetic market (PLAN §9.4).

Fails if any metric moves by more than 1e-9. To accept a deliberate change, run once with
``GOLDEN_UPDATE=1`` (rewrites the parquet) and explain the change in docs/DECISIONS.md.
Hypothetical backtests only.
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momlab import engine, paths, synthetic
from momlab.analytics import metrics
from momlab.config import load_config
from momlab.data.handler import DataHandler

GOLDEN = Path(__file__).with_name("golden_synthetic.parquet")
TOL = 1e-9
STRATEGY_FILES = {
    "b1": "b1_equal_weight.yaml",
    "b3": "b3_mom_12_1.yaml",
    "b4": "b4_vs_mom_12_1.yaml",
    "b5": "b5_mom_1m.yaml",
}


def current_metrics() -> pd.DataFrame:
    m = synthetic.null_market(n_assets=20, n_years=8, seed=7)
    rf = pd.Series(np.full(len(m.dates), 0.0001), index=m.dates)
    rows = {}
    for strategy, file in STRATEGY_FILES.items():
        cfg = load_config(
            paths.ROOT / "configs" / "base.yaml", paths.ROOT / "configs" / "strategies" / file
        ).model_copy(update={"start": m.dates[0].date(), "end": m.dates[-1].date(), "n_per_leg": 5})
        assert cfg.strategy == strategy
        res = engine.run(cfg, DataHandler(m.dates, m.assets, m.returns, rf=rf.to_numpy()))
        perf = metrics.performance(res.daily["net"], rf, "D", turnover=res.daily["turnover"])
        rows[strategy] = {k: np.nan if v is None else float(v) for k, v in perf.items()}
    return pd.DataFrame(rows).T.sort_index(axis=1)


def differences(golden: pd.DataFrame, now: pd.DataFrame, tol: float = TOL) -> list[str]:
    """Metrics that changed by more than ``tol`` (NaN equals NaN), or a changed shape."""
    if list(golden.index) != list(now.index) or list(golden.columns) != list(now.columns):
        return ["strategies or metric names changed"]
    a, b = golden.to_numpy(dtype=float), now.to_numpy(dtype=float)
    bad = ~((np.abs(a - b) <= tol) | (np.isnan(a) & np.isnan(b)))
    return [
        f"{golden.index[i]}.{golden.columns[j]}: {a[i, j]!r} -> {b[i, j]!r}"
        for i, j in zip(*np.nonzero(bad), strict=True)
    ]


def test_golden_synthetic_metrics() -> None:
    now = current_metrics()
    if os.environ.get("GOLDEN_UPDATE") == "1":
        now.to_parquet(GOLDEN)
        pytest.skip("golden file rewritten (GOLDEN_UPDATE=1): explain the change in DECISIONS")
    assert GOLDEN.exists(), "golden file missing: run once with GOLDEN_UPDATE=1"
    assert differences(pd.read_parquet(GOLDEN), now) == []


def test_a_1e8_change_fails() -> None:
    golden = pd.read_parquet(GOLDEN)
    assert differences(golden, golden.copy()) == []
    moved = golden.copy()
    moved.loc["b3", "sharpe"] += 1e-8
    assert differences(golden, moved) == [
        f"b3.sharpe: {golden.loc['b3', 'sharpe']!r} -> {moved.loc['b3', 'sharpe']!r}"
    ]
    renamed = golden.rename(columns={"sharpe": "sharpe2"})
    assert differences(golden, renamed) == ["strategies or metric names changed"]
