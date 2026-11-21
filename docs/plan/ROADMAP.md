# Roadmap: full task table

Format: **ID | what | why | exact steps | inputs | outputs | acceptance test | depends on**. ★ = critical path. No calendar; do tasks in ID order within a phase. Section references (§) point to PLAN.md.

The **cut line** sits between P7 and P8. Everything above it is core; nothing in P8 starts before P7's exit criterion is met.

---

## P0 Setup and pre-registration

Entry: plan approved. Exit: CI green; `PREREGISTRATION.md` v1 committed and tagged `prereg-v1`.

| ID | What | Why | Exact steps | Inputs | Outputs | Acceptance test | Depends |
|---|---|---|---|---|---|---|---|
| S-1 ★ | Create repo and environment | Reproducibility from day one | Create public GitHub repo `momentum-lab`; `uv init --package momlab`; `.python-version` = 3.13; `uv add pandas numpy scipy statsmodels pyarrow pydantic pyyaml lightgbm scikit-learn shap matplotlib`; `uv add --dev pytest pytest-cov hypothesis ruff mypy pyinstrument bt quantstats purgedcv pandas-datareader`; commit `uv.lock` | PLAN §3.5, §4 | repo, `pyproject.toml`, `uv.lock` | `uv sync --frozen` succeeds on a clean clone on Windows and in CI; `python -c "import lightgbm, shap, bt"` works | — |
| S-2 ★ | CI and task runner | Every later task is checked automatically | Write `.github/workflows/ci.yml` (§4); `Makefile` and `tasks.py` with targets; `tests/test_smoke.py` | §4 | CI workflow, task runner | CI green on push; `python tasks.py test` runs locally | S-1 |
| S-3 | Repo skeleton and docs stubs | Structure before code avoids sprawl | Create the folder tree of §4 with empty modules and docstrings; `docs/DECISIONS.md` with first entry "Why event-driven + oracle" | §4 | skeleton | `ruff check` and `mypy src` pass | S-1 |
| S-4 ★ | Pre-registration v1 | Fix hypotheses before seeing results (SG2) | Copy §2.1–2.4 into `PREREGISTRATION.md`; add trial budget 300, research/test dates, cost grid, baselines; commit; `git tag prereg-v1` | PLAN §2 | `PREREGISTRATION.md` | Tag exists; file hash recorded in README; no file in `results/` exists yet | S-1 |

## P1 Data

Entry: P0. Exit: all §5.3 rule tests pass on real data; D-4 gate passes.

| ID | What | Why | Exact steps | Inputs | Outputs | Acceptance test | Depends |
|---|---|---|---|---|---|---|---|
| D-1 ★ | Ken French downloader | Primary data, survivorship-free | `data/kenfrench.py`: download the zips listed in RESEARCH_INVENTORY §4 to `data/raw/`; record URL, timestamp, sha256 in `data/manifest.json` | Ken French URLs | raw zips, manifest | Re-running is idempotent; manifest hashes stable; `data/raw` is gitignored | S-2 |
| D-2 ★ | Parser and cleaner | Silent bugs live in header blocks and -99.99 codes | Parse each CSV block (VW, EW, n_firms, avg_size; confirm which blocks exist, inventory gap 2); apply §5.3 rules 1–5; write `industry_daily.parquet`, `industry_monthly.parquet`, `factors_daily.parquet` | raw zips | processed parquet | Unit tests on a fixture file; real-data test: 49 assets, first date 1926-07-01, last 2026-09-30, no -99.99 left | D-1 |
| D-3 ★ | Daily vs monthly reconciliation | Detects parsing, vintage or compounding bugs | Compound daily to month; compare with monthly file | processed parquet | `reports/data_reconciliation.csv` | ≥ 99.5% of industry-months within 1e-4 (threshold Unverified); all mismatches listed | D-2 |
| D-4 ★ | Momentum sanity gate | If this fails, the timing is wrong (Phase 1 step 3) | Quick vectorised 12-1 industry long-short on monthly data (notebook allowed, not a result); correlate with published Mom 1927–2005 | processed parquet | number + chart in `docs/DECISIONS.md` | Correlation > 0.5 passes; < 0.3 stops the project until fixed (Unverified thresholds) | D-3 |
| D-5 | Calendar module | Rebalance dates on real trading days | `calendar.py`: trading days from the panel; month-end = last trading day of month | processed parquet | module + tests | Tests with month ends on Fridays and holidays | D-2 |
| D-6 | ETF downloader | Tradable leg | Sign up to Tiingo free; read and save its terms to `docs/DATA.md`; download 9 SPDR ETFs adjusted and unadjusted with volume; confirm inception dates; Alpaca Basic as cross-check | API keys in `.env` (gitignored) | `etf_daily.parquet` | Returns from Tiingo vs Alpaca correlate > 0.999 on overlapping days (Unverified threshold); terms recorded | D-2 |
| D-7 | Spread estimate | Realistic ETF costs | Pull a sample of Alpaca quotes (e.g. 20 days per year since 2016, 15:50–16:00 ET) per ETF; compute median half-spread bps | Alpaca | `etf_quotes_sample.parquet`, table in DATA.md | Values recorded with method; IEX-only caveat stated | D-6 |
| D-8 | Data doc | Licences and choices in one place | Write `docs/DATA.md`: sources, licences, schema, cleaning rules, vintages | D-1…D-7 | DATA.md | Every dataset has licence/terms and a hash | D-7 |

