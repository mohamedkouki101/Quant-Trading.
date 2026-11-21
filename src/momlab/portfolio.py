"""Portfolio: weights, drift, daily P&L, fills and turnover (task E-3).

Weights are fractions of NAV in the data handler's asset order; the rest (1 − Σw) is cash
earning the daily risk-free rate. Conventions (DECISIONS 010):

- Day t gross return ``R = Σ w_i r_i + (1 − Σ w_i)·rf`` with the weights held into t. A missing
  return on a held asset counts as 0 for that day and is counted.
- A holding cost ``h`` (e.g. borrow, fraction of NAV) is charged the same day; the growth factor
  is ``g = 1 + R − h`` and weights drift to ``w_i (1 + r_i) / g``.
- A fill sets the weights to the order's target exactly and multiplies NAV by ``1 − cost``.
- The *unscaled* strategy weights (the signal's target before risk scaling) are tracked the
  same way, from the first fill on, and their daily returns ``Σ u_i r_i`` feed vol targeting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np
import numpy.typing as npt
import pandas as pd

from momlab.events import FillEvent, OrderEvent, SignalEvent

FloatArray = npt.NDArray[np.float64]


@dataclass(frozen=True)
class PortfolioState:
    """Snapshot of the portfolio after the last event."""

    ts: pd.Timestamp | None
    weights: FloatArray
    unscaled: FloatArray
    nav: float
    unscaled_returns: list[float] = field(default_factory=list)


@dataclass(frozen=True)
class DayRecord:
    """What happened to the portfolio on one bar (before any fill at that bar's close)."""

    ts: pd.Timestamp
    gross: float
    holding: float
    n_missing_held: int


class RiskManager(Protocol):
    """Turns an unscaled target into the weights to trade to."""

    def apply(self, unscaled: FloatArray, state: PortfolioState) -> FloatArray: ...


class NoRisk:
    """Risk manager that passes the target through unchanged."""

    def apply(self, unscaled: FloatArray, state: PortfolioState) -> FloatArray:
        """Return ``unscaled`` as is."""
        return unscaled


class Portfolio:
    """Holds weights and NAV; see the module docstring for the accounting rules."""

    def __init__(self, n_assets: int, nav: float = 1.0) -> None:
        self._w = np.zeros(n_assets)
        self._u = np.zeros(n_assets)
        self._started = False
        self._nav = nav
        self._u_hist: list[float] = []
        self._ts: pd.Timestamp | None = None
        self._pending: dict[int, OrderEvent] = {}
        self.last_turnover = 0.0

    @property
    def state(self) -> PortfolioState:
        """Copy of the current state."""
        return PortfolioState(
            ts=self._ts,
            weights=self._w.copy(),
            unscaled=self._u.copy(),
            nav=self._nav,
            unscaled_returns=list(self._u_hist),
        )

    def on_market(
        self, ts: pd.Timestamp, bar_returns: FloatArray, rf: float, holding_cost: float = 0.0
    ) -> DayRecord:
        """Mark to market with the returns of bar ``ts`` and drift the weights."""
        missing = np.isnan(bar_returns)
        r = np.where(missing, 0.0, bar_returns)
        n_missing_held = int(np.count_nonzero(missing & (self._w != 0.0)))
        gross = float(self._w @ r + (1.0 - self._w.sum()) * rf)
        g = 1.0 + gross - holding_cost
        if g <= 0.0:
            raise RuntimeError(f"NAV wiped out on {ts} (growth factor {g})")
        self._w = self._w * (1.0 + r) / g
        self._nav *= g
        if self._started:
            u_ret = float(self._u @ r)
            self._u_hist.append(u_ret)
            self._u = self._u * (1.0 + r) / (1.0 + u_ret)
        self._ts = ts
        return DayRecord(ts=ts, gross=gross, holding=holding_cost, n_missing_held=n_missing_held)

    def turnover(self, target: FloatArray) -> float:
        """Σ|target − current (drifted) weights|."""
        return float(np.abs(target - self._w).sum())

    def on_signal(self, ev: SignalEvent, order_id: int, risk: RiskManager) -> OrderEvent:
        """Apply the risk rules to the signal and create an order to trade to the result."""
        target = risk.apply(np.asarray(ev.weights, dtype=np.float64), self.state)
        order = OrderEvent(
            ts=ev.ts, order_id=order_id, target=target, delta=target - self._w, unscaled=ev.weights
        )
        self._pending[order_id] = order
        return order

    def on_fill(self, ev: FillEvent) -> None:
        """Set the weights to the filled order's target and pay the trading cost."""
        order = self._pending.pop(ev.order_id)
        self.last_turnover = float(np.abs(ev.delta).sum())
        self._nav *= 1.0 - ev.cost
        self._w = np.array(order.target, dtype=np.float64)
        if order.unscaled is not None:
            self._u = np.array(order.unscaled, dtype=np.float64)
            self._started = True
        self._ts = ev.ts
