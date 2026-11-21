"""Factor regressions with HAC (Newey-West) standard errors, task E-7.

Typical use: monthly strategy *excess* returns on ``mkt_rf, smb, hml, mom, st_rev`` from
``factors_monthly.parquet``. Both inputs are decimal returns; rows are matched on dates and
rows with any NaN are dropped.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import statsmodels.api as sm


@dataclass(frozen=True)
class RegressionResult:
    """Alpha (per period, decimal), betas, HAC t-stats (keys ``const`` and factor names),
    observation count and R²."""

    alpha: float
    betas: dict[str, float]
    tstats: dict[str, float]
    nobs: int
    r2: float
    hac_lags: int


def factor_regression(r: pd.Series, factors: pd.DataFrame, hac_lags: int) -> RegressionResult:
    """OLS of ``r`` on a constant and ``factors`` with ``cov_type="HAC"``."""
    data = pd.concat([r.rename("__y"), factors], axis=1, join="inner").dropna()
    x = sm.add_constant(data[list(factors.columns)], has_constant="add")
    fit = sm.OLS(data["__y"], x).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})
    params = fit.params
    return RegressionResult(
        alpha=float(params["const"]),
        betas={str(c): float(params[c]) for c in factors.columns},
        tstats={str(k): float(v) for k, v in fit.tvalues.items()},
        nobs=int(fit.nobs),
        r2=float(fit.rsquared),
        hac_lags=hac_lags,
    )
