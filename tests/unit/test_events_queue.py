"""E-1: event dataclasses and the time-ordered EventQueue."""

import dataclasses

import numpy as np
import pandas as pd
import pytest

from momlab.events import FillEvent, MarketEvent, OrderEvent, SignalEvent
from momlab.queue import EventOrderError, EventQueue

T0 = pd.Timestamp("2023-01-31")
T1 = pd.Timestamp("2023-02-01")


def _order(ts: pd.Timestamp = T0, oid: int = 1) -> OrderEvent:
    return OrderEvent(
        ts=ts, order_id=oid, target=np.array([0.5, -0.5]), delta=np.array([0.5, -0.5])
    )


def _fill(ts: pd.Timestamp = T1, oid: int = 1) -> FillEvent:
    return FillEvent(ts=ts, order_id=oid, delta=np.array([0.5, -0.5]), cost=0.001)


def test_events_are_frozen_and_arrays_read_only() -> None:
    ev = SignalEvent(ts=T0, weights=np.array([0.1, -0.1]))
    with pytest.raises(dataclasses.FrozenInstanceError):
        ev.ts = T1  # type: ignore[misc]
    with pytest.raises(ValueError, match="read-only"):
        ev.weights[0] = 9.0
    src = np.array([1.0, 2.0])
    o = OrderEvent(ts=T0, order_id=3, target=src, delta=src)
    src[0] = 99.0  # the event holds its own copy
    assert o.target[0] == 1.0
    assert MarketEvent(ts=T0).ts == T0
    assert _fill().cost == 0.001


def test_queue_pops_in_time_order() -> None:
    q = EventQueue()
    q.put(MarketEvent(ts=T0))
    q.put(SignalEvent(ts=T0, weights=np.zeros(2)))
    q.put(_order())
    assert len(q) == 3 and bool(q)
    kinds = [type(q.get()).__name__ for _ in range(3)]
    assert kinds == ["MarketEvent", "SignalEvent", "OrderEvent"]  # FIFO within a timestamp
    q.put(_fill())
    assert isinstance(q.get(), FillEvent)
    assert not q
    with pytest.raises(IndexError):
        q.get()


def test_out_of_order_event_raises() -> None:
    q = EventQueue()
    q.put(MarketEvent(ts=T1))
    q.get()
    with pytest.raises(EventOrderError, match="before the current time"):
        q.put(MarketEvent(ts=T0))


def test_fill_at_or_before_order_raises() -> None:
    q = EventQueue()
    q.put(_order(ts=T0, oid=7))
    q.get()
    with pytest.raises(EventOrderError, match="not after its order"):
        q.put(_fill(ts=T0, oid=7))
    q2 = EventQueue()
    q2.put(_order(ts=T1, oid=8))
    with pytest.raises(EventOrderError, match="not after its order"):
        q2.put(_fill(ts=T0, oid=8))


def test_fill_for_unknown_order_raises() -> None:
    q = EventQueue()
    with pytest.raises(EventOrderError, match="unknown order"):
        q.put(_fill(oid=42))


def test_duplicate_order_id_raises() -> None:
    q = EventQueue()
    q.put(_order(oid=1))
    with pytest.raises(EventOrderError, match="duplicate"):
        q.put(_order(oid=1))
