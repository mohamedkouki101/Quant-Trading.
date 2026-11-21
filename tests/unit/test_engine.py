"""E-6: engine loop, hand-computed trades, engine vs oracle, poisoned future."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momlab import engine, oracle
from momlab.config import CostConfig, RunConfig
from momlab.costs import FlatBps, SpreadImpactBorrow
from momlab.data.handler import AsOfView, DataHandler
from momlab.events import MarketEvent, SignalEvent
from momlab.portfolio import NoRisk

FIX = Path(__file__).resolve().parents[1] / "fixtures"


class ScheduleSignal:
    """Emits fixed targets on given dates (test helper)."""

    def __init__(self, schedule: dict[pd.Timestamp, list[float]]) -> None:
        self.schedule = schedule

    def on_market(self, ev: MarketEvent, view: AsOfView) -> SignalEvent | None:
        if ev.ts in self.schedule:
            return SignalEvent(ts=ev.ts, weights=np.array(self.schedule[ev.ts]))
        return None


def test_hand_computed_trades_3x6() -> None:
    hand = pd.read_csv(FIX / "hand_trades_3x6.csv", parse_dates=["date"])
    dates = pd.DatetimeIndex(hand["date"])
    rets = hand[["ret_X", "ret_Y", "ret_Z"]].to_numpy()
    dh = DataHandler(dates, ["X", "Y", "Z"], rets, rf=hand["rf"].to_numpy())
    sched = {
        dates[0]: [0.5, 0.3, -0.2],
        dates[2]: [0.2, 0.2, 0.2],
        dates[4]: [-0.1, 0.4, 0.0],
    }
    res = engine.run_with(dh, ScheduleSignal(sched), NoRisk(), FlatBps(10.0), fill_lag=1)
    d = res.daily
    for col in ("gross", "turnover", "trade_cost", "net", "nav"):
        np.testing.assert_allclose(d[col].to_numpy(), hand[col].to_numpy(), rtol=0, atol=1e-12)
    np.testing.assert_allclose(
        res.weights.to_numpy(), hand[["w_X", "w_Y", "w_Z"]].to_numpy(), rtol=0, atol=1e-12
    )
    assert list(res.fills["ts"]) == [dates[1], dates[3], dates[5]]
    assert list(res.orders["ts"]) == [dates[0], dates[2], dates[4]]
    assert res.n_missing_held == 0


def _market(
    seed: int = 3, n_assets: int = 30, years: int = 5
) -> tuple[pd.DatetimeIndex, np.ndarray, np.ndarray]:
    """Synthetic daily market (before 2006, so the vault does not cut it) with missing data:
    two assets start late and a few isolated days are missing."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("1990-01-01", periods=252 * years)
    drift = rng.normal(0.0003, 0.0004, n_assets)
    rets = drift + rng.standard_t(5, size=(len(dates), n_assets)) * 0.01
    rets[:300, 0] = np.nan
    rets[:450, 1] = np.nan
    for i, j in zip(rng.integers(0, len(dates), 8), rng.integers(2, n_assets, 8), strict=True):
        rets[i, j] = np.nan
    rf = np.full(len(dates), 0.00015)
    return pd.DatetimeIndex(dates), rets, rf


def _config(strategy: str, bps: float) -> RunConfig:
    extra: dict[str, object] = {}
    if strategy == "b5":
        extra = {"lookback_months": 1, "skip_months": 0, "signal_sign": -1}
    return RunConfig(
        strategy=strategy,  # type: ignore[arg-type]
        start="1990-01-01",  # type: ignore[arg-type]
        end="2005-12-31",  # type: ignore[arg-type]
        n_per_leg=5,
        vol_window=63,
        cost=CostConfig(model="flat", bps=bps),
        **extra,  # type: ignore[arg-type]
    )


