"""Risk rules (task E-5): volatility targeting and gross / net / position caps.

Vol targeting (B4, DECISIONS 010): leverage = min(target / σ, cap), with σ the sample standard
deviation (ddof 1) of the last ``window`` daily returns of the *unscaled* strategy, annualised
with √252. Only returns up to and including the current bar are in the state (L9). Before
``window`` returns exist the leverage is 0 (cash).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

from momlab.portfolio import PortfolioState

FloatArray = npt.NDArray[np.float64]
DAYS_PER_YEAR = 252


def vol_target_leverage(
    unscaled_returns: Sequence[float], target: float, window: int, cap: float
) -> float:
    """Leverage that scales the unscaled strategy to ``target`` annualised vol, capped."""
    if len(unscaled_returns) < window:
        return 0.0
    recent = np.asarray(unscaled_returns[-window:], dtype=np.float64)
    sigma = float(np.std(recent, ddof=1)) * math.sqrt(DAYS_PER_YEAR)
    if sigma == 0.0:
        return cap
    return min(target / sigma, cap)


def apply_caps(
    w: FloatArray,
    gross_cap: float | None = None,
    net_cap: float | None = None,
    position_cap: float | None = None,
) -> FloatArray:
    """Clip each |w_i| to ``position_cap``, then scale down to meet ``gross_cap`` (Σ|w|) and
    ``net_cap`` (|Σw|). Scaling down never breaks an earlier cap."""
    out = np.asarray(w, dtype=np.float64)
    if position_cap is not None:
        out = np.clip(out, -position_cap, position_cap)
    if gross_cap is not None:
        gross = float(np.abs(out).sum())
        if gross > gross_cap:
            out = out * (gross_cap / gross)
    if net_cap is not None:
        net = abs(float(out.sum()))
        if net > net_cap:
            out = out * (net_cap / net)
    return out


class CapsRisk:
    """Caps only (no vol targeting); with no caps set it passes the target through."""

    def __init__(
        self,
        gross_cap: float | None = None,
        net_cap: float | None = None,
        position_cap: float | None = None,
    ) -> None:
        self.gross_cap = gross_cap
        self.net_cap = net_cap
        self.position_cap = position_cap

    def apply(self, unscaled: FloatArray, state: PortfolioState) -> FloatArray:
        """Apply the caps to the target."""
        return apply_caps(unscaled, self.gross_cap, self.net_cap, self.position_cap)


class VolTargetRisk(CapsRisk):
    """B4: scale the unscaled target by the vol-target leverage, then apply the caps."""

    def __init__(
        self,
        target: float,
        window: int,
        cap: float,
        gross_cap: float | None = None,
        net_cap: float | None = None,
        position_cap: float | None = None,
    ) -> None:
        super().__init__(gross_cap, net_cap, position_cap)
        self.target = target
        self.window = window
        self.cap = cap

    def apply(self, unscaled: FloatArray, state: PortfolioState) -> FloatArray:
        """Scaled and capped target weights."""
        lev = vol_target_leverage(state.unscaled_returns, self.target, self.window, self.cap)
        return super().apply(unscaled * lev, state)