## P2 Engine

Entry: P1 exit. Exit: hand-computed tests pass; engine equals oracle to 1e-10.

| ID | What | Why | Exact steps | Inputs | Outputs | Acceptance test | Depends |
|---|---|---|---|---|---|---|---|
| E-1 ★ | Events and queue | Backbone of the event-driven design | `events.py` frozen dataclasses; `queue.py` with time-order assertions | §3.3 | modules + tests | Out-of-order event raises; Fill before Order raises | S-3 |
| E-2 ★ | DataHandler and AsOfView | Look-ahead impossible by construction | Integer cursor over NumPy arrays; `LookAheadError`; `available_at` filtering; test vault masking | processed parquet | `data/handler.py` | Accessing index > cursor raises; vault masks 2006+ unless unlocked | E-1, D-2 |
| E-3 ★ | Portfolio and drift | Most silent P&L bugs live here | Positions in weights, drift with bar returns, P&L, turnover from drifted weights | E-2 | `portfolio.py` | Drift test (0.5/0.5 → 0.55/0.45); turnover test | E-2 |
| E-4 ★ | Execution and cost model | Fill timing and costs | `ExecutionSimulator` with `fill_lag`; `FlatBps`, `SpreadImpactBorrow` | E-3 | `execution.py`, `costs.py` | Fill at t+1 close; cost on Δw; borrow accrues daily on shorts | E-3 |
| E-5 ★ | Rule signals and risk | Baselines need them | `rules.py` (B1, B3, B4, B5); `risk.py` vol targeting with cap | E-2 | modules | Window unit tests; vol-target test | E-4 |
| E-6 ★ | Engine loop and oracle | Integration plus an independent check | `engine.run(config) -> RunResult` (daily returns, weights, trades, costs); `oracle.py` vectorised with the same timing | E-1…E-5 | `engine.py`, `oracle.py` | Hand-computed 3×6 CSV test passes to 1e-12; engine == oracle to 1e-10 for B1, B3, B4, B5 at 0 and 10 bp; poisoned-future test passes | E-5 |
| E-7 | Analytics | Metrics everyone will probe | `metrics.py`, `bootstrap.py`, `factors.py` (HAC), Lo-adjusted Sharpe | E-6 | modules | Hand-example tests (§9.1) | E-6 |
| E-8 | Ledger | Count every trial | `ledger.py` append-only with hash chain; `engine.run` logs automatically when `log=True` | E-6 | module | Tampering with a line breaks chain verification test | E-6 |

## P3 Verification

Entry: P2 exit. Exit: all synthetic and cross-check tests pass or have documented, quantified differences.

| ID | What | Why | Exact steps | Inputs | Outputs | Acceptance test | Depends |
|---|---|---|---|---|---|---|---|
| V-1 ★ | Synthetic markets S1–S3 | Known answers catch subtle bias | `synthetic.py` generators; tests per §9.2 | E-6 | tests | S1 false-positive rate within binomial 95% band of 5%; S2 CI coverage ≥ 90%; S3 exact | E-6 |
| V-2 | Property tests | Invariants beyond examples | hypothesis tests per §9.1 | E-6 | tests | Pass with 200 examples each | E-6 |
| V-3 ★ | bt cross-check | Independent open-source check | `tests/crosscheck/test_bt.py` per §9.3 step 2; write `reports/crosscheck.md` with gap decomposition | E-6 | report | Tolerance in PLAN §2.3 or documented cause | E-6 |
| V-4 | QuantStats and purgedcv parity | Independent metric checks | Tests per §9.3 steps 3–4 | E-7 | tests | Within 1e-6 | E-7 |
| V-5 | Performance profile | Engine as product (perf) | `make profile` per PLAN §3.7 | E-6 | `reports/profile.html`, table | Full run time recorded; target < 30 s or optimisation logged | E-6 |
| V-6 | Coverage report | Engine as product (quality) | `pytest --cov --cov-report=html` | all tests | `reports/coverage/` | Thresholds in §9.4 | V-1…V-4 |

