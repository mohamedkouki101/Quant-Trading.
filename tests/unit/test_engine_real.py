"""E-6 on real research-period data: engine equals oracle for B1, B3, B4, B5 at 0 and 10 bp.

This computes strategy returns, so (like D-4) it only runs after Kouki has tagged the
pre-registration (`prereg-v1`), DECISIONS 010 (h). Only the max absolute difference is checked;
no performance figure is printed or stored, and nothing goes to the trial ledger.
"""

import numpy as np
import pytest

from momlab import engine, gitinfo, oracle
from momlab.config import CostConfig, RunConfig
from momlab.data.handler import DataHandler

pytestmark = [
    pytest.mark.data,
    pytest.mark.skipif(
        not gitinfo.git_tag_exists("prereg-v1"), reason="waits for Kouki's prereg-v1 tag"
    ),
]


def _arrays(cfg: RunConfig) -> tuple[DataHandler, np.ndarray, np.ndarray]:
    dh = DataHandler.from_processed(cfg.weighting, start=cfg.start, end=cfg.end)
    while dh.advance() is not None:
        pass
    rets = np.asarray(dh.view().returns())
    rf = np.array([dh.bar_rf(ts) for ts in dh.dates])
    return dh, rets, rf


@pytest.mark.parametrize("strategy", ["b1", "b3", "b4", "b5"])
@pytest.mark.parametrize("bps", [0.0, 10.0])
def test_engine_equals_oracle_real(strategy: str, bps: float) -> None:
    extra: dict[str, object] = {}
    if strategy == "b5":
        extra = {"lookback_months": 1, "skip_months": 0}
    cfg = RunConfig(strategy=strategy, cost=CostConfig(model="flat", bps=bps), **extra)  # type: ignore[arg-type]
    full, rets, rf = _arrays(cfg)
    res = engine.run(cfg, DataHandler.from_processed(cfg.weighting, start=cfg.start, end=cfg.end))
    ora = oracle.run_oracle(cfg, full.dates, rets, rf)
    for col in ("gross", "net"):
        assert np.abs(res.daily[col].to_numpy() - ora[col].to_numpy()).max() <= 1e-10
