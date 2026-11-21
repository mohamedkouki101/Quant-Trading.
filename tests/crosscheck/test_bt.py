"""V-3: engine vs bt 1.4.1 (PLAN §9.3 step 2). Hypothetical backtests only."""

import subprocess

import numpy as np
import pytest

from momlab import crosscheck, synthetic
from momlab.config import RunConfig

pytest.importorskip("bt")
# ffn (a bt dependency) calls pandas.infer_freq, which warns about a future change.
pytestmark = pytest.mark.filterwarnings("ignore:A future version of pandas will return")


def _cfg(strategy: str, bps: float, m: synthetic.Market) -> RunConfig:
    return RunConfig(
        strategy=strategy,
        start=m.dates[0].date(),
        end=m.dates[-1].date(),
        n_per_leg=5,
        cost={"model": "flat", "bps": bps},
    )


@pytest.fixture(scope="module")
def market() -> synthetic.Market:
    return synthetic.null_market(n_assets=20, n_years=10, seed=3)


@pytest.mark.parametrize("strategy", ["b1", "b3", "b4"])
def test_bt_matches_engine_at_zero_cost(strategy: str, market: synthetic.Market) -> None:
    c = crosscheck.bt_crosscheck(_cfg(strategy, 0.0, market), market)
    # PLAN §2.3: annualised return within 5 bp/yr and daily correlation > 0.9999.
    assert abs(c.ann_gap_bp) < 5.0 and c.corr > 0.9999
    assert c.max_abs_gap < 1e-12  # in fact identical up to floating point


@pytest.mark.parametrize("strategy", ["b1", "b3", "b4"])
def test_bt_gap_at_cost_is_commission_sizing(strategy: str, market: synthetic.Market) -> None:
    """Cause (b): bt takes each trade's commission out of the trade (position gets A/(1 ± b))
    instead of trading exactly to the target. A replica of that rule equals bt to floating
    point, so it explains the whole gap."""
    c = crosscheck.bt_crosscheck(_cfg(strategy, 10.0, market), market)
    assert c.corr > 0.9999
    assert 0 < c.weight_dev < 1e-2  # bt misses the target by about the commission
    assert c.sizing_error < 1e-12  # bt weights = replica weights after every fill
    assert c.max_abs_gap_bt_convention < 1e-12


def test_unshifted_weights_show_the_timing_difference(market: synthetic.Market) -> None:
    """Cause (a): fed the weights on the order date, bt trades one bar early."""
    shifted = crosscheck.bt_crosscheck(_cfg("b3", 0.0, market), market)
    early = crosscheck.bt_crosscheck(_cfg("b3", 0.0, market), market, shift=False)
    assert shifted.max_abs_gap < 1e-12 < 1e-4 < early.max_abs_gap


@pytest.mark.parametrize("bps", [0.0, 10.0])
def test_bt_survives_a_book_that_compounds_into_billions(bps: float) -> None:
    """bt's trade-sizing loop accepts a result only within 1e-8 dollars; started with 1e6 it
    breaks once the book is worth ~1e9 (float spacing > 1e-8). The cross-check scales bt's
    starting capital so its peak value stays near 1e6; returns are scale-free."""
    m = synthetic.planted_momentum(n_assets=20, n_years=30, beta=0.03, n_per_leg=5, seed=11)
    c = crosscheck.bt_crosscheck(_cfg("b3", bps, m), m)
    assert c.peak_nav > 1e4  # the engine book grew by more than 10,000x
    if bps == 0.0:  # no commission: bt sizes in one step, exact to floating point
        assert c.max_abs_gap < 1e-12 and c.max_abs_gap_bt_convention < 1e-12
    else:
        # With a commission bt iterates until within 1e-8 *dollars* of the amount; on a book
        # that starts at 1e6 / peak_nav dollars that is a relative error of up to
        # 1e-8 / (1e6 / peak_nav). Derived from bt's constant, not fitted.
        assert c.max_abs_gap_bt_convention < 1e-8 / (1e6 / c.peak_nav)


def _tagged() -> bool:
    try:
        out = subprocess.run(["git", "tag", "-l", "prereg-v1"], capture_output=True, text=True)
    except OSError:
        return False
    return "prereg-v1" in out.stdout.split()


@pytest.mark.data
@pytest.mark.skipif(not _tagged(), reason="waits for Kouki's prereg-v1 tag")
@pytest.mark.parametrize("strategy", ["b1", "b3", "b4"])
def test_bt_matches_engine_real_research_period(strategy: str) -> None:
    from momlab.config import load_config
    from momlab.data.handler import DataHandler

    cfg = load_config("configs/base.yaml").model_copy(
        update={"strategy": strategy, "cost": RunConfig().cost.model_copy(update={"bps": 0.0})}
    )
    dh = DataHandler.from_processed(cfg.weighting, start=cfg.start, end=cfg.end)
    rows = []
    while dh.advance() is not None:
        rows.append(dh.bar_returns(dh.dates[dh.cursor]))
    rets = np.vstack(rows)
    m = synthetic.Market(dh.dates, list(dh.assets), rets, np.zeros(len(dh.dates)))
    c = crosscheck.bt_crosscheck(cfg, m)
    assert abs(c.ann_gap_bp) < 5.0 and c.corr > 0.9999
