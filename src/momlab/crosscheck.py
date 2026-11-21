"""Cross-check of the engine against bt 1.4.1 (task V-3, PLAN §9.3 step 2).

Hypothetical backtests only. bt is a development dependency and is imported lazily.

The engine's fill-date targets are fed to bt (``WeighTarget`` + ``Rebalance``) on price
indices built from the same returns (missing returns count as 0, as the engine does for held
assets), with ``commissions = |q|·p·bps/1e4`` and fractional positions. Cash earns nothing in
bt, so the engine also runs with RF = 0 here.

Known difference, cause (b) in PLAN §9.3: bt sizes each trade from the pre-trade value V and
takes the commission out of the trade. A position moving to a non-zero target gets
``A / (1 ± b)`` for an amount ``A = (w − u)·V`` while cash pays ``A`` (``b = bps/1e4``, + for buys,
− for sells); a position closed to zero is sold in full and the fee is paid from the proceeds.
The engine instead trades exactly to the target and charges ``bps·Σ|Δw|`` to NAV. The
comparison builds a replica of bt's rule (:func:`bt_convention`); if bt equals the replica to
floating point, cause (b) explains the whole gap. Cash residuals (c) do not arise with
fractional positions.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import pandas as pd

from momlab import engine
from momlab.analytics import metrics
from momlab.config import RunConfig
from momlab.data.handler import DataHandler
from momlab.synthetic import Market

FloatArray = npt.NDArray[np.float64]


@dataclass(frozen=True)
class BtCheck:
    """Gaps between engine and bt daily net returns from the first fill on.

    ``ann_gap_bp``: engine minus bt annual return (bp/yr); ``corr``: daily correlation;
    ``max_abs_gap``: largest daily difference; ``weight_dev``: largest ``|w_bt − target|`` right
    after a fill; ``sizing_error``: largest ``|w_bt − w_replica|`` after a fill;
    ``*_bt_convention``: bt vs the replica of bt's rule."""

    n_days: int
    ann_gap_bp: float
    corr: float
    max_abs_gap: float
    weight_dev: float
    sizing_error: float
    max_abs_gap_bt_convention: float
    ann_gap_bt_convention_bp: float


def fill_targets(result: engine.RunResult, assets: list[str]) -> pd.DataFrame:
    """Target weights indexed by fill date (the order's target, shifted to its fill)."""
    targets = dict(zip(result.orders["order_id"], result.orders["target"], strict=True))
    rows = [np.asarray(targets[o], dtype=np.float64) for o in result.fills["order_id"]]
    return pd.DataFrame(rows, index=pd.DatetimeIndex(result.fills["ts"]), columns=assets)


def order_targets(result: engine.RunResult, assets: list[str]) -> pd.DataFrame:
    """The same targets indexed by the order date (what a naive bt user would pass)."""
    rows = [np.asarray(t, dtype=np.float64) for t in result.orders["target"]]
    return pd.DataFrame(rows, index=pd.DatetimeIndex(result.orders["ts"]), columns=assets)


def run_bt(market: Market, weights: pd.DataFrame, bps: float) -> tuple[pd.Series, pd.DataFrame]:
    """bt daily returns (on ``market.dates``) and its end-of-day security weights."""
    import bt

    rets = np.nan_to_num(market.returns)
    prices = pd.DataFrame(
        100.0 * np.cumprod(1.0 + rets, axis=0), index=market.dates, columns=market.assets
    )
    strat = bt.Strategy("engine_targets", [bt.algos.WeighTarget(weights), bt.algos.Rebalance()])

    def commissions(q: float, p: float) -> float:
        return abs(q) * p * bps / 1e4

    test = bt.Backtest(strat, prices, commissions=commissions, integer_positions=False)
    out = bt.run(test).backtests["engine_targets"]
    daily = out.strategy.prices.pct_change().reindex(market.dates)
    sw = out.security_weights.reindex(index=market.dates, columns=market.assets).fillna(0.0)
    return daily, sw


def bt_convention(
    market: Market, weights: pd.DataFrame, bps: float
) -> tuple[FloatArray, dict[pd.Timestamp, FloatArray]]:
    """Replica of bt's trading rule (module docstring); cash earns 0. Returns daily returns and
    the end-of-day weights on each fill date."""
    rets = np.nan_to_num(market.returns)
    b = bps / 1e4
    pos = dict(zip(pd.DatetimeIndex(weights.index), weights.to_numpy(), strict=True))
    hold = np.zeros(rets.shape[1])
    cash, value = 1.0, 1.0
    out = np.zeros(len(market.dates))
    after: dict[pd.Timestamp, FloatArray] = {}
    for t, ts in enumerate(market.dates):
        hold = hold * (1.0 + rets[t])
        base = cash + hold.sum()
        if ts in pos:
            target = pos[ts]
            amount = target * base - hold
            closing = target == 0.0
            fee_close = b * np.abs(hold[closing]).sum()
            cash += hold[closing].sum() - fee_close
            hold[closing] = 0.0
            trade = ~closing & (amount != 0.0)
            cash -= amount[trade].sum()
            hold[trade] += amount[trade] / (1.0 + b * np.sign(amount[trade]))
            after[ts] = hold / (cash + hold.sum())
        new_value = cash + hold.sum()
        out[t] = new_value / value - 1.0
        value = new_value
    return out, after


def bt_crosscheck(config: RunConfig, market: Market, *, shift: bool = True) -> BtCheck:
    """Run the engine (RF = 0) and bt on ``market`` and measure the gaps."""
    if config.cost.model != "flat":
        raise ValueError("the bt cross-check uses flat costs")
    bps = config.cost.bps
    dh = DataHandler(market.dates, market.assets, market.returns, rf=np.zeros(len(market.dates)))
    res = engine.run(config, dh)
    fills = fill_targets(res, market.assets)
    fed = fills if shift else order_targets(res, market.assets)
    bt_daily, bt_w = run_bt(market, fed, bps)
    replica, rep_w = bt_convention(market, fills, bps)
    sel = market.dates >= fills.index[0]
    eng = res.daily["net"].to_numpy()[sel]
    btr = bt_daily.to_numpy()[sel]
    rep = replica[sel]
    bt_at_fills = bt_w.reindex(pd.DatetimeIndex(fills.index)).to_numpy()
    weight_dev = float(np.abs(bt_at_fills - fills.to_numpy()).max())
    rep_at_fills = np.vstack([rep_w[ts] for ts in pd.DatetimeIndex(fills.index)])
    sizing = float(np.abs(bt_at_fills - rep_at_fills).max())

    def ann(x: FloatArray) -> float:
        return metrics.annual_return(pd.Series(x), freq="D")

    return BtCheck(
        n_days=int(sel.sum()),
        ann_gap_bp=(ann(eng) - ann(btr)) * 1e4,
        corr=float(np.corrcoef(eng, btr)[0, 1]),
        max_abs_gap=float(np.abs(eng - btr).max()),
        weight_dev=weight_dev,
        sizing_error=sizing,
        max_abs_gap_bt_convention=float(np.abs(rep - btr).max()),
        ann_gap_bt_convention_bp=(ann(rep) - ann(btr)) * 1e4,
    )
