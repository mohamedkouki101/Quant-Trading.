# Pre-registration (v1)

Project: momentum-lab. Author: Kouki. Version 1, written 2026-11-08 in task S-4, **before any
strategy return has been computed**. Hypothetical backtests only, not investment advice.

Rules for this file:

- After Kouki commits it and tags `prereg-v1`, nothing above the "Deviations" section changes.
  Its sha256 is recorded in `README.md`.
- A v2 addendum (task T-1) freezes the final configurations before the locked test period is
  opened. v2 is added below v1; it does not rewrite v1.
- Any later departure from this document is written in "Deviations" with date, what changed,
  why, and whether it was decided before or after seeing a result.

## 1. Hypotheses, baselines, thresholds and null-result presentation

Sections 1.1 to 1.4 copy `docs/plan/PLAN.md` §2.1 to §2.4 word for word (headings keep their
original numbers).

### 2.1 Hypotheses

| ID | Hypothesis (why the edge might exist) | Primary metric | What would kill it |
|---|---|---|---|
| H1 | Vol-scaled 12-1 industry momentum, long top 10 / short bottom 10 of 49, earns a positive return net of 10 bp one-way costs. Mechanism: slow diffusion of industry-wide news and investor under-reaction; risk-based stories (crash exposure) also exist ([Moskowitz & Grinblatt 1999](https://ideas.repec.org/a/bla/jfinan/v54y1999i4p1249-1290.html); [Daniel & Moskowitz 2016](https://www.nber.org/papers/w20439)). High (that the effect was documented); Medium (mechanism). | Annualised net Sharpe and Newey-West t-stat of monthly net returns | Arbitrage after publication ([McLean & Pontiff](https://academicnewsletter.sufe.edu.cn/info/359722)), crowding, costs above break-even, crash in rebounds |
| H2 | Vol scaling raises Sharpe and cuts the worst month vs unscaled 12-1 ([Barroso & Santa-Clara 2015](https://econpapers.repec.org/RePEc:eee:jfinec:v:116:y:2015:i:1:p:111-120)). High. | Sharpe difference (scaled minus unscaled), worst month | Vol forecasts failing in sudden regime shifts |
| H3 | A LightGBM ranker on 19 features beats vol-scaled 12-1 net of costs. Pre-registered expectation: **probably not by much** ([Nagel 2025](https://www.nber.org/papers/w34104)). Medium. | Net Sharpe difference with a block-bootstrap CI | Nagel's critique; overfitting; higher turnover eating the gain |
| H4 | The 1-month industry signal has a non-zero sign (two-sided: continuation or reversal). Unverified which. | Long-short return t-stat at 0 and 10 bp | Costs; it is a known liquidity effect at stock level ([Avramov et al. 2006](https://ideas.repec.org/a/bla/jfinan/v61y2006i5p2365-2394.html)) |
| H5 | In the ML model, the momentum feature group ranks first by grouped held-out permutation importance in most folds, consistent with [Gu, Kelly & Xiu 2020](https://nber.org/papers/w25398). High (their finding); the transfer to industries is Unverified. | Share of folds where momentum group ranks first | Importance spread evenly or unstable across folds |
| H6 | The edge survives on tradable sector ETFs at measured costs. Unverified. | ETF net Sharpe at measured spread + borrow | Only 9 assets; short sample; higher costs |

### 2.2 Baselines (every model must be compared to all of these, net of the same costs)

B0 cash (risk-free from Ken French daily RF); B1 equal-weight all industries, monthly rebalance; B2 published Ken French Mom factor (reference, stock-level); B3 plain 12-1 industry momentum; B4 vol-scaled 12-1; B5 1-month signal (sign chosen on research period only); B6 shuffled-label LightGBM (null model); B7 ridge regression on the same features.

### 2.3 Thresholds (set now; never promised as outcomes)

| Claim | Threshold | Notes |
|---|---|---|
| "Signal exists" (research period 1927–2005) | Newey-West t > 3.0 on net monthly returns at 10 bp ([Harvey, Liu & Zhu](https://www.nber.org/papers/w20592), High) | t between 2 and 3 is reported as "suggestive" |
| "Survives selection" | DSR ≥ 0.95 using all trials in the ledger ([Bailey & López de Prado](https://papers.ssrn.com/abstract=2460551), High); PBO < 0.5 ([Bailey et al.](https://papers.ssrn.com/abstract=2326253), High) | |
| "Holds out of sample" (locked test 2006-01 to 2026-09) | Point estimate of net Sharpe > 0 and the 90% block-bootstrap CI reported; no significance claim required | 20 years is short for a Sharpe test; Unverified judgement |
| "ML adds value" (H3) | Lower bound of 90% CI of Sharpe difference (ML minus B4) > 0 in research walk-forward **and** point estimate > 0 in test | |
| "Engine verified" | Event engine vs vectorised oracle: daily returns equal to 1e-10. Engine vs bt: annualised return within 5 bp/yr at zero cost, daily return correlation > 0.9999 | Tolerances are Unverified judgement; differences are explained, not tuned away |
| Trial budget | At most 300 logged configurations on the research period, all counted in DSR | Number is my judgement |

### 2.4 What a null or negative result looks like, and how to present it

- **H1 fails in test** (Sharpe ≤ 0 after 2006): present as "consistent with post-publication decay", show the pre/post-1993 and pre/post-2006 split, and the crash months. Headline becomes "the engine and the test design caught a decayed anomaly".
- **H3 fails** (ML ≈ vol-scaled momentum): headline "a gradient-boosted ranker rediscovers momentum; complexity added turnover, not alpha", with SHAP dependence plots showing it. This is the Nagel result and a strong interview story.
- **DSR < 0.95**: report it next to the raw Sharpe, with the trial count. Never drop trials to raise it.
- **Engine disagreement with bt** above tolerance: listed as an open issue with the decomposition (§9.3), not hidden.
- Presentation rule: each result table shows gross, net, DSR, trial count and period together. Text uses "hypothetical backtest" on every page.

## 2. Data and periods

| Item | Value |
|---|---|
| Industry data | Ken French 49 Industry Portfolios, daily and monthly, value-weighted block primary (equal-weighted is an ablation) |
| Factor data | Ken French F-F Research Data Factors (incl. RF), Momentum factor, Short-Term Reversal factor; daily and monthly |
| ETF data | The nine original Select Sector SPDRs: XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY |
| Research period | 1926-07 to 2005-12; first signal 1927-07 (the 12-1 lookback needs 12 months) |
| Locked test period | 2006-01 to 2026-09. Masked in code (`DataHandler` test vault) until `prereg-v2` exists; opened once, in task T-2 |
| ETF leg | 1999-01 to 2026-09, run once with the frozen industry strategy; no ETF tuning |
| Clock | Daily bars (trading days of the Ken French daily panel); monthly rebalance on the last trading day of each month |

## 3. Costs

| Item | Value |
|---|---|
| Industry leg cost grid | Flat one-way cost of {0, 5, 10, 25, 50} bp on traded weight, no impact; 10 bp is the headline cost |
| ETF leg | Measured half-spread (task D-7) or a spread sweep; commission 0; square-root impact at AUM $1m, $10m, $100m, $1bn; borrow on short notional swept over {25, 50, 100, 300} bp a year |

## 4. Pre-registered strategy parameters

| Parameter | Value |
|---|---|
| Momentum lookback | 12 months |
| Skip | 1 month (the 12-1 signal uses months t-12 to t-2) |
| Holding period | 1 month (rebalance monthly) |
| Assets per leg | 10 long (top), 10 short (bottom) of 49, equal weight within each leg |
| Vol target (B4) | 10% annualised |
| Vol window (B4) | 126 trading days of trailing strategy returns (≤ t only) |
| Leverage cap | 2.0 |
| Fill lag | 1 trading day (signal at the close of t, fill at the close of t+1, returns earned from t+2) |
| Portfolio mapping | Identical for every signal: rank the score, long top 10, short bottom 10, equal weight within legs, then the same vol-targeting rule |

## 5. Machine-learning settings (H3, H5)

- Models: ridge (B7) and LightGBM regression; shuffled-label LightGBM (B6) runs with every ML
  configuration.
- Features: the 19 features of PLAN §7.2 in 5 groups (momentum, short-term, volatility/risk,
  structure, market state), all computed from data ≤ t.
- Label: next-month return minus the cross-sectional mean over assets valid at t, measured from
  the fill close (t+1 trading day) to the next fill close.
- LightGBM defaults: `num_leaves=15, learning_rate=0.03, n_estimators=300,
  min_data_in_leaf=200, feature_fraction=0.8, bagging_fraction=0.8, lambda_l2=1.0`. Tuning only
  via the inner time-series split, and every tuning configuration counts toward the trial budget.
- Scorer: mean monthly Spearman rank IC.
- Validation inside the research period: expanding-window walk-forward, first training window
  1927-07 to 1946-12, retrain every 12 months, predictions 1947-01 to 2005-12; purge 1 month plus
  1 day, embargo 1 month. CPCV: 6 groups, 2 test groups (15 splits, 5 paths).

## 6. Trial budget

At most **300** logged configurations on the research period. Every strategy run from P4 on is
appended to `experiments/ledger.jsonl` and counted in the deflated Sharpe ratio. Trials are never
deleted.

## 7. Deviations

**D1 (2026-11-21, clarification, not a change).** The "Signal exists" threshold (Newey-West
t > 3.0 on net monthly returns at 10 bp) is computed on monthly **excess** returns: net strategy
return minus the risk-free rate, both compounded per calendar month. The text did not say
whether RF is subtracted. The long-short book earns RF on its collateral, and that interest is
not a momentum premium. Kouki chose this reading (option a) on 2026-11-21, after `prereg-v1`
was tagged and before any strategy performance figure was computed or seen. The t-stat of
raw net returns is reported next to it as a secondary, labelled number. Details:
`docs/DECISIONS.md` entry 012 (c).
