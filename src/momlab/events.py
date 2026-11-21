"""Event dataclasses for the event-driven engine (task E-1, PLAN §3.3).

All events are frozen. Weight vectors are NumPy arrays in the data handler's asset order
(fractions of NAV); each event stores its own read-only copy, so no later code can change what
an event said. Timestamps are trading-day closes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt
import pandas as pd

FloatArray = npt.NDArray[np.float64]


def _frozen_copy(a: npt.ArrayLike) -> FloatArray:
    out = np.array(a, dtype=np.float64, copy=True)
    out.flags.writeable = False
    return out


@dataclass(frozen=True)
class MarketEvent:
    """A new bar closed at ``ts``."""

    ts: pd.Timestamp


@dataclass(frozen=True)
class SignalEvent:
    """Unscaled target weights decided at the close of ``ts`` from data <= ``ts``. Risk rules
    (vol targeting, caps) are applied afterwards by the portfolio's risk manager."""

    ts: pd.Timestamp
    weights: FloatArray

    def __post_init__(self) -> None:
        object.__setattr__(self, "weights", _frozen_copy(self.weights))


@dataclass(frozen=True)
class OrderEvent:
    """Order created at the close of ``ts``: trade to ``target`` (weights after risk rules).
    ``delta`` is target minus the drifted weights at ``ts`` (an estimate; the fill trades to
    ``target`` from the weights at the fill). ``unscaled`` is the target before leverage."""

    ts: pd.Timestamp
    order_id: int
    target: FloatArray
    delta: FloatArray
    unscaled: FloatArray | None = field(default=None)

    def __post_init__(self) -> None:
        object.__setattr__(self, "target", _frozen_copy(self.target))
        object.__setattr__(self, "delta", _frozen_copy(self.delta))
        if self.unscaled is not None:
            object.__setattr__(self, "unscaled", _frozen_copy(self.unscaled))


@dataclass(frozen=True)
class FillEvent:
    """Order ``order_id`` filled at the close of ``ts``: ``delta`` is the weight actually
    traded and ``cost`` the trading cost as a fraction of pre-fill NAV."""

    ts: pd.Timestamp
    order_id: int
    delta: FloatArray
    cost: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "delta", _frozen_copy(self.delta))


Event = MarketEvent | SignalEvent | OrderEvent | FillEvent
