"""E-3: portfolio drift, P&L, fills and turnover (hand-computed expected values)."""

import numpy as np
import pandas as pd
import pytest

from momlab.events import FillEvent, SignalEvent
from momlab.portfolio import NoRisk, Portfolio, PortfolioState

T = pd.date_range("2023-01-02", periods=4, freq="B")


def _fill_to(
    p: Portfolio, target: list[float], ts: pd.Timestamp, oid: int = 1, cost: float = 0.0
) -> None:
    order = p.on_signal(SignalEvent(ts=ts, weights=np.array(target)), oid, NoRisk())
    delta = order.target - p.state.weights
    p.on_fill(FillEvent(ts=ts + pd.Timedelta(days=1), order_id=oid, delta=delta, cost=cost))


def test_drift_half_half() -> None:
    """0.5/0.5 with +10%/-10% -> portfolio return 0 -> weights 0.55/0.45."""
    p = Portfolio(2)
    _fill_to(p, [0.5, 0.5], T[0])
    day = p.on_market(T[1], np.array([0.10, -0.10]), rf=0.0)
    assert day.gross == pytest.approx(0.0, abs=1e-15)
    np.testing.assert_allclose(p.state.weights, [0.55, 0.45], rtol=0, atol=1e-15)


def test_cash_earns_rf() -> None:
    # w = 0.5 in one asset, 0.5 cash; r = 2%, rf = 0.1% -> R = 0.5*0.02 + 0.5*0.001 = 0.0105
    p = Portfolio(1)
    _fill_to(p, [0.5], T[0])
    day = p.on_market(T[1], np.array([0.02]), rf=0.001)
    assert day.gross == pytest.approx(0.0105, abs=1e-15)
    assert p.state.weights[0] == pytest.approx(0.5 * 1.02 / 1.0105, abs=1e-15)
    assert p.state.nav == pytest.approx(1.0105, abs=1e-15)


def test_long_short_earns_spread_plus_rf() -> None:
    # +0.5 / -0.5, r = +1% / -1%, rf = 0.02% -> R = 0.005 + 0.005 + 1.0*0.0002 = 0.0102
    p = Portfolio(2)
    _fill_to(p, [0.5, -0.5], T[0])
    assert p.on_market(T[1], np.array([0.01, -0.01]), rf=0.0002).gross == pytest.approx(
        0.0102, abs=1e-15
    )


def test_turnover_from_drifted_weights() -> None:
    """Rebalancing back to 0.5/0.5 after the drift trades 0.1 in total, not 0 (which a
    comparison with the previous target would wrongly give)."""
    p = Portfolio(2)
    _fill_to(p, [0.5, 0.5], T[0])
    p.on_market(T[1], np.array([0.10, -0.10]), rf=0.0)
    order = p.on_signal(SignalEvent(ts=T[1], weights=np.array([0.5, 0.5])), 2, NoRisk())
    np.testing.assert_allclose(order.delta, [-0.05, 0.05], rtol=0, atol=1e-15)
    assert p.turnover(order.target) == pytest.approx(0.1, abs=1e-15)


def test_fill_sets_target_and_charges_cost() -> None:
    p = Portfolio(2)
    _fill_to(p, [0.2, -0.2], T[0], cost=0.0004)
    np.testing.assert_array_equal(p.state.weights, [0.2, -0.2])
    assert p.state.nav == pytest.approx(0.9996, abs=1e-15)
    assert p.last_turnover == pytest.approx(0.4, abs=1e-15)


def test_holding_cost_reduces_nav_and_scales_drift() -> None:
    # w = -0.5 (short), r = 0, rf = 0, holding cost h = 0.0001 -> g = 0.9999
    p = Portfolio(1)
    _fill_to(p, [-0.5], T[0])
    day = p.on_market(T[1], np.array([0.0]), rf=0.0, holding_cost=0.0001)
    assert day.holding == 0.0001
    assert p.state.nav == pytest.approx(0.9999, abs=1e-15)
    assert p.state.weights[0] == pytest.approx(-0.5 / 0.9999, abs=1e-15)


def test_missing_return_on_held_asset_earns_zero_and_is_counted() -> None:
    p = Portfolio(2)
    _fill_to(p, [0.5, 0.5], T[0])
    day = p.on_market(T[1], np.array([np.nan, 0.02]), rf=0.0)
    assert day.n_missing_held == 1
    assert day.gross == pytest.approx(0.01, abs=1e-15)
    # A missing return on an asset that is not held is not counted.
    p2 = Portfolio(2)
    _fill_to(p2, [1.0, 0.0], T[0])
    assert p2.on_market(T[1], np.array([0.01, np.nan]), rf=0.0).n_missing_held == 0


def test_unscaled_history_starts_at_first_fill() -> None:
    p = Portfolio(2)
    p.on_market(T[0], np.array([0.01, 0.02]), rf=0.0)
    assert p.state.unscaled_returns == []
    order = p.on_signal(SignalEvent(ts=T[0], weights=np.array([0.5, -0.5])), 1, NoRisk())
    assert order.unscaled is not None
    p.on_fill(FillEvent(ts=T[1], order_id=1, delta=order.target - p.state.weights, cost=0.0))
    p.on_market(T[2], np.array([0.02, 0.0]), rf=0.0)
    # u = [0.5, -0.5]: u.r = 0.01 ; drift u -> [0.5*1.02, -0.5] / 1.01
    assert p.state.unscaled_returns == pytest.approx([0.01], abs=1e-15)
    np.testing.assert_allclose(p.state.unscaled, [0.51 / 1.01, -0.5 / 1.01], rtol=0, atol=1e-15)


def test_unknown_fill_and_wipeout_raise() -> None:
    p = Portfolio(1)
    with pytest.raises(KeyError):
        p.on_fill(FillEvent(ts=T[1], order_id=99, delta=np.zeros(1), cost=0.0))
    _fill_to(p, [2.0], T[0])
    with pytest.raises(RuntimeError, match="NAV"):
        p.on_market(T[1], np.array([-0.6]), rf=0.0)


def test_state_is_a_snapshot() -> None:
    p = Portfolio(2)
    s = p.state
    assert isinstance(s, PortfolioState)
    _fill_to(p, [0.5, 0.5], T[0])
    assert s.weights.tolist() == [0.0, 0.0]