@pytest.mark.parametrize("strategy", ["b1", "b3", "b4", "b5"])
@pytest.mark.parametrize("bps", [0.0, 10.0])
def test_engine_equals_oracle_synthetic(strategy: str, bps: float) -> None:
    dates, rets, rf = _market()
    assets = [f"a{i}" for i in range(rets.shape[1])]
    cfg = _config(strategy, bps)
    res = engine.run(cfg, DataHandler(dates, assets, rets, rf=rf))
    ora = oracle.run_oracle(cfg, dates, rets, rf)
    assert len(res.fills) > 10
    for col in ("gross", "net"):
        diff = np.abs(res.daily[col].to_numpy() - ora[col].to_numpy())
        assert diff.max() <= 1e-10, (col, diff.max())
    np.testing.assert_allclose(
        res.weights.to_numpy(), ora.filter(like="w_").to_numpy(), rtol=0, atol=1e-10
    )


def test_b4_waits_for_vol_history() -> None:
    dates, rets, rf = _market()
    res = engine.run(
        _config("b4", 0.0), DataHandler(dates, [f"a{i}" for i in range(30)], rets, rf=rf)
    )
    first_order = res.orders.iloc[0]
    assert np.all(np.asarray(first_order["target"]) == 0.0)  # warm-up: cash
    assert any(np.abs(np.asarray(t)).sum() > 0 for t in res.orders["target"])


class _RecordSignal:
    def __init__(self, inner: object) -> None:
        self.inner = inner
        self.out: list[tuple[pd.Timestamp, np.ndarray]] = []

    def on_market(self, ev: MarketEvent, view: AsOfView) -> SignalEvent | None:
        sig = self.inner.on_market(ev, view)  # type: ignore[attr-defined]
        if sig is not None:
            self.out.append((sig.ts, sig.weights))
        return sig


class _RecordRisk:
    def __init__(self, inner: object) -> None:
        self.inner = inner
        self.out: list[tuple[pd.Timestamp, np.ndarray]] = []

    def apply(self, unscaled: np.ndarray, state: object) -> np.ndarray:
        target = self.inner.apply(unscaled, state)  # type: ignore[attr-defined]
        self.out.append((state.ts, target))  # type: ignore[attr-defined]
        return np.asarray(target)


def _decisions(cfg: RunConfig, dh: DataHandler) -> tuple[list, list, str]:
    signal, risk = engine.build_strategy(cfg, dh.dates)
    rs, rr = _RecordSignal(signal), _RecordRisk(risk)
    outcome = "completed"
    try:
        engine.run_with(dh, rs, rr, engine.build_cost_model(cfg), cfg.fill_lag)
    except RuntimeError as exc:  # a +1000% day can wipe out a long-short book after t
        assert "wiped out" in str(exc)
        outcome = str(exc)
    return rs.out, rr.out, outcome


@pytest.mark.parametrize("strategy", ["b1", "b3", "b4", "b5"])
@pytest.mark.parametrize("poison", ["nan", "plus1000"])
def test_poisoned_future(strategy: str, poison: str) -> None:
    """L1, L9: replacing every return after t (with NaN, or with +1000%) changes no decision
    (signal or risk-adjusted target) made up to t."""
    dates, rets, rf = _market(seed=11)
    assets = [f"a{i}" for i in range(rets.shape[1])]
    cfg = _config(strategy, 10.0)
    cut = 900
    t = dates[cut]
    bad = rets.copy()
    bad[cut + 1 :] = np.nan if poison == "nan" else 10.0
    sig_a, risk_a, _ = _decisions(cfg, DataHandler(dates, assets, rets, rf=rf))
    sig_b, risk_b, outcome = _decisions(cfg, DataHandler(dates, assets, bad, rf=rf))
    if outcome != "completed":
        assert pd.Timestamp(outcome.split(" on ")[1].split(" (")[0]) > t
    sa = [(ts, w) for ts, w in sig_a if ts <= t]
    sb = [(ts, w) for ts, w in sig_b if ts <= t]
    ra = [(ts, w) for ts, w in risk_a if ts <= t]
    rb = [(ts, w) for ts, w in risk_b if ts <= t]
    assert len(sa) == len(sb) > 5 and len(ra) == len(rb) == len(sa)
    for (ta, wa), (tb, wb) in zip(sa + ra, sb + rb, strict=True):
        assert ta == tb and np.array_equal(wa, wb)  # bit-identical


