# Implementation plan: momentum-lab, phases P0 to P2

This is the step-by-step build plan for Claude Code. It turns the roadmap in
[docs/plan/ROADMAP.md](docs/plan/ROADMAP.md) into ordered tasks with checkboxes and
acceptance criteria for:

- **P0 Setup and pre-registration** (required before P1 can start)
- **P1 Data**
- **P2 Engine**

P3 to P8 are listed at the end as an outline only. They get their own detailed plan
when P2 is done.

Reference documents (read-only, do not edit): [docs/plan/PLAN.md](docs/plan/PLAN.md) (the
design, sections are cited here as "PLAN §x"), [docs/plan/ROADMAP.md](docs/plan/ROADMAP.md),
[docs/plan/RESEARCH_INVENTORY.md](docs/plan/RESEARCH_INVENTORY.md),
[docs/plan/PHASE1_RESEARCH.md](docs/plan/PHASE1_RESEARCH.md).

## How to use this file

1. Do tasks in the order they appear. A task starts only when everything in its
   **Depends** line is ticked.
2. Inside a task, tick each `- [ ]` box as you finish it.
3. A task is done only when every **Acceptance** box is ticked and
   `uv run python tasks.py check` passes (once that command exists after S-2).
4. After each task: update [README.md](README.md) (status table, "Current focus",
   change log), add a line to `docs/DECISIONS.md` if anything differed from the plan,
   then stop and print a summary plus a suggested commit message for Kouki.
5. **Kouki** boxes are things only Kouki can do (git, GitHub, accounts, API keys).
   Claude Code never does them. When the next task needs one, stop and say so.

---

## Corrections to the original plan

The plan was written before the repo existed. These changes apply; where this file and
PLAN.md or ROADMAP.md disagree, this file wins.

