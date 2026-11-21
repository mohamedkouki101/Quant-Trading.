"""D-3: reconcile daily-compounded industry returns with the monthly file (PLAN §5.3 rule 4).

Usage: ``uv run python scripts/d3_reconcile.py`` (after ``uv run python tasks.py data``).
Writes ``reports/data_reconciliation.csv`` (row level, research period only, local only) and
``reports/data_reconciliation_summary.json`` (committed; the locked test period appears as
counts only). Exit code 1 when the criterion as written (>= 99.5% of industry-months within
1e-4) fails; Kouki decided on 2026-11-09 to record that failure rather than change the
criterion (DECISIONS 008).
"""

from __future__ import annotations

import json
import sys

import pandas as pd

from momlab import paths
from momlab.data import clean

TOL = 1e-4
MIN_SHARE = 0.995


def main() -> int:
    """Run the reconciliation and write the reports."""
    daily = pd.read_parquet(paths.PROCESSED_DIR / "industry_daily.parquet")
    monthly = pd.read_parquet(paths.PROCESSED_DIR / "industry_monthly.parquet")
    rows, summary = clean.reconcile_panels(daily, monthly, tol=TOL, min_share=MIN_SHARE)
    rows.rename(columns={"asset": "industry"}).to_csv(
        paths.REPORTS_DIR / "data_reconciliation.csv",
        index=False,
        lineterminator="\n",
        float_format="%.10g",
    )
    out_json = paths.REPORTS_DIR / "data_reconciliation_summary.json"
    with out_json.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n")
    for w in ("vw", "ew"):
        r, t = summary[w]["research"], summary[w]["test_period"]
        print(
            f"{w} research: compared {r['n_compared']}, within {r['n_within_tol']} "
            f"({r['share_within_tol']:.4%}), one side missing {r['n_one_side_missing']}, "
            f"max |diff| {r['max_abs_difference']:.2e} | test period: within {t['n_within_tol']} "
            f"of {t['n_compared']}"
        )
    o = summary["overall"]
    verdict = "PASS" if o["passed"] else "FAIL"
    print(
        f"criterion as written (all dates): {o['share_within_tol']:.4%} within {TOL} -> {verdict}"
    )
    return 0 if o["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
