"""Cost models in weight units (task E-4, PLAN §3.4).

``trade_cost`` returns the cost of a trade ``delta`` (change in weights) as a fraction of NAV;
``holding_cost`` returns the cost of holding ``weights`` for one day as a fraction of NAV.
Costs are never negative. 1 bp = 0.0001.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

import numpy as np
import numpy.typing as npt

if TYPE_CHECKING:
    from momlab.data.handler import AsOfView

FloatArray = npt.NDArray[np.float64]
BP = 1e-4
DAYS_PER_YEAR = 252


class CostModel(Protocol):
    """Interface every cost model implements."""

    def trade_cost(self, delta: FloatArray, view: AsOfView | None = None) -> float: ...

    def holding_cost(self, weights: FloatArray) -> float: ...


class FlatBps:
    """Flat one-way cost: ``bps × Σ|Δw|`` (industry leg; no impact, no borrow)."""

    def __init__(self, bps: float) -> None:
        if bps < 0:
            raise ValueError("bps must be >= 0")
        self.bps = float(bps)

    def trade_cost(self, delta: FloatArray, view: AsOfView | None = None) -> float:
        """Cost of trading ``delta`` as a fraction of NAV."""
        return self.bps * BP * float(np.abs(delta).sum())

    def holding_cost(self, weights: FloatArray) -> float:
        """No holding cost."""
        return 0.0


class SpreadImpactBorrow:
    """ETF-leg costs (PLAN §3.4).

    Trade: ``Σ |Δw_i| × (half_spread_i + commission + impact_i)`` with square-root impact
    ``impact_i = k × σ_i × sqrt(|Δw_i| × AUM / ADV_i)``; ``σ_i`` is the sample standard
    deviation of asset i's daily returns over the last ``sigma_window`` bars of the view
    (data <= now only). Holding: daily borrow on short notional, ``borrow / 252 × Σ max(−w_i, 0)``.
    """

    def __init__(
        self,
        half_spread_bps: float | FloatArray = 0.0,
        commission_bps: float = 0.0,
        borrow_bps_annual: float = 0.0,
        impact_k: float = 0.0,
        aum: float = 0.0,
        adv: FloatArray | None = None,
        sigma_window: int = 63,
    ) -> None:
        hs = np.asarray(half_spread_bps, dtype=np.float64)
        if (hs < 0).any() or min(commission_bps, borrow_bps_annual, impact_k, aum) < 0:
            raise ValueError("cost parameters must be non-negative")
        self.uses_impact = impact_k > 0 and aum > 0
        if self.uses_impact and adv is None:
            raise ValueError("impact needs adv (average daily dollar volume per asset)")
        self.half_spread = hs * BP
        self.commission = commission_bps * BP
        self.borrow_daily = borrow_bps_annual * BP / DAYS_PER_YEAR
        self.impact_k = impact_k
        self.aum = aum
        self.adv = None if adv is None else np.asarray(adv, dtype=np.float64)
        self.sigma_window = sigma_window

    def trade_cost(self, delta: FloatArray, view: AsOfView | None = None) -> float:
        """Cost of trading ``delta`` as a fraction of NAV (``view`` needed for impact)."""
        size = np.abs(delta)
        per_unit = self.half_spread + self.commission
        if self.uses_impact:
            if view is None:
                raise ValueError("impact needs the as-of view for trailing volatility")
            assert self.adv is not None
            sigma = np.nanstd(view.returns(self.sigma_window), axis=0, ddof=1)
            per_unit = per_unit + self.impact_k * sigma * np.sqrt(size * self.aum / self.adv)
        return float((size * per_unit).sum())

    def holding_cost(self, weights: FloatArray) -> float:
        """One day of borrow on the short side."""
        return self.borrow_daily * float(np.clip(-weights, 0.0, None).sum())