| # | Original | Corrected | Why |
|---|---|---|---|
| C1 | ROADMAP S-1 and S-4 create the GitHub repo, commit and run `git tag prereg-v1` | Kouki does all git and GitHub work. Claude Code never runs git commands that change anything (no init, add, commit, tag, branch, push, stash, checkout). Tasks that need git have a **Kouki** checkpoint. | Kouki's instruction |
| C2 | `uv init --package momlab` | `uv init --package --name momlab --python 3.13 --vcs none .` run inside the repo folder | The original creates a subfolder `momlab/`, and plain `uv init` also runs `git init` by default |
| C3 | Makefile **and** `tasks.py` | `tasks.py` only; every `make X` in the plan means `uv run python tasks.py X` | Windows has no `make` by default; two runners drift apart |
| C4 | Repo root folder `momentum-lab/` | Repo root is `C:\Users\ASUS\Desktop\Projects\Quant Trading`. The project name stays momentum-lab and the package stays `momlab` | That is the folder Kouki created |
| C5 | Plan files in `docs/plan/` with a nested `docs/` | All plan files flat in `docs/plan/`, links fixed, plus the Phase 1 research doc copied in as `PHASE1_RESEARCH.md` | Simpler, links work |
| C6 | No task creates `config.py` though E-6 needs `run(config)` | New task **E-0** builds the pydantic config and config hash before the engine | Gap in the roadmap |
| C7 | E-5 depends only on E-2 | E-5 also depends on D-5 (calendar gives the month-end rebalance dates) | Missing dependency |
| C8 | D-2 test: last date equals 2026-09-30 | Last date is **at least** 2026-09-30 and equals the date recorded in `data/manifest.json` | Ken French files are updated; a fixed end date would break on the next download |
| C9 | D-4 "notebook allowed" | D-4 is a script, `scripts/d4_momentum_gate.py`, using research-period data only (1927-07 to 2005-12) | Reproducible, and it keeps the locked test period untouched |
| C10 | P1 exit needs every §5.3 rule, including ETF rule 6 | D-6 and D-7 (ETFs) need Tiingo and Alpaca keys from Kouki. They may finish later, but before P6 task T-3. P1 core exit is D-1 to D-5 plus D-8 for Ken French data | Engine work should not wait on account sign-ups |
| C11 | CI "green" as an acceptance test | Claude Code runs the same steps locally with `tasks.py ci`. Kouki confirms CI is green after pushing | Claude Code cannot push |
| C12 | Code reads `git_sha` (ledger) and checks the `prereg-v2` tag (test vault) | Allowed only as read-only calls inside the program (`git rev-parse HEAD`, `git status --porcelain`, `git tag -l prereg-v2`), with a safe fallback (`"nogit"`, vault stays locked) when git is missing | Needed by the design, changes nothing |
| C13 | Exact library versions from Nov 2026 (e.g. pandas 3.1, lightgbm 4.7) | Use them as lower bounds. If one does not resolve on Windows with Python 3.13, use the newest version that does and record it in `docs/DECISIONS.md` | Avoid getting stuck on one wheel |
| C14 | D-3: "If below 99.5%: stop … before going on"; D-4 depends on D-3 | D-3 failed (24.6% within 1e-4) for explained reasons (rounding to 0.01%, EW by construction); **Kouki decided 2026-11-09** to record the failure and keep the criterion. D-4 depends on D-3 having been run and logged, not on it passing | DECISIONS 008 |
| C15 | CLAUDE.md rule 6 vs D-2/D-3 tests on the full file | Data-integrity checks run on all dates; for 2006+ only counts are reported, row-level outputs are research-period only (**Kouki, 2026-11-09**) | DECISIONS 009 |
| C16 | V-5 `make profile` runs the full 1926–2026 daily backtest on real data | V-5 profiles B3 and B4 on a **synthetic** panel with the real shape (49 assets × the weekdays of 1926-07-01 … 2026-09-30). A real-data profile is added after `prereg-v1`, research period only | A real 1926–2026 run reads the locked test period (rule 6) and computes strategy returns before the tag (rule 7); run time does not depend on the values |
| C17 | V-3 bt cross-check on the real baselines | V-3 runs on synthetic markets now; the same check on real data (research period) is written and skipped until `prereg-v1` exists, like the E-6 real-data test | Rule 7 |
| C18 | V-4 includes purgedcv parity for DSR and PBO | DSR and PBO are built in B-2 (P6); their purgedcv parity test moves there. V-4 covers QuantStats only | Nothing to compare yet |
| C19 | PLAN §9.4 golden synthetic regression has no roadmap task | Added to V-6 | Gap in the roadmap |

---

## P0 Setup and pre-registration

Exit: `tasks.py check` passes locally; `PREREGISTRATION.md` v1 exists; Kouki has
committed and tagged `prereg-v1`.

### S-1 Environment and package ★
Depends: none.

