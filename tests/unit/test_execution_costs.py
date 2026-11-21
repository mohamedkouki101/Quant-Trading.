"""E-4: execution timing (fill_lag) and cost models (hand-computed expected values)."""

import math

import numpy as np
import pandas as pd
import pytest

from momlab.costs import FlatBps, SpreadImpactBorrow
from momlab.data.handler import DataHandler
from momlab.events import MarketEvent, SignalEvent
from momlab.execution import ExecutionSimulator
from momlab.portfolio import NoRisk, Portfolio

DATES = pd.date_range("2001-01-01", periods=5, freq="B")
RETS = np.array(
    [[0.00, 0.00], [0.01, 0.02], [0.03, -0.01], [0.02, 0.02], [-0.01, 0.01]], dtype=np.float64
)


def _run(fill_lag: int) -> tuple[list[float], list[pd.Timestamp]]:
    """Signal [0.5, 0.5] at the close of bar 0; return daily gross P&L and fill dates."""
    dh = DataHandler(DATES, ["A", "B"], RETS)
    p = Portfolio(2)
    ex = ExecutionSimulator(fill_lag=fill_lag, cost_model=FlatBps(0.0))
    gross, fills = [], []
    while (ev := dh.advance()) is not None:
        gross.append(p.on_market(ev.ts, dh.bar_returns(ev.ts), dh.bar_rf(ev.ts)).gross)
        for fill in ex.on_market(ev, dh.view(), p.state.weights):
            p.on_fill(fill)
            fills.append(fill.ts)
        if ev.ts == DATES[0]:
            ex.on_order(
                p.on_signal(SignalEvent(ts=ev.ts, weights=np.array([0.5, 0.5])), 1, NoRisk())
            )
    return gross, fills


def test_order_at_t_fills_at_t_plus_1_and_earns_from_t_plus_2() -> None:
    gross, fills = _run(fill_lag=1)
    assert fills == [DATES[1]]
    # Bars 0 and 1 earn nothing (no position yet / filled at bar 1's close).
    # Bar 2: 0.5*0.03 + 0.5*(-0.01) = 0.01. Bar 3: weights drifted to 0.515/0.495 over 1.01:
    # (0.515*0.02 + 0.495*0.02)/1.01 = 0.02. Bar 4 then follows from the drifted weights.
    assert gross[0] == 0.0 and gross[1] == 0.0
    assert gross[2] == pytest.approx(0.01, abs=1e-15)
    assert gross[3] == pytest.approx(0.02, abs=1e-15)


def test_fill_lag_two() -> None:
    gross, fills = _run(fill_lag=2)
    assert fills == [DATES[2]]
    assert gross[:3] == [0.0, 0.0, 0.0]
    assert gross[3] == pytest.approx(0.02, abs=1e-15)  # 0.5*0.02 + 0.5*0.02


def test_fill_lag_must_be_positive() -> None:
    with pytest.raises(ValueError, match="fill_lag"):
        ExecutionSimulator(fill_lag=0, cost_model=FlatBps(10.0))


def test_fill_trades_to_target_from_drifted_weights_and_charges_cost() -> None:
    dh = DataHandler(DATES, ["A", "B"], RETS)
    ex = ExecutionSimulator(fill_lag=1, cost_model=FlatBps(10.0))
    p = Portfolio(2)
    ev0 = dh.advance()
    assert ev0 is not None
    assert ex.on_market(ev0, dh.view(), p.state.weights) == []
    ex.on_order(p.on_signal(SignalEvent(ts=ev0.ts, weights=np.array([0.2, -0.2])), 7, NoRisk()))
    assert ex.pending == 1
    ev1 = dh.advance()
    assert ev1 is not None
    (fill,) = ex.on_market(ev1, dh.view(), np.array([0.0, 0.0]))
    assert fill.order_id == 7 and fill.ts == DATES[1]
    np.testing.assert_array_equal(fill.delta, [0.2, -0.2])
    assert fill.cost == pytest.approx(0.0004, abs=1e-18)
    assert ex.pending == 0


