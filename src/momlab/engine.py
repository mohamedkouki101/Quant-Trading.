"""Event loop (task E-6): ``run(config) -> RunResult`` following PLAN §3.2.

For each bar t (a trading-day close):

1. ``DataHandler.advance()`` moves the cursor to t and emits ``MarketEvent(t)``.
2. ``Portfolio.on_market`` marks the positions held into t with t's returns (and charges the
   day's holding cost).
3. Orders due at t fill at t's close (``ExecutionSimulator``, ``fill_lag`` bars after the order).
4. On rebalance dates the signal gets an ``AsOfView`` (rows <= t only) and emits a target.
5. ``Portfolio.on_signal`` applies the risk rules and creates an order sized from the
   positions after step 2; the order is queued and fills at the close of t + fill_lag, so the
   new positions earn returns from t + fill_lag + 1.

All events go through the time-ordered ``EventQueue``. Hypothetical backtests only.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Protocol

import numpy as np
import numpy.typing as npt
import pandas as pd

from momlab.config import RunConfig
from momlab.costs import CostModel, FlatBps, SpreadImpactBorrow
from momlab.data.calendar import TradingCalendar
from momlab.data.handler import AsOfView, DataHandler
from momlab.events import FillEvent, MarketEvent, OrderEvent, SignalEvent
from momlab.execution import ExecutionSimulator
from momlab.ledger import Ledger, make_entry, manifest_hash
from momlab.portfolio import Portfolio, RiskManager
from momlab.queue import EventQueue
from momlab.risk import CapsRisk, VolTargetRisk
from momlab.signals.rules import EqualWeightSignal, MomentumSignal

FloatArray = npt.NDArray[np.float64]


class SignalGenerator(Protocol):
    """Anything that turns a bar and an as-of view into an optional target."""

    def on_market(self, ev: MarketEvent, view: AsOfView) -> SignalEvent | None: ...


@dataclass(frozen=True)
class RunResult:
    """Output of one run. ``daily`` (index = date) has ``gross``, ``holding_cost``,
    ``trade_cost``, ``net`` (all decimal returns or fractions of NAV), ``turnover`` (Σ|Δw|),
    ``nav`` and ``n_missing_held``; ``weights`` are end-of-day weights after fills."""

    config_hash: str
    daily: pd.DataFrame
    weights: pd.DataFrame
    signals: dict[pd.Timestamp, FloatArray]
    orders: pd.DataFrame
    fills: pd.DataFrame
    n_missing_held: int


def build_cost_model(config: RunConfig) -> CostModel:
    """Cost model named in the config."""
    c = config.cost
    if c.model == "flat":
        return FlatBps(c.bps)
    return SpreadImpactBorrow(
        half_spread_bps=c.half_spread_bps,
        commission_bps=c.commission_bps,
        borrow_bps_annual=c.borrow_bps_annual,
        impact_k=c.impact_k,
        aum=c.aum,
    )


def build_strategy(
    config: RunConfig, dates: pd.DatetimeIndex
) -> tuple[SignalGenerator, RiskManager]:
    """Signal and risk manager for B1, B3, B4 or B5."""
    cal = TradingCalendar(dates)
    caps = {
        "gross_cap": config.gross_cap,
        "net_cap": config.net_cap,
        "position_cap": config.position_cap,
    }
    signal: SignalGenerator
    if config.strategy == "b1":
        signal = EqualWeightSignal(cal)
    else:
        sign = config.signal_sign if config.strategy == "b5" else 1
        signal = MomentumSignal(
            cal, config.lookback_months, config.skip_months, config.n_per_leg, sign=sign
        )
    risk: RiskManager
    if config.strategy == "b4":
        risk = VolTargetRisk(config.vol_target, config.vol_window, config.leverage_cap, **caps)
    else:
        risk = CapsRisk(**caps)
    return signal, risk


def run_with(
    handler: DataHandler,
    signal: SignalGenerator,
    risk: RiskManager,
    cost_model: CostModel,
    fill_lag: int,
    config_hash: str = "",
) -> RunResult:
    """Run the event loop over every bar of ``handler``."""
    n_assets = len(handler.assets)
    portfolio = Portfolio(n_assets)
    execution = ExecutionSimulator(fill_lag, cost_model)
    queue = EventQueue()
    order_ids = itertools.count(1)
    rows: list[dict[str, float | int]] = []
    weights: list[FloatArray] = []
    dates: list[pd.Timestamp] = []
    signals: dict[pd.Timestamp, FloatArray] = {}
    orders: list[dict[str, object]] = []
    fills: list[dict[str, object]] = []

    while (bar := handler.advance()) is not None:
        nav_before = portfolio.state.nav
        day: dict[str, float | int] = {"trade_cost": 0.0, "turnover": 0.0}
        queue.put(bar)
        while queue:
            ev = queue.get()
            if isinstance(ev, MarketEvent):
                view = handler.view()
                held = portfolio.state.weights
                rec = portfolio.on_market(
                    ev.ts,
                    handler.bar_returns(ev.ts),
                    handler.bar_rf(ev.ts),
                    cost_model.holding_cost(held),
                )
                day.update(
                    gross=rec.gross, holding_cost=rec.holding, n_missing_held=rec.n_missing_held
                )
                for fill in execution.on_market(ev, view, portfolio.state.weights):
                    queue.put(fill)
                sig = signal.on_market(ev, view)
                if sig is not None:
                    queue.put(sig)
            elif isinstance(ev, FillEvent):
                portfolio.on_fill(ev)
                day["trade_cost"] = float(day["trade_cost"]) + ev.cost
                day["turnover"] = float(day["turnover"]) + portfolio.last_turnover
                fills.append({"ts": ev.ts, "order_id": ev.order_id, "cost": ev.cost})
            elif isinstance(ev, SignalEvent):
                signals[ev.ts] = ev.weights
                order = portfolio.on_signal(ev, next(order_ids), risk)
                queue.put(order)
            else:
                assert isinstance(ev, OrderEvent)
                execution.on_order(ev)
                orders.append(
                    {
                        "ts": ev.ts,
                        "order_id": ev.order_id,
                        "target": ev.target,
                        "unscaled": ev.unscaled,
                    }
                )
        state = portfolio.state
        day["nav"] = state.nav
        day["net"] = state.nav / nav_before - 1.0
        rows.append(day)
        weights.append(state.weights)
        dates.append(bar.ts)

    index = pd.DatetimeIndex(dates, name="date")
    daily = pd.DataFrame(rows, index=index)[
        ["gross", "holding_cost", "trade_cost", "net", "turnover", "nav", "n_missing_held"]
    ]
    return RunResult(
        config_hash=config_hash,
        daily=daily,
        weights=pd.DataFrame(
            np.array(weights).reshape(len(dates), n_assets),
            index=index,
            columns=list(handler.assets),
        ),
        signals=signals,
        orders=pd.DataFrame(orders, columns=["ts", "order_id", "target", "unscaled"]),
        fills=pd.DataFrame(fills, columns=["ts", "order_id", "cost"]),
        n_missing_held=int(daily["n_missing_held"].sum()),
    )


def run(
    config: RunConfig,
    handler: DataHandler | None = None,
    *,
    log: bool = False,
    ledger: Ledger | None = None,
    notes: str = "",
) -> RunResult:
    """Run the strategy in ``config``; data comes from ``data/processed`` unless a handler is
    given (synthetic tests). With ``log=True`` the run is appended to the trial ledger
    (default ``experiments/ledger.jsonl``) with its metrics; every research run from P4 on
    must be logged (DECISIONS 013)."""
    from_disk = handler is None
    if handler is None:
        handler = DataHandler.from_processed(config.weighting, start=config.start, end=config.end)
    signal, risk = build_strategy(config, handler.dates)
    result = run_with(
        handler, signal, risk, build_cost_model(config), config.fill_lag, config.config_hash()
    )
    if log:
        rf = pd.Series([handler.bar_rf(d) for d in handler.dates], index=handler.dates)
        entry = make_entry(
            config,
            result,
            rf,
            manifest_hash=manifest_hash() if from_disk else None,
            notes=notes,
        )
        (ledger if ledger is not None else Ledger()).append(entry)
    return result