- [x] Check `uv --version` (install uv if missing: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`); `uv python install 3.13`
- [x] `uv init --package --name momlab --python 3.13 --vcs none .` (gives `pyproject.toml`, `src/momlab/__init__.py`, `.python-version`)
- [x] Runtime deps: `uv add pandas numpy scipy statsmodels pyarrow pydantic pyyaml requests lightgbm scikit-learn shap matplotlib`
- [x] Dev deps: `uv add --dev pytest pytest-cov hypothesis ruff mypy pandas-stubs types-PyYAML types-requests pyinstrument bt quantstats purgedcv pandas-datareader`
- [x] `.gitignore`: `.venv/`, `__pycache__/`, `.env`, `data/raw/`, `data/interim/`, `data/processed/`, `reports/coverage/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `*.egg-info/`
- [x] `.env.example` with `TIINGO_API_KEY=` and `ALPACA_API_KEY_ID=` / `ALPACA_API_SECRET_KEY=` (empty values)
- [x] `LICENSE` (MIT, holder "Kouki", 2026)

Acceptance:
- [x] `uv sync --frozen` succeeds from the lockfile
- [x] `uv run python -c "import pandas, numpy, lightgbm, shap, bt, quantstats, statsmodels; print('ok')"` prints ok
- [x] Any version that differs from RESEARCH_INVENTORY §4 is noted in `docs/DECISIONS.md` (create the file if needed)

### S-2 Task runner and CI ★
Depends: S-1.

- [x] `tasks.py` (plain Python, standard library only, run as `uv run python tasks.py <target>`). Targets now: `test` (all except `data` marker), `test-fast` (unit only), `test-data` (only `data` marker), `lint` (`ruff check` + `ruff format --check`), `format`, `typecheck` (`mypy src`), `check` (lint + typecheck + test), `ci` (same steps as the CI workflow), `data` (filled in at D-1/D-2). Unknown target prints the list and exits 1
- [x] `pyproject.toml`: ruff config (line length 100, rules E, F, I, B, UP, NPY, PD), mypy config (`disallow_untyped_defs = true` for `momlab`), pytest config (`testpaths = ["tests"]`, markers `data` and `slow`, `--strict-markers`), coverage source `momlab`
- [x] `tests/test_smoke.py`: imports `momlab` and checks the version string
- [x] `.github/workflows/ci.yml` per PLAN §4: on push and pull_request; ubuntu-latest; `astral-sh/setup-uv`; `uv sync --frozen`; `ruff check`; `ruff format --check`; `mypy src`; `pytest -m "not data" --cov=momlab --cov-report=html --cov-fail-under=85`; upload `htmlcov` as an artefact

Acceptance:
- [x] `uv run python tasks.py check` passes
- [x] `uv run python tasks.py ci` passes (the local stand-in for CI)
- [ ] **Kouki:** after pushing, the GitHub Actions run is green

### S-3 Repo skeleton and decision log
Depends: S-1.

- [x] Create the PLAN §4 folder tree: `configs/` (`base.yaml`, `strategies/`, `sweeps/`), `data/` (with `data/README.md` saying raw data is never committed), `src/momlab/` subpackages `data/`, `signals/`, `analytics/`, `tests/` (`unit/`, `property/`, `synthetic/`, `crosscheck/`, `regression/`, `fixtures/`), `experiments/`, `results/`, `reports/`, `scripts/`, `notebooks/`, `app/`
- [x] Each module from PLAN §4 exists with a module docstring only (what it will hold, which task builds it). No stub functions, so coverage counts only real code
- [x] Use `.gitkeep` in empty folders that must exist in git
- [x] `docs/DECISIONS.md` with a dated entry format (date, task ID, decision, reason, alternatives) and first entry "Why an event-driven engine plus a vectorised oracle" (from RESEARCH_INVENTORY C1); add the C1 to C13 corrections above as entry 2
- [x] `docs/DESIGN.md`, `docs/DATA.md`, `docs/LIMITATIONS.md` as headed stubs

Acceptance:
- [x] `ruff check`, `mypy src` and `pytest` pass
- [x] Tree matches PLAN §4 except `Makefile` (see C3)

### S-4 Pre-registration v1 ★
Depends: S-1. Must be done before any strategy return is computed (that includes D-4).

- [x] Write `PREREGISTRATION.md` (v1): hypotheses H1 to H6, baselines B0 to B7, thresholds, null-result presentation (copy PLAN §2.1 to §2.4 word for word); research period 1926-07 to 2005-12 (first signal 1927-07), locked test 2006-01 to 2026-09; cost grid {0, 5, 10, 25, 50} bp; trial budget 300; pre-registered parameters (12-1 lookback, skip 1, hold 1 month, 10 per leg, 10% vol target, 126-day vol window, leverage cap 2.0, fill_lag 1); LightGBM defaults from PLAN §7.2; a "Deviations" section (empty)
- [x] Print the file's sha256 and put it in README under "Pre-registration"

Acceptance:
- [x] `results/` holds no result files (only `.gitkeep`)
- [x] sha256 recorded in README
- [x] **Kouki:** commit `PREREGISTRATION.md` and run `git tag prereg-v1`; tick this box in README when done — **done: tag `prereg-v1` on commit 4b04bc1, pushed (checked 2026-11-21)**

**P0 exit check:** all S-tasks ticked, Kouki boxes ticked. Update README phase status.

---

## P1 Data

Exit (core): D-1 to D-5 accepted on real Ken French data, D-4 gate passed, Ken French parts
of D-8 written. D-6 and D-7 can finish later (C10).

### D-1 Ken French downloader ★
Depends: S-2.

- [x] `src/momlab/data/kenfrench.py`: download to `data/raw/` the zips listed in RESEARCH_INVENTORY §4 from `https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/`: `49_Industry_Portfolios_CSV.zip`, `49_Industry_Portfolios_daily_CSV.zip`, `F-F_Research_Data_Factors_CSV.zip`, `F-F_Research_Data_Factors_daily_CSV.zip`, `F-F_Momentum_Factor_CSV.zip`, `F-F_Momentum_Factor_daily_CSV.zip`, `F-F_ST_Reversal_Factor_CSV.zip`, `F-F_ST_Reversal_Factor_daily_CSV.zip`
- [x] `data/manifest.json` entry per file: `url`, `download_ts` (UTC ISO-8601), `sha256`, `bytes`. Rows and dates are added by D-2
- [x] Skip the download if the file exists and its hash matches the manifest; `--force` re-downloads and records a new vintage
- [x] Timeouts and one retry; clear error if the site is down
- [x] Wire `tasks.py data` to call it
- [x] Unit tests use a mocked HTTP layer (no network in unit tests)

Acceptance:
- [x] Running `tasks.py data` twice leaves the manifest unchanged the second time
- [x] `data/raw/` is gitignored; `data/manifest.json` is not
- [x] Tests pass without network

### D-2 Parser and cleaner ★
Depends: D-1.

- [x] Open each real CSV first and list its blocks (value-weighted, equal-weighted, number of firms, average firm size, BE/ME, etc.). Record what exists in `docs/DATA.md` (closes inventory gap 2)
- [x] `kenfrench.py` parser: split header blocks, parse `YYYYMMDD` (daily) and `YYYYMM` (monthly, to month-end) dates, replace -99.99 and -999 with NaN, percent to decimal
- [x] `src/momlab/data/clean.py`: PLAN §5.3 rules 1 to 5, each as a named function that returns a report (rule 3 is applied by consumers; here, just never forward-fill returns; rule 5 flags, never clips)
- [x] Write long-format parquet to `data/processed/` per PLAN §5.2: `industry_daily.parquet`, `industry_monthly.parquet`, `factors_daily.parquet`, `factors_monthly.parquet`. `n_firms` and `avg_size` lagged one month through `available_at`
- [x] Add `rows`, `first_date`, `last_date` and processed-file hashes to the manifest
- [x] Fixture file `tests/fixtures/kf_sample.csv` with header blocks, -99.99 and -999 values; unit tests on it (`test_kenfrench_parse`)
- [x] Real-data tests marked `@pytest.mark.data`

Acceptance:
- [x] Unit tests on the fixture pass: NaN where codes were, decimals not percents, month-end dates
- [x] Real-data test: 49 assets; daily first date 1926-07-01; last date ≥ 2026-09-30 and equal to the manifest (C8); no -99.99 or -999 left; dates unique and increasing
- [x] `test_available_at_lag` passes (leakage check L3)

### D-3 Daily vs monthly reconciliation ★
Depends: D-2.

- [x] Compound daily returns to calendar months per industry; compare with the monthly file
- [x] Write `reports/data_reconciliation.csv` (industry, month, daily-compounded, monthly, difference) and a summary

Acceptance:
- [ ] ≥ 99.5% of industry-months within 1e-4; every mismatch listed; summary in `docs/DATA.md` — **FAILED: 24.6%** (mismatches listed, summary written; failure recorded per Kouki, C14)
- [x] If below 99.5%: stop, investigate, log the cause in DECISIONS.md before going on

### D-4 Momentum sanity gate ★
Depends: D-3 and S-4 (pre-registration first).

- [x] `scripts/d4_momentum_gate.py`: vectorised 12-1 industry long-short (top 10 / bottom 10, equal weight) on monthly value-weighted data, **1927-07 to 2005-12 only**; correlation with the published Mom factor
- [x] Hand-check the 12-1 window on one industry for one month and write the numbers in the decision entry (guards L2)
- [x] Entry in `docs/DECISIONS.md` with the correlation, the period, and a small chart saved to `reports/d4_gate.png`
- [x] This is a sanity check, not a result: do not write to `results/`, do not add it to the trial ledger

Acceptance:
- [x] Correlation > 0.5 → pass. Between 0.3 and 0.5 → write down the likely reasons and ask Kouki before going on. Below 0.3 → stop; the timing is wrong, debug before any other task

### D-5 Calendar
Depends: D-2.

- [x] `src/momlab/data/calendar.py`: trading days from the daily panel; `month_end_rebalance_dates` = last trading day of each month; helper for the n-th trading day of the month (needed later for rebalance-day sensitivity)

Acceptance:
- [x] Tests with months ending on a weekend or holiday (e.g. 2023-09-29 Friday) and with a short month
- [x] Every rebalance date is a date in the panel

### D-6 ETF downloader (can finish later, see C10)
Depends: D-2, **Kouki:** Tiingo and Alpaca free accounts with keys in `.env`.

- [ ] Before coding: write the Tiingo free-tier terms into `docs/DATA.md` (Kouki may need to paste them if the page needs a login)
- [ ] `src/momlab/data/etf.py`: download XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY daily (adjusted and unadjusted close, volume) from Tiingo; cache in `data/raw/`; manifest entries
- [ ] Confirm inception dates; record them in DATA.md
- [ ] Alpaca Basic cross-check on overlapping days
- [ ] PLAN §5.3 rule 6 (returns from adjusted close; split check; drop zero-volume days); write `etf_daily.parquet`
- [ ] Keys read from `.env` only; never printed or logged

Acceptance:
- [ ] Tiingo vs Alpaca daily returns correlate > 0.999 on overlapping days
- [ ] Terms recorded; `.env` gitignored

### D-7 ETF spread estimate (can finish later)
Depends: D-6.

- [ ] Sample Alpaca quotes (about 20 days per year since 2016, 15:50 to 16:00 ET) per ETF; median half-spread in bps; write `etf_quotes_sample.parquet`

Acceptance:
- [ ] Table and method in DATA.md, with the IEX-only caveat

### D-8 Data documentation
Depends: D-3 (Ken French part); D-7 (ETF part).

- [ ] `docs/DATA.md`: sources, licences/terms, schema (PLAN §5.2), cleaning rules and their test names, vintage hashes, reconciliation summary, leakage items L3, L10, L11

Acceptance:
- [ ] Every dataset has its licence or terms and a hash

**P1 exit check:** D-1 to D-5 and D-8 (Ken French) ticked; D-4 passed. Update README.

---

## P2 Engine

Exit: hand-computed trade test passes to 1e-12; engine equals oracle to 1e-10 for B1, B3,
B4, B5 at 0 and 10 bp; poisoned-future test passes; analytics and ledger tested.

Rules for this phase:
- The timing contract in PLAN §3.2 is the spec. Read it before E-1 and keep it open.
- `engine.py`, `execution.py`, `costs.py` and `data/handler.py` need 100% line coverage
  (PLAN §9.4).
- `oracle.py` must not import from `engine.py`, `portfolio.py` or `execution.py`. It is an
  independent implementation; shared timing code would make the check useless.
- Runs on real data in this phase use the research period only. The test vault stays locked.

### E-0 Config (added, see C6)
Depends: S-3.

- [x] `src/momlab/config.py`: pydantic v2 `RunConfig` (universe, weighting vw/ew, start/end, rebalance rule, lookback, skip, n per leg, vol target, vol window, leverage cap, cost model and bps, `fill_lag: int` with validator `>= 1`, seed)
- [x] Load `configs/base.yaml` merged with a strategy YAML; `config_hash = sha256(canonical JSON)` (sorted keys, no whitespace)
- [x] `configs/base.yaml` with the pre-registered defaults from `PREREGISTRATION.md`

Acceptance:
- [x] `fill_lag=0` raises a validation error
- [x] Same config gives the same hash across runs; key order in YAML does not change it

### E-1 Events and queue ★
Depends: S-3.

- [x] `events.py`: frozen dataclasses `MarketEvent`, `SignalEvent`, `OrderEvent`, `FillEvent` (PLAN §3.3)
- [x] `queue.py`: `EventQueue` that asserts non-decreasing timestamps and `FillEvent.ts > OrderEvent.ts` for the matching order

Acceptance:
- [x] Test: an out-of-order event raises
- [x] Test: a fill at or before its order's timestamp raises

### E-2 DataHandler and AsOfView ★
Depends: E-1, D-2.

- [x] `data/handler.py`: `DataHandler` over NumPy arrays with an integer cursor; `advance()`, `view()`, `bar_returns(ts)`
- [x] `AsOfView`: only `returns(lookback)` and `field(name, lookback)`; raises `LookAheadError` on any index > cursor; drops rows with `available_at > t`; no attribute that exposes the underlying DataFrame
- [x] Test vault: rows from 2006-01-01 on are masked unless `MOMLAB_UNLOCK_TEST=1` **and** the `prereg-v2` git tag exists (read-only check, C12); every unlock appends to `experiments/unlock_log.jsonl`

Acceptance:
- [x] Access beyond the cursor raises `LookAheadError`
- [x] `test_vault_locked`: 2006+ rows are invisible by default; setting only the env var is not enough
- [x] 100% line coverage on `data/handler.py`

### E-3 Portfolio and drift ★
Depends: E-2.

- [x] `portfolio.py`: positions as weights; mark-to-market drift with bar returns; daily P&L; `PortfolioState`; turnover from drifted weights

Acceptance:
- [x] Drift test: 0.5/0.5 with +10%/−10% gives 0.55/0.45
- [x] Turnover test: computed from drifted weights, not previous targets

### E-4 Execution and cost models ★
Depends: E-3.

- [x] `execution.py`: `ExecutionSimulator` queues orders and fills at the close of bar `t + fill_lag`
- [x] `costs.py`: `FlatBps`; `SpreadImpactBorrow` (half-spread per asset, commission, square-root impact `k·σ·sqrt(notional/ADV)`, daily borrow on short notional) per PLAN §3.4

Acceptance:
- [x] Order at t fills at t+1 close; returns credited from t+2
- [x] `FlatBps`: Δw = [+0.2, −0.2] at 10 bp costs 0.0004
- [x] Borrow accrues daily on shorts only; cost is never negative
- [x] 100% line coverage on `execution.py` and `costs.py`

### E-5 Rule signals and risk ★
Depends: E-4, D-5 (C7).

- [x] `signals/rules.py`: B1 equal weight, B3 12-1 momentum, B4 vol-scaled 12-1, B5 1-month signal (sign as a parameter); all read data only through `AsOfView`; emit only on month-end rebalance dates; top 10 / bottom 10 equal weight per leg
- [x] `risk.py`: vol targeting from trailing strategy returns ≤ t, leverage cap, gross/net/position caps

Acceptance:
- [x] `test_mom_12_1_window` on a 15-month toy series: product of months t-12 … t-2 minus 1, skip month excluded (L2)
- [x] Vol-target test: constant-vol returns give leverage = target / vol, cap respected

### E-6 Engine loop and oracle ★
Depends: E-0 to E-5.

- [x] `engine.py`: `run(config) -> RunResult` (daily returns gross and net, weights, trades, costs, turnover) following PLAN §3.2 steps 1 to 6
- [x] `oracle.py`: vectorised version with the same timing, written independently (see phase rules)
- [x] `tests/fixtures/hand_trades_3x6.csv`: 3 assets × 6 days with every fill, cost, position and daily P&L **worked out by hand** (formulas written in a comment block or a companion `.md`), never generated by running the engine
- [x] Poisoned-future test: replace all data after t with NaN and, separately, with +1000% returns; every decision up to t must be bit-identical

Acceptance:
- [x] Hand-computed 3×6 test matches to 1e-12
- [x] Engine equals oracle to 1e-10 on daily returns for B1, B3, B4, B5 at 0 and 10 bp, on synthetic data in CI and on real research-period data in a `data`-marked test — **synthetic: 8/8; real research period: 8/8 (Kouki's `tasks.py test-data`, 2026-11-21)**
- [x] Poisoned-future test passes (L1, L9)
- [x] 100% line coverage on `engine.py`

### E-7 Analytics
Depends: E-6.

- [x] `analytics/metrics.py`: Sharpe (RF subtracted, √252 or √12 by frequency), Sortino, max drawdown, Calmar, turnover, worst month, skew, kurtosis, Newey-West t via statsmodels `cov_type="HAC"`, Lo (2002) adjusted Sharpe
- [x] `analytics/bootstrap.py`: stationary block bootstrap with seeded `SeedSequence`
- [x] `analytics/factors.py`: regression on FF3 + Mom + ST Rev with HAC

Acceptance:
- [x] Hand-example tests from PLAN §9.1 (Sharpe, drawdown with two drawdowns)
- [x] Bootstrap is reproducible with a fixed seed

### E-8 Trial ledger
Depends: E-6.

- [x] `ledger.py`: append-only `experiments/ledger.jsonl` with the PLAN §7.5 schema; each line stores the sha256 of the previous line; `verify()` checks the chain; git SHA and dirty flag read-only (C12)
- [x] `engine.run(config, log=True)` appends one trial

Acceptance:
- [x] Editing or deleting any line makes `verify()` fail (`test_ledger_append_only`)
- [x] The ledger API has no update or delete method

**P2 exit check:** all E-tasks ticked; `tasks.py check` passes; coverage targets met. Update
README and write the timing contract into `docs/DESIGN.md` (sequence diagram + invariants).
Then stop and ask Kouki before starting P3.

---

## P3 Verification

Entry: P2 (code complete; the E-6 real-data box waits for `prereg-v1`).
Exit: all synthetic and cross-check tests pass or have documented, quantified differences.

Rules for this phase:
- Synthetic data only, except checks marked as real-data, which are skipped until
  `prereg-v1` exists and then use the research period only.
- Seeds come from `SeedSequence(seed).spawn(n)`; every expected value is derived in the test
  file or in `synthetic.py` independently of the engine.
- Long tests are marked `@pytest.mark.slow`; seeds run in a process pool.

### V-1 Synthetic markets S1–S3 ★
Depends: E-6, E-7.

- [x] `synthetic.py`: `null_market` (i.i.d. Student-t), `planted_momentum` (next month's
  return planted from the 12-1 score, with the generator's own picks and expected
  holding-period returns), `cost_market` (constant returns)
- [x] `tests/synthetic/test_markets.py`: S1, S2, S3 per PLAN §9.2

Acceptance:
- [x] S1 (49 assets, 30 years, 200 seeds, B3 at 0 bp): share of seeds with |HAC t| > 2 inside
  the binomial 95% interval around 5%; mean Sharpe within 3 standard errors of 0
- [x] S2 (49 assets, 100 years, 50 seeds): the engine's mean holding-period return minus the
  generator's expected value has a 95% CI that contains 0 in ≥ 90% of seeds
- [x] S3: net P&L equals −(turnover × cost) exactly (1e-15) at 0 and 10 bp

### V-2 Property tests
Depends: E-6.

- [x] `tests/property/test_engine_properties.py` (hypothesis, 200 examples each): zero-cost
  run invariant to asset column order; weights after a fill equal the target and Σ|w| equals
  the target gross; costs ≥ 0 for both cost models; doubling all target weights doubles each
  holding-period gross return (RF = 0)

Acceptance:
- [x] All properties pass with 200 examples each

### V-3 bt cross-check ★
Depends: E-6.

- [x] `tests/crosscheck/test_bt.py`: engine target weights shifted to the fill date, fed to
  bt 1.4.1 `WeighTarget` + `Rebalance`, `commissions=lambda q, p: abs(q) * p * bps / 1e4`,
  `integer_positions=False`; synthetic markets for B1, B3, B4 at 0 and 10 bp
- [x] `scripts/v3_crosscheck.py` writes `reports/crosscheck.md`: per run annualised return gap,
  daily correlation, max daily gap, and the gap decomposition of PLAN §9.3
- [x] Real-data version (research period) written, skipped until `prereg-v1` (C17) — **B1, B3, B4 pass at 0 bp after the bt-capital fix (DECISIONS 018)**

Acceptance:
- [x] At 0 bp: annualised return within 5 bp/yr and daily correlation > 0.9999, or the cause
  is documented and quantified in `reports/crosscheck.md`

### V-4 QuantStats parity
Depends: E-7.

- [x] `tests/crosscheck/test_quantstats.py`: Sharpe, Sortino, max drawdown and CAGR from
  `analytics.metrics` vs QuantStats on the same series (daily and monthly), RF = 0 and with RF
  passed as excess returns. purgedcv parity moves to B-2 (C18)

Acceptance:
- [x] All within 1e-6

### V-5 Performance profile
Depends: E-6.

- [x] `scripts/profile_engine.py` and `tasks.py profile`: B3 and B4 on the synthetic panel of
  C16 under pyinstrument → `reports/profile.html`; table with wall time, bars per second, peak
  memory (`tracemalloc`) and time share per component → `reports/profile.md` and
  `docs/DESIGN.md`

Acceptance:
- [x] Full run time recorded; target < 30 s, or an optimisation is logged

### V-6 Coverage report and golden regression
Depends: V-1 … V-4.

- [x] `tasks.py ci` also fails if `engine.py`, `execution.py`, `costs.py` or
  `data/handler.py` is below 100% line coverage; HTML report in `reports/coverage/`
- [x] `tests/regression/golden_synthetic.parquet` + test: metrics of B1, B3, B4, B5 on a
  seeded synthetic market; fails if any metric changes by > 1e-9 unless `GOLDEN_UPDATE=1`
  (then the change must be explained in `docs/DECISIONS.md`) (C19)

Acceptance:
- [x] Coverage ≥ 85% overall and 100% for the four files
- [x] Golden test passes; changing a metric by 1e-8 makes it fail

**P3 exit check:** all V-tasks ticked (real-data parts may wait for `prereg-v1`); `tasks.py
check` passes. Update README. Then stop and ask Kouki before starting P4.

---

## Outline of later phases (not to start yet)

Detailed tasks are in [docs/plan/ROADMAP.md](docs/plan/ROADMAP.md). A detailed plan like the
one above is written when P2 is done.

| Phase | Goal | Tasks |
|---|---|---|
| P3 Verification | Detailed above | V-1 to V-6 |
| P4 Baselines | B0 to B5 on 1927–2005, cost curve, factor regressions | R-1 to R-4 |
| P5 ML and features | 19 features, walk-forward and CPCV, ridge and LightGBM, importance study | M-1 to M-5, F-1 to F-5 |
| P6 Robustness and locked test | Surfaces, DSR/PBO, PREREG v2, single unlock, ETF leg | B-1 to B-4, T-1 to T-3 |
| P7 Product | README, DESIGN, MODEL_CARD, static report, Streamlit app | W-1, W-2, A-1, I-1 |
| P8 Stretch | numba, CPCV viewer, JKP, paper trading, blog | X-1 to X-6 |
