"""E-5: rule signals (B1, B3/B4, B5) and risk (vol targeting, caps)."""

import math

import numpy as np
import pandas as pd
import pytest

from momlab.data.calendar import TradingCalendar
from momlab.data.handler import DataHandler
from momlab.events import MarketEvent
from momlab.portfolio import PortfolioState
from momlab.risk import CapsRisk, VolTargetRisk, apply_caps, vol_target_leverage
from momlab.signals.rules import EqualWeightSignal, MomentumSignal, momentum_score

# 15 month-ends, one trading day per month, so each daily return is that month's return.
MONTHS = pd.DatetimeIndex(pd.date_range("2000-01-31", periods=15, freq="BME"))


def _handler(rets: np.ndarray, dates: pd.DatetimeIndex = MONTHS) -> DataHandler:
    return DataHandler(dates, [f"a{i}" for i in range(rets.shape[1])], rets)


def _signal_at_end(sig: object, dh: DataHandler) -> object:
    out = None
    while (ev := dh.advance()) is not None:
        out = sig.on_market(ev, dh.view())  # type: ignore[attr-defined]
    return out


def test_mom_12_1_window() -> None:
    """L2: at the end of month 15 (holding month t = 16) the score is the product of months
    t-12 .. t-2 = months 4 .. 14 minus 1; month 15 (the skip month) and months 1-3 are out."""
    r = np.array([m / 100 for m in range(1, 16)])
    rets = np.column_stack([r, np.zeros(15)])
    dh = _handler(rets)
    for _ in range(15):
        dh.advance()
    score = momentum_score(dh.view(), lookback_months=12, skip_months=1)
    expected = math.prod(1 + m / 100 for m in range(4, 15)) - 1
    assert score is not None
    assert score[0] == pytest.approx(expected, rel=1e-14)
    assert score[1] == 0.0
    # Changing the skip month or months 1-3 does not change the score.
    for month in (0, 1, 2, 14):
        bumped = rets.copy()
        bumped[month, 0] = 0.5
        dh2 = _handler(bumped)
        for _ in range(15):
            dh2.advance()
        s2 = momentum_score(dh2.view(), 12, 1)
        assert s2 is not None and s2[0] == pytest.approx(expected, rel=1e-14)
    # Changing month 4 does.
    bumped = rets.copy()
    bumped[3, 0] = 0.5
    dh3 = _handler(bumped)
    for _ in range(15):
        dh3.advance()
    s3 = momentum_score(dh3.view(), 12, 1)
    assert s3 is not None and s3[0] != pytest.approx(expected, rel=1e-6)


def test_score_needs_full_history_and_excludes_missing() -> None:
    rets = np.full((15, 2), 0.01)
    rets[5, 1] = np.nan  # asset 1 has a missing month inside the window
    dh = _handler(rets)
    for _ in range(11):
        dh.advance()
    assert momentum_score(dh.view(), 12, 1) is None  # only 11 months so far
    dh.advance()
    s = momentum_score(dh.view(), 12, 1)
    assert s is not None and not math.isnan(s[0]) and math.isnan(s[1])
    with pytest.raises(ValueError, match="skip"):
        momentum_score(dh.view(), 1, 1)


def test_one_month_signal_and_sign() -> None:
    rets = np.zeros((15, 25))
    rets[-1] = np.arange(25) / 1000  # last month: asset i returned i/1000
    cal = TradingCalendar(MONTHS)
    cont = _signal_at_end(MomentumSignal(cal, 1, 0, n_per_leg=10, sign=1), _handler(rets))
    rev = _signal_at_end(MomentumSignal(cal, 1, 0, n_per_leg=10, sign=-1), _handler(rets))
    w_c = cont.weights  # type: ignore[attr-defined]
    w_r = rev.weights  # type: ignore[attr-defined]
    np.testing.assert_allclose(w_c[15:], 0.1, rtol=0, atol=1e-15)  # winners long
    np.testing.assert_allclose(w_c[:10], -0.1, rtol=0, atol=1e-15)  # losers short
    assert np.all(w_c[10:15] == 0.0)
    np.testing.assert_allclose(w_r, -w_c, rtol=0, atol=1e-15)
    assert w_c.sum() == pytest.approx(0.0, abs=1e-15)
    assert np.abs(w_c).sum() == pytest.approx(2.0, abs=1e-15)


def test_signal_only_on_rebalance_dates() -> None:
    days = pd.bdate_range("2000-01-03", "2000-02-29")
    rets = np.full((len(days), 25), 0.001)
    dh = _handler(rets, pd.DatetimeIndex(days))
    sig = MomentumSignal(TradingCalendar(pd.DatetimeIndex(days)), 1, 0, n_per_leg=10)
    emitted = []
    while (ev := dh.advance()) is not None:
        out = sig.on_market(ev, dh.view())
        if out is not None:
            emitted.append(out.ts)
    assert emitted == [pd.Timestamp("2000-01-31"), pd.Timestamp("2000-02-29")]


