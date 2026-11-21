"""V-2: engine invariants with hypothesis (PLAN §9.1), 200 examples each.

Hypothesis draws the market *parameters* and a seed; returns come from NumPy so rankings have
no ties (ties would make column order matter by construction). Hypothetical backtests only.
"""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from momlab import engine
from momlab.config import RunConfig
from momlab.costs import FlatBps, SpreadImpactBorrow
from momlab.data.handler import AsOfView, DataHandler
from momlab.events import MarketEvent, SignalEvent
from momlab.portfolio import NoRisk

pytestmark = pytest.mark.slow
SETTINGS = settings(max_examples=200, deadline=None, derandomize=True, database=None)


@st.composite
def markets(draw: st.DrawFn) -> dict:
    seed = draw(st.integers(0, 2**32 - 1))
    n_assets = draw(st.integers(4, 10))
    n_months = draw(st.integers(13, 18))
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("1960-01-01", periods=n_months * 21)
    rets = rng.normal(0.0004, 0.01, (len(dates), n_assets))
    if draw(st.booleans()):  # sprinkle missing returns
        rets[rng.random(rets.shape) < 0.01] = np.nan
    rf = np.full(len(dates), draw(st.sampled_from([0.0, 0.0001])))
    return {
        "dates": dates,
        "rets": rets,
        "rf": rf,
        "strategy": draw(st.sampled_from(["b1", "b3", "b4", "b5"])),
        "n_per_leg": draw(st.integers(1, n_assets // 2)),
        "fill_lag": draw(st.integers(1, 3)),
        "perm": rng.permutation(n_assets),
    }


def _cfg(m: dict, bps: float = 0.0) -> RunConfig:
    return RunConfig(
        strategy=m["strategy"],
        start=m["dates"][0].date(),
        end=m["dates"][-1].date(),
        n_per_leg=m["n_per_leg"],
        fill_lag=m["fill_lag"],
        vol_window=20,
        cost={"model": "flat", "bps": bps},
    )


def _names(n: int) -> list[str]:
    return [f"A{i}" for i in range(n)]


@SETTINGS
@given(markets())
def test_zero_cost_run_invariant_to_column_order(m: dict) -> None:
    n = m["rets"].shape[1]
    a = engine.run(_cfg(m), DataHandler(m["dates"], _names(n), m["rets"], rf=m["rf"]))
    perm = m["perm"]
    names = [_names(n)[i] for i in perm]
    b = engine.run(_cfg(m), DataHandler(m["dates"], names, m["rets"][:, perm], rf=m["rf"]))
    np.testing.assert_allclose(a.daily["net"], b.daily["net"], rtol=0, atol=1e-12)
    np.testing.assert_allclose(a.weights[names].to_numpy(), b.weights.to_numpy(), atol=1e-12)


@SETTINGS
@given(markets(), st.sampled_from([0.0, 10.0]))
def test_weights_after_fill_equal_target(m: dict, bps: float) -> None:
    n = m["rets"].shape[1]
    res = engine.run(_cfg(m, bps), DataHandler(m["dates"], _names(n), m["rets"], rf=m["rf"]))
    targets = dict(zip(res.orders["order_id"], res.orders["target"], strict=True))
    for ts, oid in zip(res.fills["ts"], res.fills["order_id"], strict=True):
        w = res.weights.loc[ts].to_numpy()
        np.testing.assert_array_equal(w, targets[oid])
        gross = np.abs(w).sum()
        if m["strategy"] in ("b3", "b5"):
            assert gross == pytest.approx(2.0, abs=1e-12) or gross == 0.0
        elif m["strategy"] == "b1":
            assert gross == pytest.approx(1.0, abs=1e-12)
        else:  # b4: 2 × leverage, leverage in [0, cap]
            assert -1e-12 <= gross <= 2.0 * 2.0 + 1e-12


@SETTINGS
@given(
    st.integers(0, 2**32 - 1),
    st.integers(1, 12),
    st.floats(0, 100),
    st.floats(0, 50),
    st.floats(0, 500),
    st.floats(0, 1),
    st.floats(0, 1e9),
)
def test_costs_never_negative(
    seed: int, n: int, bps: float, spread: float, borrow: float, k: float, aum: float
) -> None:
    rng = np.random.default_rng(seed)
    delta = rng.uniform(-2, 2, n)
    weights = rng.uniform(-1, 1, n)
    assert FlatBps(bps).trade_cost(delta) >= 0.0
    assert FlatBps(bps).holding_cost(weights) >= 0.0
    dates = pd.bdate_range("1990-01-01", periods=70)
    dh = DataHandler(dates, _names(n), rng.normal(0, 0.01, (70, n)))
    for _ in range(70):
        dh.advance()
    model = SpreadImpactBorrow(
        half_spread_bps=spread,
        commission_bps=spread / 2,
        borrow_bps_annual=borrow,
        impact_k=k,
        aum=aum,
        adv=rng.uniform(1e6, 1e9, n),
    )
    assert model.trade_cost(delta, dh.view()) >= 0.0
    assert model.holding_cost(weights) >= 0.0


class _Scaled:
    def __init__(self, inner: engine.SignalGenerator, k: float) -> None:
        self.inner, self.k = inner, k

    def on_market(self, ev: MarketEvent, view: AsOfView) -> SignalEvent | None:
        sig = self.inner.on_market(ev, view)
        return None if sig is None else SignalEvent(ts=sig.ts, weights=self.k * sig.weights)


@SETTINGS
@given(markets())
def test_doubling_targets_doubles_holding_period_gross(m: dict) -> None:
    """Between fills the book is buy-and-hold, so with RF = 0 the holding-period return
    Σ w_i (Π(1 + r_i) − 1) is linear in the weights."""
    if m["strategy"] == "b4":
        m["strategy"] = "b3"  # vol targeting rescales the book; the property is about targets
    n = m["rets"].shape[1]
    rets = np.nan_to_num(m["rets"])
    cfg = _cfg(m)
    out = []
    for k in (1.0, 2.0):
        dh = DataHandler(m["dates"], _names(n), rets)
        sig, _ = engine.build_strategy(cfg, dh.dates)
        out.append(engine.run_with(dh, _Scaled(sig, k), NoRisk(), FlatBps(0.0), cfg.fill_lag))
    one, two = out
    rows = [one.daily.index.get_loc(ts) for ts in one.fills["ts"]] + [len(one.daily) - 1]
    nav1, nav2 = one.daily["nav"].to_numpy(), two.daily["nav"].to_numpy()
    for a, b in zip(rows[:-1], rows[1:], strict=True):
        h1 = nav1[b] / nav1[a] - 1.0
        h2 = nav2[b] / nav2[a] - 1.0
        assert h2 == pytest.approx(2.0 * h1, abs=1e-12)
