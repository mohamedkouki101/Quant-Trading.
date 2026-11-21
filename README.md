# momentum-lab

An event-driven backtest engine, written from scratch and verified three ways, used to test
whether vol-scaled industry momentum still earns a premium after costs and whether a
machine-learning ranker adds anything beyond it. Includes a feature-importance study.

> Hypothetical backtests only, not investment advice.

**Status: P0 done locally (waiting on Kouki's commit, CI check and `prereg-v1` tag); P1 in progress.** This README tracks progress while the project is being
built. It becomes the results-first README at task W-1.

- Build plan: [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)
- Full design: [docs/plan/PLAN.md](docs/plan/PLAN.md) · all tasks: [docs/plan/ROADMAP.md](docs/plan/ROADMAP.md)
- Decisions and deviations: [docs/DECISIONS.md](docs/DECISIONS.md)
- Rules for Claude Code: [CLAUDE.md](CLAUDE.md)

## Current focus

**P3 complete except the real-data bt check (needs `prereg-v1`); stopped before P4 (needs Kouki's go-ahead).** Done: V-1 to V-6; S-1, S-3, D-1, D-2, D-5, E-0 to E-5, E-7, E-8; E-6 except the real-data check (needs `prereg-v1`); D-3 closed as failed (Kouki). Waiting on Kouki: push/CI, tag `prereg-v1`.

## Waiting on Kouki

1. **S-2 — first commit, push, CI check.** Commit everything (`.gitignore` keeps `.venv/`,
   `.env`, `data/raw|interim|processed/` out), push to GitHub, and confirm the Actions run
   "CI" is green. Then tick the Kouki box under S-2 in `IMPLEMENTATION_PLAN.md`.
   Suggested message: `S-1, S-2: uv package, task runner and CI`.
2. **S-4 — tag the pre-registration.** After the commit above (it includes
   `PREREGISTRATION.md`), check the hash in PowerShell:
   `(Get-FileHash PREREGISTRATION.md -Algorithm SHA256).Hash` should equal the sha256 under
   "Pre-registration" below (case aside). Then `git tag prereg-v1` and `git push origin prereg-v1`.
   Tick the Kouki box under S-4 and change "tag `prereg-v1`: not yet" to "done" below.
   **D-4 (momentum sanity gate) will not run until this tag exists.**
3. **D-6 / D-7 (later)** need free Tiingo and Alpaca accounts with keys in `.env`.
4. **Confirm the HAC t reading (DECISIONS 012 c)** before D-4/R-1: the pre-registered
   "Newey-West t of monthly net returns" is computed on monthly *excess* returns (net minus RF),
   because the long-short book earns RF on its collateral. Say if you want the literal raw-net t instead.
5. After `prereg-v1` is tagged, `uv run python tasks.py test-data` runs the open real-data boxes
   (E-6 engine = oracle, V-3 bt cross-check, research period only).
6. **Go-ahead for P4** (baselines on 1927–2005). P4 also needs the tag (D-4 first) and your answer on item 4.

## Progress

Legend: ⬜ not started · 🟨 in progress · ✅ done · ⛔ blocked · ⏸ deferred

### Phases

| Phase | Goal | Status |
|---|---|---|
| P0 Setup & pre-registration | Repo, env, CI, PREREG v1 | 🟨 local work done; Kouki checkpoints open |
| P1 Data | Clean, hashed Ken French panels; momentum sanity gate | 🟨 D-1, D-2, D-5 done; D-3 failed (recorded); D-4 waits for `prereg-v1`; D-6/D-7 need keys |
| P2 Engine | Event-driven engine + vectorised oracle | 🟨 E-0 to E-8 built and tested; one box open: E-6 real-data engine = oracle (waits for `prereg-v1`) |
| P3 Verification | Synthetic markets, bt/QuantStats parity, profile | 🟨 V-1…V-6 done; real-data bt check waits for `prereg-v1` |
| P4 Baselines | B0–B5 on research period, cost curve | ⬜ |
| P5 ML & feature study | Ridge, LightGBM, importance | ⬜ |
| P6 Robustness & locked test | DSR/PBO, PREREG v2, test opened once, ETF leg | ⬜ |
| P7 Product | Docs, static report, Streamlit app | ⬜ |
| P8 Stretch | Optional extras | ⬜ |

### P0 Setup and pre-registration

| ID | Task | Status | Notes |
|---|---|---|---|
| S-1 | Environment and package | ✅ | uv 0.12.17 (Windows), CPython 3.13.15; see DECISIONS 003 |
| S-2 | Task runner and CI | 🟨 | Done locally; Kouki: push and confirm CI green |
| S-3 | Repo skeleton and decision log | ✅ | |
| S-4 | Pre-registration v1 | 🟨 | Written, sha256 recorded; Kouki: commit + tag `prereg-v1` |

### P1 Data

| ID | Task | Status | Notes |
|---|---|---|---|
| D-1 | Ken French downloader | ✅ | |
| D-2 | Parser and cleaner | ✅ | 49 assets, 1926-07-01 → 2026-09-30; blocks listed in DATA.md |
| D-3 | Daily vs monthly reconciliation | ⛔ | Closed as FAILED per Kouki (24.6% within 1e-4; rounding + EW by construction); DECISIONS 008 |
| D-4 | Momentum sanity gate | ⬜ | Gate: correlation with Mom > 0.5 |
| D-5 | Calendar | ✅ | |
| D-6 | ETF downloader | ⬜ | Needs Tiingo + Alpaca keys from Kouki; may be deferred |
| D-7 | ETF spread estimate | ⬜ | May be deferred |
| D-8 | Data documentation | ⬜ | |

### P2 Engine

| ID | Task | Status | Notes |
|---|---|---|---|
| E-0 | Config (pydantic, hash) | ✅ | |
| E-1 | Events and queue | ✅ | |
| E-2 | DataHandler, AsOfView, test vault | ✅ | |
| E-3 | Portfolio and drift | ✅ | |
| E-4 | Execution and cost models | ✅ | |
| E-5 | Rule signals and risk | ✅ | |
| E-6 | Engine loop and oracle | 🟨 | Done except the real-data engine = oracle test, which waits for the `prereg-v1` tag |
| E-7 | Analytics | ✅ | Metrics, stationary bootstrap, HAC factor regression; HAC t on monthly excess returns (DECISIONS 012, confirm) |
| E-8 | Trial ledger | ✅ | Hash chain plus head record; `run(config, log=True)` appends one trial (DECISIONS 013) |

### P3 Verification

| ID | Task | Status | Notes |
|---|---|---|---|
| V-1 | Synthetic markets S1–S3 | ✅ | S1 11/200 seeds with abs(t) > 2 (band 4–16); S2 CI covers 0 in 47/50; S3 exact (DECISIONS 014) |
| V-2 | Property tests | ✅ | 4 hypothesis properties × 200 examples; doubling property catches a no-drift mutant |
| V-3 | bt cross-check | 🟨 | Synthetic: pass at 0 bp (gap ~1e-15/day); cost gaps fully explained by bt's commission rule (reports/crosscheck.md, DECISIONS 015). Real-data part waits for `prereg-v1` |
| V-4 | QuantStats parity | ✅ | Sharpe, Sortino, MDD, CAGR identical to QuantStats (≤ 5.6e-17); purgedcv part moved to B-2 (C18) |
| V-5 | Performance profile | ✅ | 11.15 s (B3), 10.45 s (B4) for 26,155 bars × 49 assets; target < 30 s met (reports/profile.md) |
| V-6 | Coverage and golden regression | ✅ | 98.53% overall, core four files 100% (enforced in check/ci/workflow); golden metrics for B1/B3/B4/B5 (DECISIONS 017) |

## Key checks

| Check | Target | Latest |
|---|---|---|
| `tasks.py check` | passes | passes (2026-11-08, after S-4) |
| Test count / coverage | coverage ≥ 85% | 59 tests / 100% (1 statement so far) |
| D-3 reconciliation | ≥ 99.5% within 1e-4 | — |
| D-4 own 12-1 vs Mom correlation (1927–2005) | > 0.5 | — |
| Engine vs oracle | ≤ 1e-10 | — |

## Pre-registration

`PREREGISTRATION.md` v1 sha256 (LF line endings, see `.gitattributes`):
`a920ca3f04aeed8e9e0aafe890a94fc224b8ef15f788cfe8e4baccb9045a6823` · tag `prereg-v1`: not yet

## Session log (evidence)

Command output behind each tick, newest last.
- **S-1** (2026-11-08): `uv sync --frozen` exit 0; import check printed `ok`; `ruff check .` "All checks passed!"; `mypy src` "no issues found in 1 source file"; `pytest` collected 0 items (exit 5, smoke test comes in S-2).
- **S-2** (2026-11-08): `tasks.py check` exit 0 (ruff clean, format clean, mypy "no issues", 3 passed); `tasks.py ci` exit 0, coverage 100% ≥ 85; `tasks.py test-fast` 3 passed. Unknown/no target exits 1 (tests/unit/test_tasks.py, watched fail first).
- **S-3** (2026-11-08): `ruff check .` "All checks passed!"; `ruff format --check .` 44 files already formatted; `mypy src` "no issues found in 30 source files"; `pytest` 59 passed (tests/unit/test_skeleton.py pins the tree); `tasks.py check` exit 0.
- **S-4** (2026-11-08): `sha256sum PREREGISTRATION.md` → a920ca3f04aeed8e9e0aafe890a94fc224b8ef15f788cfe8e4baccb9045a6823; verbatim check "verbatim present: True"; `ls -A results` → only .gitkeep; ruff clean, mypy clean, pytest 59 passed.
- **D-1** (2026-11-08): `tasks.py data` downloaded 8 zips (49 industries monthly 489,861 B, daily 4,177,116 B, …); second run downloaded nothing and `sha256sum data/manifest.json` was b4681bc35cf3… both times; 10 mocked-HTTP tests (watched fail first); `tasks.py check` exit 0, 69 passed, coverage 100%.
- **D-2** (2026-11-08): `tasks.py data` wrote industry_daily 2,581,124 rows and industry_monthly 117,894 rows (1926-07-01 → 2026-09-30), factors daily 26,338 / monthly 1,203; manifest sha256 3143a9f9… identical on a second run; `tasks.py test-data` 7 passed (49 assets, first date 1926-07-01, last = manifest, no codes left, test_available_at_lag_real); `tasks.py check` exit 0, 90 passed, coverage 99%.
- **D-3** (2026-11-09): `scripts/d3_reconcile.py` → vw within 1e-4 46.83%, ew 2.39%, overall 24.61% → FAIL (exit 1). Research-period investigation: VW mean signed gap < 0.5 bp per decade, corr 0.99982, rounding-only simulation predicts ~52% within 1e-4; 613 / 43,843 VW months (1.4%) exceed the worst-case rounding bound (n_days+1)·0.5e-4; EW differs by construction (daily-rebalanced vs monthly EW). No parsing/timing bug found. Decision asked of Kouki.
- **D-3** (2026-11-09): Kouki decisions 1a + 2a. `scripts/d3_reconcile.py` (re-run) → VW research 45.99% within 1e-4, EW 2.40%; test period counts only; criterion as written 24.6117% → FAIL (exit 1, recorded). Row-level CSV ends at 2005-12. `tasks.py data` re-run: manifest sha256 unchanged (3143a9f9…), 0 flags in test period. `tasks.py check` exit 0.
- **D-5** (2026-11-09): tests/unit/test_calendar.py 10 passed after fixing two hand-count errors in my own expected values (10th trading day of Sep 2023 is Sep 15, not 14); weekend month-end 2023-09-29, Good Friday 2018-03-29, Feb 2023/2024, Saturday session 1950-09-30; `tasks.py test-data` 8 passed incl. every rebalance date in the panel, one per month from 1926-07; `tasks.py check` exit 0, 106 passed.
- **E-0** (2026-11-09): tests/unit/test_config.py 8 passed (watched 7 fail first): fill_lag=0 raises; hash = sha256 of canonical JSON; reordered YAML keys give the same hash; nested merge; all strategy YAMLs validate. `tasks.py check` exit 0, 114 passed.
- **E-1** (2026-11-09): tests/unit/test_events_queue.py 6 passed (collection failed first: modules missing): out-of-order put raises, fill at/before its order raises, unknown/duplicate order ids raise. `tasks.py check` exit 0, 120 passed.
- **E-2** (2026-11-09): tests/unit/test_handler.py 11 + test_gitinfo.py 4 passed (collection failed first); `test_vault_locked`: 2006 rows invisible by default, env var alone and tag alone not enough; access beyond cursor raises LookAheadError; handler.py and gitinfo.py 100% line coverage; real-data handler: 49 assets, 1926-07-01 → 2005-12-30. `tasks.py check` exit 0, 135 passed.
- **E-3** (2026-11-09): tests/unit/test_portfolio.py 10 passed (collection failed first): 0.5/0.5 with +10%/-10% → 0.55/0.45; turnover after drift = 0.1 (not 0); cash earns RF; missing return on a held asset earns 0 and is counted. `tasks.py check` exit 0, 145 passed.
- **E-4** (2026-11-09): tests/unit/test_execution_costs.py 12 passed (collection failed first): order at t fills at t+1 close, P&L from t+2 (and t+2/t+3 with fill_lag 2); FlatBps [+0.2,−0.2] at 10 bp = 0.0004; borrow daily on shorts only; costs ≥ 0 on 200 random trades; costs.py and execution.py 100% line coverage. `tasks.py check` exit 0, 157 passed.
- **E-5** (2026-11-09): tests/unit/test_rules_risk.py 9 passed (collection failed first): `test_mom_12_1_window` on 15 months = Π(1+R_m), m=4..14, minus 1, skip month and months 1-3 have no effect; constant-vol (alternating ±a) leverage = 0.10/(a·√(126/125)·√252), cap 2.0 respected, warm-up gives 0; signals only on month-end rebalance dates. `tasks.py check` exit 0, 166 passed.
- **E-6** (2026-11-09): tests/unit/test_engine.py 25 passed (23 failed first): hand 3×6 matches to 1e-12 (gross, turnover, cost, net, NAV, weights); engine = oracle ≤ 1e-10 on a synthetic 30-asset market with missing data and RF for B1/B3/B4/B5 × {0, 10} bp (8/8); poisoned future (NaN and +1000%) bit-identical decisions for all four strategies; engine.py 100% coverage. Real-data engine = oracle test: 8 skipped "waits for Kouki's prereg-v1 tag". `tasks.py check` exit 0, 191 passed.
- **E-7** (2026-11-09): tests/unit/test_analytics.py 12 passed (12 failed first, module missing): Sharpe hand series with RF subtraction and √252 vs √12; max drawdown with two drawdowns (−20%, then −19%) = −0.20; Sortino, Calmar, worst month (−9.75%), raw kurtosis, HAC t with 0 lags = mean/(sd_pop/√n), Lo η(3; 0.5, 0.25) = 3/√5.5; bootstrap identical with seed 7 twice, different with seed 8; factor regression recovers α = 0.001, β = 1.5/−0.5 exactly. analytics modules fully covered. `tasks.py check` exit 0, 203 passed, coverage 99%.
- **E-8** (2026-11-09): tests/unit/test_ledger.py 17 passed (collection failed first): `test_ledger_append_only` fails verify() and blocks append for 8 tamperings (edit first/last line, delete first/middle/last, swap, hand-appended line, CRLF); public API is exactly append/read/verify/path/head_path; entry keys = PLAN §7.5 schema; `run(..., log=True)` appends one line with Sharpe equal to `metrics.sharpe` on the run, `log=False` writes nothing; ledger.py and engine.py 100% coverage. No real ledger written. `tasks.py check` exit 0, 220 passed.
- **P2 exit** (2026-11-09): ruff clean; mypy clean (33 files); `tasks.py check` exit 0, 220 passed, coverage 99% (only kenfrench.py 508 and oracle.py 53, 103 missed; engine, execution, costs, handler 100%); `tasks.py test-data` 9 passed, 8 skipped (engine = oracle on real data, waits for `prereg-v1`). Timing contract, invariants and interfaces written to docs/DESIGN.md.
- **V-1** (2026-11-09): tests/synthetic/test_markets.py 8 passed (8 failed first, generators missing). S1: 11/200 null seeds with |HAC t| > 2, binomial band 4–16, mean Sharpe −0.0110. S2: CI of realised − expected covers 0 in 47/50 seeds (≥ 45 needed), engine picks = generator picks in 50/50. S3: net = −turnover × cost to 1e-15 at 0 and 10 bp, r = 0 and 0.0004. Mutation check: S2 does not detect fill_lag 2 (5/5 covered), recorded in DECISIONS 014 d. `tasks.py check` exit 0, 228 passed (2 min 46 s).
- **V-2** (2026-11-09): tests/property/test_engine_properties.py 4 passed, 200 examples each (derandomized, 25 s): column-order invariance at 0 bp (B1/B3/B4/B5, NaNs, fill_lag 1–3), weights after each fill = order target with gross 2 (B3/B5), 1 (B1), ≤ 4 (B4), costs ≥ 0 for FlatBps and SpreadImpactBorrow, doubling targets doubles each holding-period return (RF 0). Mutation: replacing drift by daily rebalancing makes the doubling property fail. `tasks.py check` exit 0, 232 passed.
- **V-3** (2026-11-09): tests/crosscheck/test_bt.py 7 passed, 3 skipped (real data, waits for `prereg-v1`); failed first on the missing module, then 3 failed on my first guess at bt's commission rule (fixed after reading bt's source). `scripts/v3_crosscheck.py` exit 0 → reports/crosscheck.md: at 0 bp B1/B3/B4 annual gap 0.0000 bp/yr, correlation 1.0000000000, max daily gap ≤ 1.55e-15; at 10/50 bp annual gap up to 0.36/4.74 bp/yr, and bt equals the replica of its commission rule to ≤ 6.4e-15 a day; unshifted weights give 26.6 bp/yr and corr 0.98796. `tasks.py check` exit 0, 239 passed.
- **V-4** (2026-11-09): tests/crosscheck/test_quantstats.py 5 passed (daily, monthly, first-period loss, RF via excess returns). Largest differences vs QuantStats 0.0.86: Sharpe 0.0, Sortino 5.6e-17, max drawdown 0.0, CAGR 0.0 (tolerance 1e-6). `tasks.py check` exit 0, 244 passed.
- **V-5** (2026-11-09): `tasks.py profile` exit 0 → reports/profile.md: 49 assets × 26,155 bars, B3 11.15 s (2,346 bars/s), B4 10.45 s (2,504 bars/s), peak memory 64.9 MiB; target < 30 s met. Time shares (B4): portfolio 50.8%, engine loop 34.1%, data handler 10.0%, rest < 2% each. Machine: Windows 11, Python 3.13.15. `tasks.py check` exit 0, 244 passed.
- **V-6** (2026-11-10): tests/regression/test_golden_synthetic.py 2 passed (failed first: no golden file; generated with GOLDEN_UPDATE=1, then passed twice unchanged); a 1e-8 change in b3.sharpe is reported. Core gate: engine, execution, costs, data/handler 336 statements, 0 missed, 100%; probe on oracle.py (98%) prints "Coverage failure".
- **P3 exit** (2026-11-10): `tasks.py ci` exit 0: uv sync --frozen, ruff clean, 80 files formatted, mypy clean (34 files), 246 passed, coverage 98.53% (≥ 85%), core files 100%. `tasks.py test-data`: 9 passed, 11 skipped (8 engine = oracle, 3 bt; wait for `prereg-v1`). No ledger written.

## Change log

| Date | Task | Change |
|---|---|---|
| 2026-11-08 | setup | Plan files copied to `docs/plan/`; IMPLEMENTATION_PLAN, CLAUDE.md and this README created |
| 2026-11-08 | S-1 | Created uv package momlab (Python 3.13), runtime and dev deps, .gitignore, .env.example, LICENSE, docs/DECISIONS.md |
| 2026-11-08 | S-2 | tasks.py runner (test, test-fast, test-data, lint, format, typecheck, check, ci, data), ruff/mypy/pytest/coverage config, smoke test, GitHub Actions workflow |
| 2026-11-08 | S-3 | PLAN §4 folder tree with docstring-only modules, doc stubs (DESIGN, DATA, LIMITATIONS), decision log entries 001-004, skeleton test |
| 2026-11-08 | S-4 | PREREGISTRATION.md v1 (PLAN §2.1–2.4 verbatim, periods, cost grid, parameters, LightGBM defaults, trial budget 300) and .gitattributes for hashed files |
| 2026-11-08 | D-1 | Ken French downloader with manifest (url, UTC time, sha256, bytes), skip-if-hash-matches, --force vintages, one retry, wired to tasks.py data |
| 2026-11-08 | D-2 | Ken French parser (header blocks, dates, missing codes, percent→decimal), cleaning rules 1/2/3/5, four processed parquet panels, manifest rows/dates/hashes, data-quality report |
| 2026-11-09 | D-3 | Reconciliation built (rule4_reconcile + scripts/d3_reconcile.py); acceptance gate fails, investigation in session log; blocked on Kouki |
| 2026-11-09 | D-3 | Kouki chose: record D-3 failure (criterion unchanged) and full-file checks with counts only for 2006+; periods.py, reconcile_panels, research-only row-level reports |
| 2026-11-09 | D-5 | TradingCalendar: trading days from the panel, month-end rebalance dates (last trading day), n-th trading day, incomplete final month dropped |
| 2026-11-09 | E-0 | Pydantic RunConfig (fill_lag ≥ 1 validator, extra fields forbidden), YAML base + strategy deep merge, sha256 config hash; configs/base.yaml and B1/B3/B4/B5 strategy files |
| 2026-11-09 | E-1 | Frozen MarketEvent/SignalEvent/OrderEvent/FillEvent with read-only NumPy weight copies; EventQueue asserting time order and fill-after-order |
| 2026-11-09 | E-2 | DataHandler (read-only arrays, integer cursor), AsOfView snapshot (returns, field with available_at filter, month_returns compounded in-view), test vault (env + prereg-v2 tag, unlock log), read-only gitinfo |
| 2026-11-09 | E-3 | Portfolio: weights + cash at RF, drift, daily gross P&L, holding cost, fills to target with cost, turnover from drifted weights, unscaled-strategy return history for vol targeting |
| 2026-11-09 | E-4 | ExecutionSimulator (fill at close of t+fill_lag, trades to target from drifted weights); FlatBps and SpreadImpactBorrow (half-spread, commission, square-root impact, daily borrow on shorts) |
| 2026-11-09 | E-5 | Rule signals B1 (equal weight), B3/B5 (MomentumSignal with lookback/skip/sign), long-short top/bottom n; risk: realised-vol targeting of the unscaled strategy with cap, gross/net/position caps |
| 2026-11-09 | E-6 | Event loop run(config)/run_with with EventQueue; independent value-based vectorised oracle; hand-worked 3×6 fixture (exact fractions) with formula notes; poisoned-future and engine-vs-oracle tests |
| 2026-11-09 | E-7 | analytics: metrics (Sharpe, Sortino, MDD, Calmar, CAGR, worst month, skew, kurt, HAC t, Lo Sharpe, turnover, performance bundle), stationary block bootstrap, HAC factor regression |
| 2026-11-09 | E-8 | Append-only ledger with sha256 chain and head record, PLAN §7.5 entries with metrics, engine.run(log=True) |
| 2026-11-09 | P2 exit | docs/DESIGN.md: overview, timing sequence diagram, invariants with guarding tests, interfaces, cost model; P2 stopped before P3 |
| 2026-11-09 | P3 plan | Detailed P3 tasks V-1…V-6 and corrections C16–C19 written into IMPLEMENTATION_PLAN.md |
| 2026-11-09 | V-1 | synthetic.py: null, planted-momentum and constant-return markets with own expected values; S1–S3 tests with a process pool |
| 2026-11-09 | V-2 | hypothesis property tests for the engine (column order, fills = target, costs ≥ 0, linearity of holding-period returns) |
| 2026-11-09 | V-3 | crosscheck.py (engine vs bt 1.4.1 with a replica of bt's commission rule), test_bt.py, scripts/v3_crosscheck.py → reports/crosscheck.md |
| 2026-11-09 | V-4 | QuantStats parity tests for Sharpe, Sortino, max drawdown and CAGR |
| 2026-11-09 | V-5 | scripts/profile_engine.py and `tasks.py profile` (wall time, bars/s, tracemalloc peak, pyinstrument component shares); table in DESIGN.md |
| 2026-11-10 | V-6 | Golden synthetic regression (B1/B3/B4/B5 from the strategy YAMLs) and 100% coverage gate for the four core files in tasks.py and CI |