def test_too_few_valid_assets_gives_cash() -> None:
    rets = np.zeros((15, 25))
    rets[:, 5:] = np.nan  # only 5 valid assets < 2 * 10
    out = _signal_at_end(MomentumSignal(TradingCalendar(MONTHS), 12, 1, 10), _handler(rets))
    assert np.all(out.weights == 0.0)  # type: ignore[attr-defined]
    # Not enough history at all: no signal yet.
    dh = _handler(np.zeros((15, 25)))
    sig = MomentumSignal(TradingCalendar(MONTHS), 12, 1, 10)
    ev = dh.advance()
    assert ev is not None and sig.on_market(ev, dh.view()) is None


def test_equal_weight_b1() -> None:
    rets = np.full((15, 4), 0.01)
    rets[-1, 2] = np.nan  # asset 2 has no return on the rebalance day: left out
    out = _signal_at_end(EqualWeightSignal(TradingCalendar(MONTHS)), _handler(rets))
    np.testing.assert_allclose(out.weights, [1 / 3, 1 / 3, 0.0, 1 / 3], rtol=0, atol=1e-15)  # type: ignore[attr-defined]
    dh = _handler(np.full((15, 2), np.nan))
    ev = dh.advance()
    assert ev is not None
    assert EqualWeightSignal(TradingCalendar(MONTHS)).on_market(ev, dh.view()).weights.tolist() == [
        0.0,
        0.0,
    ]  # type: ignore[union-attr]
    assert (
        EqualWeightSignal(TradingCalendar(MONTHS)).on_market(
            MarketEvent(ts=pd.Timestamp("2000-01-15")), dh.view()
        )
        is None
    )


def _state(hist: list[float]) -> PortfolioState:
    return PortfolioState(
        ts=None, weights=np.zeros(2), unscaled=np.zeros(2), nav=1.0, unscaled_returns=hist
    )


def test_vol_target_constant_vol() -> None:
    """Alternating ±a: sample sd = a·sqrt(n/(n−1)); annualised × sqrt(252);
    leverage = 0.10 / that."""
    a, n = 0.005, 126
    hist = [a if i % 2 == 0 else -a for i in range(n)]
    vol = a * math.sqrt(n / (n - 1)) * math.sqrt(252)
    lev = vol_target_leverage(hist, target=0.10, window=n, cap=2.0)
    assert lev == pytest.approx(0.10 / vol, rel=1e-12)
    # Only the last `window` returns count.
    assert vol_target_leverage([0.5, -0.5, *hist], 0.10, n, 2.0) == pytest.approx(lev, rel=1e-12)
    # Cap respected: tiny vol -> leverage capped at 2.0; zero vol -> cap.
    tiny = [1e-6 if i % 2 == 0 else -1e-6 for i in range(n)]
    assert vol_target_leverage(tiny, 0.10, n, 2.0) == 2.0
    assert vol_target_leverage([0.0] * n, 0.10, n, 2.0) == 2.0
    # Warm-up: fewer than `window` returns -> 0 (hold cash).
    assert vol_target_leverage(hist[:-1], 0.10, n, 2.0) == 0.0


def test_vol_target_risk_scales_unscaled_target() -> None:
    a, n = 0.005, 126
    hist = [a if i % 2 == 0 else -a for i in range(n)]
    risk = VolTargetRisk(target=0.10, window=n, cap=2.0)
    w = risk.apply(np.array([0.1, -0.1]), _state(hist))
    lev = 0.10 / (a * math.sqrt(n / (n - 1)) * math.sqrt(252))
    np.testing.assert_allclose(w, [0.1 * lev, -0.1 * lev], rtol=1e-12)


def test_caps() -> None:
    w = np.array([0.6, 0.3, -0.1])
    # Position cap 0.5 clips the first weight: [0.5, 0.3, -0.1].
    np.testing.assert_allclose(
        apply_caps(w, position_cap=0.5), [0.5, 0.3, -0.1], rtol=0, atol=1e-15
    )
    # Gross cap 0.5 on gross 1.0 halves everything.
    np.testing.assert_allclose(apply_caps(w, gross_cap=0.5), w * 0.5, rtol=0, atol=1e-15)
    # Net cap 0.4 on net 0.8 halves everything.
    np.testing.assert_allclose(apply_caps(w, net_cap=0.4), w * 0.5, rtol=0, atol=1e-15)
    np.testing.assert_array_equal(apply_caps(w), w)
    np.testing.assert_array_equal(CapsRisk().apply(w, _state([])), w)
    np.testing.assert_allclose(
        CapsRisk(gross_cap=0.5).apply(w, _state([])), w * 0.5, rtol=0, atol=1e-15
    )
