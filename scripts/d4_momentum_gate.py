"""D-4: momentum sanity gate (task D-4, correction C9). Hypothetical backtest, not investment
advice.

A vectorised 12-1 industry long-short on the Ken French 49 value-weighted *monthly* file:
at the end of month t−1, score each industry by its compounded return over months t−12 … t−2
(the skip month t−1 is left out; an industry with any missing month in the window gets no
score), go long the top 10 and short the bottom 10 with equal weights, and earn month t. The
holding months are 1927-07 … 2005-12 only (research period). The series is correlated with
the published Mom factor (stock-level, so a different universe: a sanity check, not equality).

Usage: ``uv run python scripts/d4_momentum_gate.py``. Prints the correlation and the hand check,
saves ``reports/d4_gate.png``. Writes nothing to ``results/`` and nothing to the ledger.
Exit code 0 when the correlation is > 0.5, 2 when it is in [0.3, 0.5] (ask Kouki), 1 below.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from momlab import paths

START, END = "1927-07-01", "2005-12-31"
N_PER_LEG = 10
HAND_CHECK = ("Steel", "1950-07-31")


def mom_12_1(wide: pd.DataFrame) -> pd.DataFrame:
    """Score for holding month t (row t): Π(1 + R) over rows t−12 … t−2, minus 1; NaN when
    any of those 11 months is missing or there is not enough history."""
    growth = np.log1p(wide)
    window = growth.shift(2).rolling(11, min_periods=11).sum()
    return np.expm1(window)


def long_short(wide: pd.DataFrame, n: int = N_PER_LEG) -> pd.Series:
    """Equal-weight top-n minus bottom-n return in each month that has ≥ 2n scored assets."""
    score = mom_12_1(wide)
    out = {}
    for ts in score.index:
        s = score.loc[ts].dropna()
        if len(s) < 2 * n:
            continue
        ranked = s.sort_values(ascending=False, kind="stable").index
        r = wide.loc[ts]
        out[ts] = float(r[ranked[:n]].mean() - r[ranked[-n:]].mean())
    return pd.Series(out, name="ls_12_1", dtype="float64")


def main() -> int:
    """Run the gate and print the evidence."""
    panel = pd.read_parquet(paths.PROCESSED_DIR / "industry_monthly.parquet")
    panel = panel[(panel["weighting"] == "vw") & (panel["date"] <= pd.Timestamp(END))]
    wide = panel.pivot(index="date", columns="asset", values="ret")  # noqa: PD010
    ls = long_short(wide)
    ls = ls[(ls.index >= pd.Timestamp(START)) & (ls.index <= pd.Timestamp(END))]
    mom = pd.read_parquet(paths.PROCESSED_DIR / "factors_monthly.parquet").set_index("date")["mom"]
    both = pd.concat([ls, mom.rename("mom")], axis=1, join="inner").dropna()
    corr = float(both["ls_12_1"].corr(both["mom"]))

    asset, month = HAND_CHECK
    t = wide.index.get_loc(pd.Timestamp(month))
    window = wide[asset].iloc[t - 12 : t - 1]
    hand = float(np.prod(1.0 + window.to_numpy()) - 1.0)
    code = float(mom_12_1(wide)[asset].iloc[t])

    print(
        f"D-4 momentum sanity gate (hypothetical backtest): {both.index[0].date()} to "
        f"{both.index[-1].date()}, {len(both)} months"
    )
    print(f"correlation(own 12-1 industry L/S, published Mom) = {corr:.4f}")
    print(
        f"hand check {asset}, holding month {month}: window {window.index[0].date()} .. "
        f"{window.index[-1].date()} ({len(window)} months)"
    )
    print("  monthly returns:", ", ".join(f"{x:.4f}" for x in window))
    print(
        f"  prod(1+R) - 1 by hand = {hand:.10f}; mom_12_1 = {code:.10f}; skip month "
        f"{wide.index[t - 1].date()} return {wide[asset].iloc[t - 1]:.4f} not used"
    )

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot(np.log1p(both["ls_12_1"]).cumsum(), label="own 12-1 industry L/S (gross)", lw=1)
    ax.plot(np.log1p(both["mom"]).cumsum(), label="published Mom factor", lw=1)
    ax.set_ylabel("cumulative log return")
    ax.set_title(
        f"D-4 sanity gate, {both.index[0]:%Y-%m}–{both.index[-1]:%Y-%m}: corr {corr:.2f}",
        fontsize=10,
    )
    ax.legend(fontsize=8)
    fig.text(0.01, 0.01, "Hypothetical backtest, not investment advice.", fontsize=7)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    out = paths.REPORTS_DIR / "d4_gate.png"
    fig.savefig(out, dpi=120)
    print(f"saved {out}")

    if corr > 0.5:
        print("GATE: pass (> 0.5)")
        return 0
    if corr >= 0.3:
        print("GATE: between 0.3 and 0.5 -> write down likely reasons and ask Kouki")
        return 2
    print("GATE: FAIL (< 0.3) -> timing is probably wrong; debug before any other task")
    return 1


if __name__ == "__main__":
    sys.exit(main())
