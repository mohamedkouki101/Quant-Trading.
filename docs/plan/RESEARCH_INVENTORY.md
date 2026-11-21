# Research inventory

Date: 2026-11-06. Written for Phase 2 (planning) of the "momentum-lab" flagship project.

## 0. What I could read

| Location | What was there | Status |
|---|---|---|
| Your computer (desktop-th7qhte) | No folder is attached to this thread, so I could not list or read a local project folder. | **Gap.** If you have local notes, drafts or data, attach the folder and I will add them here. |
| Shared project files (`/mnt/project-files/`) | Empty before this thread. | Nothing to read. |
| Phase 1 research doc, ["Quant strategy project: Phase 1 research"](https://claude.ai/artifact/JtzjJ8gJiEeTHELeRgaAnv) | 12 sections plus a source list, about 49k characters, written 2026-11-06. Read in full. | **The only prior research.** Inventoried below. |

So the "folder" is effectively one file. Phase 1 is substantial, so I did not redo it. I only re-verified what was stale, contradictory, or load-bearing for a decision (section 4).

## 1. What the Phase 1 doc contains

| Section | Content | Key finding |
|---|---|---|
| Recommendation | Momentum over mean-reversion | 12-1 industry momentum with volatility scaling on Ken French 49 industry portfolios; sector ETFs as an implementability check; short-term reversal as baseline and feature. |
| 1. Problem and context | Literature on momentum, reversal, pairs, stat-arb | Momentum is broad and persistent; most published edges shrink out of sample (McLean & Pontiff); t > 3 hurdle (Harvey, Liu & Zhu). |
| 2. Existing projects | 10 reference points (papers, Qlib, zipline-reloaded, backtesting.py, Jane Street Kaggle) | Gap: a small transparent engine plus an overfitting-aware feature study. |
| 3. Pitfalls | 14 pitfalls with guards | Look-ahead, label leakage, backtest overfitting, survivorship, costs, crashes, decay, misleading importance, LLM look-ahead, model risk, hypothetical-performance marketing, data licence. |
| 4. Frontier 2023–2026 | purgedcv 0.1.11, SR 26-2, LLM look-ahead papers, Nagel 2025 vs Kelly-Malamud-Zhou | Lean toward Nagel: test whether ML beats vol-scaled momentum. |
| 5. Data and tools | Ken French, JKP, Tiingo, Alpaca, yfinance, Sharadar; library list | Ken French primary; no raw vendor data in the repo. |
| 6. Differentiation | 8 differentiators | Engine tests, trial ledger with DSR/PBO, head-to-head, crash analysis, cost curve, model card, app. |
| 7. Evaluation design | Metrics, 6 baselines, split design | Research 1927–2005, locked test 2006–2026; walk-forward plus CPCV. |
| 8. Pre-build roadmap | 9 steps, about 9.5 h | Gate: data loads, own 12-1 correlates with published Mom, pre-registration frozen. |
| 9. Delivery | Streamlit Community Cloud, README outline, CV bullet format | Precompute results; "hypothetical backtest" labels. |
| 10. Risks and open questions | 7 risks, 8 open questions | Open: Ken French terms, rebalance frequency, cost proxy, long-short vs long-only, trial budget. |
| 11. Skills | Technical and domain skills with sources | Used as a seed for my learning path. |
| 12. Handoff | Code block brief for Phase 2 | Used as the starting spec. |

The doc tags each claim High, Medium, Low or Unverified, and lists about 50 sources opened on 2026-11-06. I reuse those sources and their tags without re-opening them, except where listed in section 4.

## 2. Key findings carried forward (with sources from Phase 1)

| Finding | Source | Phase 1 tag |
|---|---|---|
| Much of stock momentum is industry momentum | [Moskowitz & Grinblatt 1999](https://ideas.repec.org/a/bla/jfinan/v54y1999i4p1249-1290.html) | High |
| Vol management roughly doubles momentum Sharpe and reduces crashes | [Barroso & Santa-Clara 2015](https://econpapers.repec.org/RePEc:eee:jfinec:v:116:y:2015:i:1:p:111-120) (re-opened today: abstract says "nearly doubles") | High |
| Momentum crashes are partly forecastable (bear market plus rebound) | [Daniel & Moskowitz 2016](https://www.nber.org/papers/w20439) | High |
| Short-term reversal mostly dies after costs | [Avramov, Chordia & Goyal 2006](https://ideas.repec.org/a/bla/jfinan/v61y2006i5p2365-2394.html); [Novy-Marx & Velikov 2016](https://nber.org/papers/w20721) | High |
| Published returns fall about 26% out of sample and 58% post-publication | [McLean & Pontiff 2016](https://academicnewsletter.sufe.edu.cn/info/359722) | High |
| t > 3 hurdle for new factors | [Harvey, Liu & Zhu 2016](https://www.nber.org/papers/w20592) | High |
| DSR and PBO quantify selection bias | [Bailey & López de Prado 2014](https://papers.ssrn.com/abstract=2460551), [Bailey et al. 2015](https://papers.ssrn.com/abstract=2326253) | High |
| Momentum, liquidity, volatility dominate ML predictors | [Gu, Kelly & Xiu 2020](https://nber.org/papers/w25398) | High |
| "Virtuous complexity" may be vol-timed momentum in disguise | [Nagel 2025](https://www.nber.org/papers/w34104) | High (paper); Medium (Phase 1's reading) |
| Impurity importance is biased; use held-out permutation importance | [scikit-learn docs](https://scikit-learn.org/stable/modules/permutation_importance.html) | High |
| SR 26-2 (Apr 2026) supersedes SR 11-7 | [SR 26-2](https://www.federalreserve.gov/supervisionreg/srletters/sr2602.htm) | High |
| Streamlit Community Cloud: up to 2.7 GB RAM, sleeps after 12 h idle | [Streamlit docs](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app) | High (re-verified today) |

## 3. Contradictions and how the plan resolves them

| # | Contradiction | Between | Resolution in PLAN.md |
|---|---|---|---|
| C1 | Phase 1 specifies a **vectorised** engine; your Phase 2 brief requires an **event-driven** engine. | Phase 1 §12 vs this brief | The event-driven engine is the product. A ~60-line vectorised implementation with the same timing rule is kept as an internal test oracle (two independent implementations must agree). Best of both. |
| C2 | Phase 1 assumed 40 hours; now no time limit. | Phase 1 assumptions vs this brief | Restore items Phase 1 cut: daily-clock engine, ETF leg with costs/borrow/capacity as **core**, CPCV and synthetic reversal market as core, paper-trading as stretch. |
| C3 | Phase 1 allowed an optional paid tier (≤ $30/month, Sharadar); now free only. | Phase 1 vs coordinator assumption | Drop Sharadar and paid Tiingo. Stock-level extension is out of scope (no free survivorship-free stock data). |
| C4 | Realism (borrow, capacity, fills) is required, but Ken French industry portfolios are **not tradable**. | This brief vs Phase 1 data choice | Two legs: industry leg answers "is there a signal?" with a cost sweep; ETF leg answers "can you trade it?" with spread, borrow and capacity. Stated in the README. |
| C5 | Phase 1 feature list implies a liquidity group (to compare with Gu-Kelly-Xiu), but Ken French industry files have **no volume or spread data**. | Phase 1 §7 vs data | Liquidity features are dropped at industry level; the closest proxies are average firm size and number of firms. The GKX comparison is stated as partial. (Gap found in this inventory.) |
| C6 | Phase 1 label: next-month cross-sectional **rank** (LambdaRank). Phase 1 also says ML forecast quality is measured by rank IC. | Internal | Primary model is LightGBM **regression** on cross-sectionally demeaned next-month return (simpler, boring); LambdaRank is an ablation. Rank IC is the scoring metric for both. |
| C7 | Interview-prep advice conflicts: one guide's "strong" CV example headlines a backtest return and drawdown ([Quantt](https://www.quantt.co.uk/resources/quant-resume-guide)); another says every backtest question is "how much should anyone believe it?" ([Tradermath](https://www.tradermath.org/articles/backtesting-interview-questions)). | Two prep sources | Follow Tradermath for research roles: CV bullets lead with engineering and validation; any return figure carries its DSR, trial count and cost assumption. |
| C8 | Phase 1 says short-term reversal is the mean-reversion baseline; at **industry** level the 1-month signal may not reverse at all (my recollection of industry-momentum results; Unverified). | Phase 1 §7 caveat ("industry-level may differ") | Pre-register the sign of the 1-month industry signal as a **two-sided** open question rather than assume reversal. |

## 4. Facts re-verified today (stale or load-bearing)

| Fact | Phase 1 status | Today's check | Source (opened 2026-11-06) | Confidence |
|---|---|---|---|---|
| Ken French 49 industries coverage | 1926 start "Unverified" | Daily July 1, 1926 to Sept 30, 2026; monthly July 1926 to Sept 2026. Industries assigned at end of June using Compustat SIC (CRSP SIC fallback). | [det_49_ind_port.html](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_49_ind_port.html) | High |
| Ken French terms of use | Unverified | No terms or licence on the library page; detail page says "Copyright Eugene F. Fama and Kenneth R. French". So: download in code, never commit raw files, publish derived results with attribution. | [data_library.html](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html), detail page above | High (fact); the publish-derived-results policy is my judgement, Unverified |
| Missing-value codes | "e.g. -99.99" | "Missing data are indicated by -99.99 or -999." | [data_library.html](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) | High |
| File names | n/a | `49_Industry_Portfolios_CSV.zip`, `49_Industry_Portfolios_daily_CSV.zip`, `F-F_Momentum_Factor(_daily)_CSV.zip`, `F-F_ST_Reversal_Factor(_daily)_CSV.zip` under `/ftp/` | same | High |
| Library versions | LightGBM 4.7 | pandas 3.1.1 (2026-11-04), numpy 2.5.4, scikit-learn 1.9.1, lightgbm 4.7.0, shap 0.54.1, streamlit 1.67.0, statsmodels 0.15.0, pandas-datareader 0.11.1 (2026-06-24, needs pandas ≥ 2.1.4), purgedcv 0.1.11, quantstats 0.0.86, pydantic 2.14.3, pytest 9.2.0, hypothesis 6.170.15, uv 0.13.7 | PyPI JSON API for each package | High |
| Python version constraint | n/a | numpy and shap need ≥ 3.12; vectorbt, zipline-reloaded and nautilus_trader need < 3.15. Choose **3.13**. | PyPI `requires_python` fields | High (constraints); Medium (choice) |
| Independent backtester options | zipline-reloaded, backtesting.py | **bt 1.4.1** (MIT, 2026-10-10, weight-based `WeighTarget` + `Rebalance`, `commissions` callable); vectorbt 1.2.0 (Apache 2.0 **with Commons Clause**); backtrader 1.9.78 (GPLv3, last release 2023-04-19); zipline-reloaded 3.2.1 (Apache-2.0); backtesting.py 0.6.6 (AGPL, single asset); nautilus_trader 1.231.0 (LGPL, event-driven, HFT-oriented) | PyPI; [bt on PyPI](https://pypi.org/project/bt/1.4.1/); bt source `bt/algos.py`, `bt/backtest.py` on GitHub; vectorbt `LICENSE.md` on GitHub | High |
| Streamlit Community Cloud limits | 2.7 GB, 12 h sleep | Same: 0.078–2 cores, 690 MB–2.7 GB, 50 GB; page says limits are approximate "as of February 2024" and "may change at any time" | [Streamlit docs](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app) | High |
| CI cost | Unverified | Standard GitHub-hosted runners are free in public repositories | [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) | High |
| Trading costs of momentum vs reversal at scale | Novy-Marx & Velikov only | Live-trade data (about $1 trillion, 1998–2011): momentum survives costs at large size; short-term reversals do not | [Frazzini, Israel & Moskowitz (AQR)](https://www.aqr.com/Insights/Research/Working-Paper/Trading-Costs-of-Asset-Pricing-Anomalies) | High |

## 5. Gaps (not answered by Phase 1 or today)

1. Your local folder: unread (not attached).
2. Whether the 49-industry CSV includes "number of firms" and "average firm size" blocks and annual BE/ME blocks (I expect it does; verify in task D-2). Medium.
3. Whether pandas-datareader 0.11.1 works with pandas 3.x. Unverified; the plan uses its own parser and keeps pandas-datareader only as a cross-check.
4. Tiingo free-tier terms (Phase 1 used a competitor's comparison page, Medium). Verify at sign-up (task D-6).
5. Real ETF bid-ask spreads: the SSGA XLF page showed no value for the 30-day median spread today. Spread assumptions stay a sweep until measured (task D-7).
6. Barroso & Santa-Clara's volatility window (I recall six months of daily returns; abstract does not say). Unverified; treated as a pre-registered parameter with a sensitivity check.
7. Citadel and Hudson River Trading internship pages failed to load; their requirements are not in the audience research.

## 6. Claims still Unverified (carried into the plan, flagged there)

- Industry 1-month returns may continue rather than reverse (C8).
- Expected correlation level between own industry 12-1 and the published stock-level Mom factor (the plan uses a gate of > 0.5 with a debug stop below 0.3; both numbers are my judgement).
- Compute estimates (event loop over about 25,000 daily bars in under 30 s on a laptop).
- "Honest result" expectations from Phase 1 §7 (modest net Sharpe, decay after 1993).
- That a cost slider and trial ledger are rare in student projects (my judgement).
