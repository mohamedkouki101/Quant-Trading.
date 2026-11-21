"""EventQueue with time-order assertions (task E-1).

Events come out in non-decreasing timestamp order (first in, first out within a timestamp).
Putting an event earlier than the last event taken out raises, and a ``FillEvent`` must be
strictly later than the ``OrderEvent`` with the same ``order_id``.
"""

from __future__ import annotations

import heapq
import itertools

import pandas as pd

from momlab.events import Event, FillEvent, OrderEvent


class EventOrderError(RuntimeError):
    """An event would break the time order of the simulation."""


class EventQueue:
    """Priority queue of events keyed by ``(ts, insertion order)``."""

    def __init__(self) -> None:
        self._heap: list[tuple[pd.Timestamp, int, Event]] = []
        self._seq = itertools.count()
        self._now: pd.Timestamp | None = None
        self._order_ts: dict[int, pd.Timestamp] = {}

    def put(self, ev: Event) -> None:
        """Add an event; raise ``EventOrderError`` if it would go back in time."""
        if self._now is not None and ev.ts < self._now:
            raise EventOrderError(
                f"{type(ev).__name__} at {ev.ts} is before the current time {self._now}"
            )
        if isinstance(ev, OrderEvent):
            if ev.order_id in self._order_ts:
                raise EventOrderError(f"duplicate order_id {ev.order_id}")
            self._order_ts[ev.order_id] = ev.ts
        elif isinstance(ev, FillEvent):
            if ev.order_id not in self._order_ts:
                raise EventOrderError(f"fill for unknown order {ev.order_id}")
            if ev.ts <= self._order_ts[ev.order_id]:
                raise EventOrderError(
                    f"fill at {ev.ts} is not after its order at {self._order_ts[ev.order_id]}"
                )
        heapq.heappush(self._heap, (ev.ts, next(self._seq), ev))

    def get(self) -> Event:
        """Remove and return the earliest event (raises ``IndexError`` when empty)."""
        ts, _, ev = heapq.heappop(self._heap)
        self._now = ts
        return ev

    def __len__(self) -> int:
        return len(self._heap)

    def __bool__(self) -> bool:
        return bool(self._heap)