## P4 Baselines and rule research (research period only)

Entry: P3 exit. Exit: baseline table T1 and cost curve on 1927–2005; ledger has every run.

| ID | What | Why | Exact steps | Inputs | Outputs | Acceptance test | Depends |
|---|---|---|---|---|---|---|---|
| R-1 ★ | Baselines B0–B5 | Reference points before any model | Run each at 0/5/10/25/50 bp; log; metrics incl. HAC t, turnover | E-7, E-8 | `results/baselines_research.parquet`, T1 | Ledger lines = runs; B3 correlates with Mom as in D-4 | V-1, V-3 |
| R-2 ★ | Vol-scaled and crash-aware variants | H2 | B4 and the crash-aware rule (§7.1 step 2) | R-1 | results, F1 | Sharpe difference with block-bootstrap CI reported | R-1 |
| R-3 | 1-month signal (H4) | Two-sided mean-reversion test | B5 with both signs reported; pick sign on research period | R-1 | results | Both signs in ledger | R-1 |
| R-4 | Factor regressions | Is it just known factors? | Regress on FF3 + Mom + ST Rev with HAC (lags 6, Unverified) | R-2 | T5 | Alpha and betas with HAC t | R-2 |

## P5 ML and feature study (research period only)

Entry: P4. Exit: walk-forward and CPCV results; importance stability report.