def test_two_orders_due_on_the_same_bar_fill_in_sequence() -> None:
    dh = DataHandler(DATES, ["A", "B"], RETS)
    ex = ExecutionSimulator(fill_lag=1, cost_model=FlatBps(10.0))
    p = Portfolio(2)
    ev0 = dh.advance()
    assert ev0 is not None
    ex.on_market(ev0, dh.view(), p.state.weights)
    ex.on_order(p.on_signal(SignalEvent(ts=ev0.ts, weights=np.array([0.5, 0.0])), 1, NoRisk()))
    ex.on_order(p.on_signal(SignalEvent(ts=ev0.ts, weights=np.array([0.2, 0.0])), 2, NoRisk()))
    ev1 = dh.advance()
    assert ev1 is not None
    f1, f2 = ex.on_market(ev1, dh.view(), np.zeros(2))
    np.testing.assert_allclose(f2.delta, [-0.3, 0.0], rtol=0, atol=1e-15)  # from the first target
    assert (f1.order_id, f2.order_id) == (1, 2)


def test_flat_bps() -> None:
    """Δw = [+0.2, −0.2] at 10 bp costs (0.2 + 0.2) × 0.001 = 0.0004."""
    c = FlatBps(10.0)
    assert c.trade_cost(np.array([0.2, -0.2])) == pytest.approx(0.0004, abs=1e-18)
    assert c.holding_cost(np.array([0.5, -0.5])) == 0.0
    with pytest.raises(ValueError, match="bps"):
        FlatBps(-1.0)


def test_borrow_accrues_daily_on_shorts_only() -> None:
    c = SpreadImpactBorrow(half_spread_bps=0.0, commission_bps=0.0, borrow_bps_annual=100.0)
    # 0.5 short at 1% a year: 0.5 * 0.01 / 252 per day.
    assert c.holding_cost(np.array([0.5, -0.5])) == pytest.approx(0.5 * 0.01 / 252, abs=1e-18)
    assert c.holding_cost(np.array([0.7, 0.3])) == 0.0


def test_spread_and_commission() -> None:
    # Δ = [0.1, -0.2], half-spreads [2, 4] bp, commission 1 bp:
    # 0.1 * 3e-4 + 0.2 * 5e-4 = 3e-5 + 1e-4 = 1.3e-4
    c = SpreadImpactBorrow(half_spread_bps=np.array([2.0, 4.0]), commission_bps=1.0)
    assert c.trade_cost(np.array([0.1, -0.2])) == pytest.approx(1.3e-4, abs=1e-18)


def test_square_root_impact() -> None:
    # Daily returns A: +1%, -1% -> sample sd = sqrt(2e-4) ; B: +2%, -2% -> sqrt(8e-4)
    dates = pd.date_range("2001-01-01", periods=2, freq="B")
    dh = DataHandler(dates, ["A", "B"], np.array([[0.01, 0.02], [-0.01, -0.02]]))
    dh.advance()
    dh.advance()
    c = SpreadImpactBorrow(
        half_spread_bps=0.0, impact_k=0.5, aum=1e6, adv=np.array([1e8, 4e8]), sigma_window=2
    )
    delta = np.array([0.1, -0.2])
    sig_a, sig_b = math.sqrt(2e-4), math.sqrt(8e-4)
    expected = 0.1 * 0.5 * sig_a * math.sqrt(0.1 * 1e6 / 1e8) + 0.2 * 0.5 * sig_b * math.sqrt(
        0.2 * 1e6 / 4e8
    )
    assert c.trade_cost(delta, dh.view()) == pytest.approx(expected, rel=1e-14)
    with pytest.raises(ValueError, match="view"):
        c.trade_cost(delta)


def test_costs_never_negative() -> None:
    rng = np.random.default_rng(0)
    flat = FlatBps(5.0)
    sib = SpreadImpactBorrow(half_spread_bps=3.0, commission_bps=1.0, borrow_bps_annual=50.0)
    for _ in range(200):
        d = rng.normal(size=5)
        assert flat.trade_cost(d) >= 0.0
        assert sib.trade_cost(d) >= 0.0
        assert sib.holding_cost(d) >= 0.0


def test_spread_model_validation() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        SpreadImpactBorrow(half_spread_bps=-1.0)
    with pytest.raises(ValueError, match="adv"):
        SpreadImpactBorrow(impact_k=1.0, aum=1e6)


def test_market_event_type() -> None:
    assert MarketEvent(ts=DATES[0]).ts == DATES[0]