def test_daily_results_up_to_t_unchanged_by_nan_future() -> None:
    dates, rets, rf = _market(seed=11)
    assets = [f"a{i}" for i in range(rets.shape[1])]
    bad = rets.copy()
    bad[901:] = np.nan
    a = engine.run(_config("b4", 10.0), DataHandler(dates, assets, rets, rf=rf))
    b = engine.run(_config("b4", 10.0), DataHandler(dates, assets, bad, rf=rf))
    upto = a.daily.index <= dates[900]
    assert np.array_equal(a.daily.loc[upto].to_numpy(), b.daily.loc[upto].to_numpy())


def test_missing_returns_on_held_assets_are_counted() -> None:
    dates, rets, rf = _market()
    res = engine.run(
        _config("b1", 0.0), DataHandler(dates, [f"a{i}" for i in range(30)], rets, rf=rf)
    )
    assert res.n_missing_held > 0
    assert res.config_hash == _config("b1", 0.0).config_hash()


def test_holding_cost_enters_net() -> None:
    dates = pd.bdate_range("2001-01-01", periods=4)
    rets = np.zeros((4, 2))
    dh = DataHandler(dates, ["A", "B"], rets)
    cost = SpreadImpactBorrow(borrow_bps_annual=252.0)  # 1 bp a day on short notional
    res = engine.run_with(dh, ScheduleSignal({dates[0]: [0.5, -0.5]}), NoRisk(), cost, fill_lag=1)
    # Day 2: short 0.5 pays 0.5 * 1e-4 = 5e-5, so g = 1 - 5e-5 and the weights drift to
    # +-0.5 / (1 - 5e-5). Day 3 pays 1e-4 * 0.5 / (1 - 5e-5). Zero returns, zero rf.
    h2 = 5e-5
    h3 = 1e-4 * 0.5 / (1 - 5e-5)
    np.testing.assert_allclose(res.daily["holding_cost"].to_numpy()[2:], [h2, h3], rtol=1e-12)
    np.testing.assert_allclose(res.daily["net"].to_numpy()[2:], [-h2, -h3], rtol=1e-12)


def test_builders() -> None:
    c = RunConfig(
        cost=CostConfig(model="spread_impact_borrow", half_spread_bps=2.0, borrow_bps_annual=50.0)
    )
    model = engine.build_cost_model(c)
    assert isinstance(model, SpreadImpactBorrow)
    assert isinstance(engine.build_cost_model(RunConfig()), FlatBps)
    c2 = RunConfig(strategy="b3", gross_cap=1.0)
    dates, rets, rf = _market(years=2)
    cal_dh = DataHandler(dates, [f"a{i}" for i in range(30)], rets, rf=rf)
    sig, risk = engine.build_strategy(c2, cal_dh.dates)
    assert risk.apply(np.array([1.0, -1.0]), None).tolist() == [0.5, -0.5]  # type: ignore[arg-type]
    assert sig is not None


def test_run_loads_processed_data_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    dates, rets, rf = _market(years=2)
    seen: dict[str, object] = {}

    def fake_from_processed(weighting: str, **kw: object) -> DataHandler:
        seen.update(weighting=weighting, **kw)
        return DataHandler(dates, [f"a{i}" for i in range(30)], rets, rf=rf)

    monkeypatch.setattr(DataHandler, "from_processed", staticmethod(fake_from_processed))
    res = engine.run(_config("b1", 0.0))
    assert seen["weighting"] == "vw"
    assert str(seen["start"]) == "1990-01-01"
    assert len(res.daily) == len(dates)


def test_oracle_rejects_unsupported_settings() -> None:
    dates, rets, rf = _market(years=2)
    with pytest.raises(NotImplementedError):
        oracle.run_oracle(RunConfig(cost=CostConfig(model="spread_impact_borrow")), dates, rets, rf)
    with pytest.raises(NotImplementedError):
        oracle.run_oracle(RunConfig(gross_cap=1.0), dates, rets, rf)


def test_oracle_has_no_engine_imports() -> None:
    src = (Path(oracle.__file__)).read_text(encoding="utf-8")
    for mod in (
        "momlab.engine",
        "momlab.portfolio",
        "momlab.execution",
        "momlab.data.handler",
        "momlab.signals",
        "momlab.risk",
    ):
        assert mod not in src
