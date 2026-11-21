"""ExecutionSimulator (task E-4): orders fill at the close of bar ``t + fill_lag``.

The simulator counts bars itself. An order received after bar t's close is due at bar
``t + fill_lag``; at that close it trades to the order's target from the weights the portfolio
holds then (drifted), and the cost model prices the traded Δw. Several orders due on the same
bar fill in the order they arrived, each from the previous one's target.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt

from momlab.events import FillEvent, MarketEvent, OrderEvent

if TYPE_CHECKING:
    from momlab.costs import CostModel
    from momlab.data.handler import AsOfView

FloatArray = npt.NDArray[np.float64]


class ExecutionSimulator:
    """Queue of orders with a fixed fill lag in bars (``fill_lag >= 1``)."""

    def __init__(self, fill_lag: int, cost_model: CostModel) -> None:
        if fill_lag < 1:
            raise ValueError("fill_lag must be >= 1")
        self.fill_lag = fill_lag
        self.cost_model = cost_model
        self._bar = -1
        self._queue: list[tuple[int, OrderEvent]] = []

    @property
    def pending(self) -> int:
        """Number of orders not yet filled."""
        return len(self._queue)

    def on_order(self, ev: OrderEvent) -> None:
        """Queue an order created at the close of the current bar."""
        self._queue.append((self._bar + self.fill_lag, ev))

    def on_market(self, ev: MarketEvent, view: AsOfView, weights: FloatArray) -> list[FillEvent]:
        """Advance one bar and fill every order due at this close."""
        self._bar += 1
        due = [o for bar, o in self._queue if bar == self._bar]
        self._queue = [(bar, o) for bar, o in self._queue if bar != self._bar]
        fills = []
        current = np.asarray(weights, dtype=np.float64)
        for order in due:
            delta = order.target - current
            cost = self.cost_model.trade_cost(delta, view)
            fills.append(FillEvent(ts=ev.ts, order_id=order.order_id, delta=delta, cost=cost))
            current = np.asarray(order.target, dtype=np.float64)
        return fills