| ID | What | Why | Exact steps | Inputs | Outputs | Acceptance test | Depends |
|---|---|---|---|---|---|---|---|
| M-1 ★ | Feature pipeline | All models share it | `features.py` 19 features with `available_at`; label per §7.2 | D-2 | `features_monthly.parquet` | Window tests; L3, L5 tests; no NaN labels in training | R-1 |
| M-2 | Validation splits | Leak-free evaluation | `validation.py` walk-forward and CPCV with purge/embargo | M-1 | module | `test_purge_removes_overlap`; split counts (15 for CPCV 6/2) | M-1 |
| M-3 ★ | Ridge and LightGBM walk-forward | H3 | Fit per fold (scalers in fold); predictions → `model_signal.py` → engine with the same portfolio mapping | M-1, M-2 | predictions, results, T2 | Shuffled-label null: rank IC mean within ±0.01 and |Sharpe t| < 2 (Unverified thresholds) | M-2 |
| M-4 ★ | Nagel test and synthetic reversal | Is ML momentum in disguise? | Momentum-only LightGBM vs full; correlation with B4 returns; run on S4 market | M-3 | results, F7 | S4: SHAP slope on mom_12_1 < 0 | M-3 |
| M-5 | CPCV paths | Variance of the backtest, PBO input | Run CPCV for rules sweep and ML configs | M-2 | path matrix | Matrix shape (n_configs × 5 paths) stored | M-3 |
| F-1 ★ | Correlation clusters | Correlated features hide each other | Spearman correlation on training data; Ward clustering on `1 − |ρ|` ([scikit-learn example, today](https://scikit-learn.org/stable/auto_examples/inspection/plot_permutation_importance_multicollinear.html), High); compare clusters with the 5 economic groups | M-1 | `results/clusters.json`, dendrogram | Cluster assignment fixed in DECISIONS.md before importance runs | M-1 |
| F-2 ★ | Grouped permutation importance | Held-out importance, by group | For each walk-forward test fold: permute each group jointly (50 repeats, seeded), score drop in rank IC | M-3, F-1 | `importance_by_fold.parquet`, F5 | Mean ± 2 std per group; null model's importances ≈ 0 | F-1 |
| F-3 | SHAP | Direction and shape, not just size | TreeExplainer interventional (background = 500 rows of training fold) and tree_path_dependent; sum by group ([SHAP docs, today](https://shap.readthedocs.io/en/stable/generated/shap.TreeExplainer.html), High) | M-3 | SHAP arrays, F7 | Group ranks from SHAP and permutation compared, disagreements explained | M-3 |
| F-4 | Stability across folds | Importance that moves is not a finding | Kendall τ of group ranks between consecutive folds; share of folds where momentum ranks first (H5) | F-2 | F6, stability table | Reported with the H5 threshold verdict | F-2 |
| F-5 | Importance caveats note | Honest interpretation | Write `docs/IMPORTANCE.md`: model-specific, not causal, correlated features, permutation creates unrealistic rows, interventional vs observational SHAP | F-2…F-4 | doc | Reviewed against §8.1 item 10 | F-4 |

## P6 Robustness and locked test

Entry: P5. Exit: final tables with DSR, PBO, CIs; test opened exactly once; ETF leg done.

| ID | What | Why | Exact steps | Inputs | Outputs | Acceptance test | Depends |
|---|---|---|---|---|---|---|---|
| B-1 ★ | Parameter stability surfaces | Plateau vs spike | Grid §7.4 via oracle (parity proven); heatmaps | R-2 | F3 | Plateau rule verdict recorded | R-2 |
| B-2 | Sensitivities | Fragility | Fill lag, vol window/target, rebalance day, VW vs EW, n_firms ≥ 5 filter | R-2 | sensitivity table | All in ledger | R-2 |
| B-3 ★ | Multiple-testing correction | Selection bias | DSR over all ledger trials; PBO via CSCV on M-5 matrix; Harvey-Liu BHY haircut; t > 3 | ledger, M-5 | T1/T2 columns | Values match purgedcv where applicable | B-1, M-5 |
| B-4 | Sub-periods and decay | One lucky era? | Sub-period table; rolling 10-year Sharpe; leave-one-decade-out | R-2, M-3 | T4, F4 | All periods reported, none dropped | R-2 |
| T-1 ★ | Pre-registration v2 | Freeze before the test | Record final configs (one rule, one ML) and the exact commands; commit; tag `prereg-v2` | B-3 | PREREG v2 | Tag exists before any test-period run | B-3 |
| T-2 ★ | Open the locked test once | Honest out-of-sample | `MOMLAB_UNLOCK_TEST=1 python tasks.py test-period`; log unlock | T-1 | T3, unlock log | Exactly one unlock entry; results match the pre-registered commands | T-1 |
| T-3 | ETF leg | Tradability, H6 | Frozen strategy on 9 ETFs 1999–2026 with measured spreads, borrow sweep, capacity at $1m–$1bn | D-7, T-1 | T7, capacity curve | No ETF-specific tuning in ledger | T-1 |

## P7 Product

Entry: P6. Exit: app live; `make all` reproduces README numbers from a clean clone.

| ID | What | Why | Exact steps | Inputs | Outputs | Acceptance test | Depends |
|---|---|---|---|---|---|---|---|
| W-1 ★ | README, DESIGN, MODEL_CARD, LIMITATIONS | The reader's entry point | Outlines in PLAN §11 | all results | docs | A friend can reproduce in < 30 min (Unverified) | T-2 |
| W-2 | Static report | App fallback | `make report` → `site/`; Pages workflow | results | Pages site | Loads on phone | W-1 |
| A-1 ★ | Streamlit app | Interactive demo | Pages per PLAN §10; deploy steps | results | live app | Every page loads < 5 s after wake; memory < 1 GB (Unverified) | W-1 |
| I-1 | Fill interview kit with real numbers | CV and talk tracks | Fill blanks in INTERVIEW_KIT from results only | results | updated kit | Every number traceable to a ledger trial id | W-1 |

---- **cut line** ----

## P8 Stretch (independent, any order)

| ID | What | Why | Exact steps | Acceptance test | Depends |
|---|---|---|---|---|---|
| X-1 | numba event loop | Performance story | JIT the per-bar weight/P&L update; keep the Python loop as reference | Same outputs to 1e-12; speed-up in profile | V-5 |
| X-2 | CPCV path viewer in app | Shows variance of backtests | Plot 5 paths per config | Loads in app | M-5, A-1 |
| X-3 | JKP global industry robustness | Out-of-country test | Download JKP (CC BY-NC 4.0) industry or momentum factors; compare | Licence noted; results in appendix | T-2 |
| X-4 | Alpaca paper-trading shadow | Live data, no money | Monthly signal → paper orders; log fills vs model | 3+ months of logs | T-3 |
| X-5 | LambdaRank and monotone-constraint ablations | Model choice study | Same splits and ledger | Counted in trial budget | M-3 |
| X-6 | Blog post | Communication | Outline in PLAN §11 | Published | W-1 |
