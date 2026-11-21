# Decision log

Every deviation from the plan (`docs/plan/`, which is frozen) and every non-obvious design
choice is recorded here, newest last. Entries are never deleted; a reversed decision gets a new
entry that points back to the old one.

Entry format:

```
## NNN. Title
- Date: YYYY-MM-DD
- Task: task ID from IMPLEMENTATION_PLAN.md
- Decision: what was decided
- Reason: why
- Alternatives: what else was considered, and why not
```

---

## 001. Event-driven engine plus a vectorised oracle
- Date: 2026-11-08
- Task: S-3 (recorded at S-1 when this file was created)
- Decision: The product is an event-driven backtest engine. A short vectorised implementation
  with the same timing rule is kept as an internal test oracle; the two must agree to 1e-10
  (task E-6). `oracle.py` must not import from `engine.py`, `portfolio.py` or `execution.py`.
- Reason: The Phase 1 research specified a vectorised engine; the Phase 2 brief requires an
  event-driven one (RESEARCH_INVENTORY §3 C1). The event style mirrors live systems and makes
  look-ahead structurally hard; the oracle is fast for sweeps and gives an independent check, so
  a timing bug has to be made twice, in two different styles, to go unnoticed.
- Alternatives: Vectorised only (fast, but look-ahead is easy to introduce silently and there is
  nothing to cross-check against); event-driven only (no independent check, slow sweeps).

## 002. Corrections C1 to C13 to the original plan
- Date: 2026-11-08
- Task: setup (recorded at S-1)
- Decision: The thirteen corrections in the "Corrections to the original plan" table of
  `IMPLEMENTATION_PLAN.md` apply wherever they disagree with `docs/plan/PLAN.md` or
  `docs/plan/ROADMAP.md`. In short: C1 Kouki does all git/GitHub work; C2 `uv init --package
  --name momlab --python 3.13 --vcs none .`; C3 `tasks.py` only, no Makefile; C4 repo root is
  the "Quant Trading" folder; C5 plan files flat in `docs/plan/`; C6 new task E-0 for the config;
  C7 E-5 also depends on D-5; C8 data end date is "at least 2026-09-30 and equal to the
  manifest"; C9 D-4 is a script on research-period data only; C10 ETF tasks D-6/D-7 may finish
  later (before T-3); C11 `tasks.py ci` is the local stand-in for CI; C12 read-only git calls in
  program code with safe fallbacks; C13 library versions are lower bounds.
- Reason: The plan was written before the repo existed; see the "Why" column of that table.
- Alternatives: Editing `docs/plan/` directly (rejected: it is frozen reference material).

## 003. Library versions and the Windows toolchain
- Date: 2026-11-08
- Task: S-1
- Decision: Versions from RESEARCH_INVENTORY §4 are lower bounds in `pyproject.toml` (C13). All
  resolved on Windows with CPython 3.13.15. Resolved versions that differ from the inventory:
  purgedcv 0.1.12 (inventory 0.1.11; newer patch release, lower bound kept at 0.1.11);
  uv 0.12.17 is installed (inventory lists 0.13.7, PLAN §3.5 says 0.13). Everything else
  resolved at exactly the inventory version: pandas 3.1.1, numpy 2.5.4, scikit-learn 1.9.1,
  lightgbm 4.7.0, shap 0.54.1, statsmodels 0.15.0, pydantic 2.14.3, pandas-datareader 0.11.1,
  quantstats 0.0.86, pytest 9.2.0, hypothesis 6.170.15, bt 1.4.1. Streamlit is not installed yet
  (needed in P7). The generated `[project.scripts]` hello-world entry point was removed.
- Reason: uv 0.12.17 builds the lockfile without problems, so upgrading the tool was not
  needed to finish S-1. Claude Code runs the Windows `uv.exe` (from WSL) so `.venv` is a native
  Windows environment, the same one PowerShell uses.
- Alternatives: Upgrading uv (`uv self update`) — left to Kouki; it changes nothing in the
  lockfile format for this project.

## 004. Skeleton details not spelled out in PLAN §4
- Date: 2026-11-08
- Task: S-3
- Decision: (a) Added `src/momlab/py.typed` (PEP 561 marker) and `configs/README.md`; (b) the
  tree is pinned by `tests/unit/test_skeleton.py` so drift from PLAN §4 fails a test;
  (c) pytest runs with `--import-mode=importlib` so test files in different folders may share a
  base name without `__init__.py` files; (d) `MODEL_CARD.md` is not created as a stub — it
  belongs to task W-1 (P7) and an empty card would look like a finished deliverable;
  (e) `configs/base.yaml` is created by E-0, as IMPLEMENTATION_PLAN says, not here.
- Reason: Small conveniences that keep the layout checked and the tools quiet.
- Alternatives: `__init__.py` in every test folder (more files, same effect).

## 005. Pre-registration v1 layout and line endings
- Date: 2026-11-08
- Task: S-4
- Decision: `PREREGISTRATION.md` copies PLAN §2.1–2.4 byte for byte (checked by a script that
  searches for the exact PLAN text in the file) under a section "1"; data/periods, costs,
  parameters, ML defaults and trial budget follow as sections 2–6, then "Deviations". Added
  `.gitattributes` forcing LF endings for `PREREGISTRATION.md`, `experiments/*.jsonl` and
  `data/manifest.json`. The recorded sha256 is of the LF file.
- Reason: The README hash and the ledger hash chain must not change because git rewrote line
  endings on a Windows checkout.
- Alternatives: Normalising line endings inside every hash computation (more code, easy to
  forget in one place).

## 006. Downloader details (manifest layout, paths module)
- Date: 2026-11-08
- Task: D-1
- Decision: (a) `data/manifest.json` has two sections, `raw` (one entry per zip: `url`,
  `download_ts`, `sha256`, `bytes`) and `processed` (added in D-2); keys sorted, LF endings, so
  re-runs produce identical bytes. (b) `--force` keeps the replaced entry under
  `previous_vintages` when the content changed, so an old result can still name its vintage.
  (c) A response that is not a zip (e.g. an HTML maintenance page) counts as a failed attempt.
  (d) New module `src/momlab/paths.py` (not in PLAN §4) holds the repo, data and report paths;
  `MOMLAB_DATA_DIR` can override the data folder. (e) The manifest is rewritten after each
  downloaded file so a failure halfway keeps the entries already fetched.
- Reason: Idempotent, auditable vintages; one place for paths.
- Alternatives: One manifest file per raw file (more files, no gain).

## 007. Parser and processed-panel choices
- Date: 2026-11-08
- Task: D-2
- Decision:
  (a) **Characteristic lag inside the panel.** `n_firms` and `avg_size` are stored already
  lagged: a row in month m carries Ken French's value for month m-1 (daily rows too), and
  `available_at` stays equal to `date` because everything on the row is known then. PLAN §5.2
  describes exactly this ("lagged one month"); a separate characteristics table with its own
  `available_at` would have done the same with one more file.
  (b) **Timestamps, not date32.** `date` and `available_at` are stored as `datetime64[ns]`
  timestamps (PLAN §5.2 says `date32`), because CLAUDE.md requires timestamps in code and pandas
  reads parquet `date32` back as Python `date` objects.
  (c) **Saturdays.** Rule 2 accepts Saturday sessions up to 1952-05-31 (NYSE Saturday trading),
  never Sundays, because the real file has 1,158 Saturdays through 1952-05-24.
  (d) **Missing rows kept.** NaN returns stay as rows, so each date has 49 assets; consumers
  decide exclusion (rule 3).
  (e) **Factor alignment.** Factor panels use the FF3 dates; Mom/ST_Rev rows outside them
  (ST_Rev before 1926-07) are dropped, and Mom's first months are NaN.
  (f) **Row-level reports stay local.** `reports/data_flags_daily.csv` and (D-3)
  `reports/data_reconciliation.csv` reproduce Ken French return values row by row, so they are
  gitignored like the processed data (CLAUDE.md rule 10); summaries go to
  `reports/data_quality.json` and `docs/DATA.md`, which are committed.
  (g) Fixture CSVs keep CRLF bytes (`.gitattributes`: `-text`) to match the real files.
- Reason: Reproducible, leakage-safe panels with one clock and no silent fills.
- Alternatives: see each item.

## 008. D-3 reconciliation gate failed; recorded, criterion unchanged
- Date: 2026-11-09
- Task: D-3
- Decision (Kouki, 2026-11-09, option "record as failed"): The D-3 criterion "≥ 99.5% of
  industry-months within 1e-4" **fails**: 24.6117% overall (all dates, VW and EW). It is
  recorded as failed and not changed. The reconciliation stays as a report
  (`scripts/d3_reconcile.py`, exit code 1 while the criterion fails). D-4 may proceed after the
  `prereg-v1` tag.
- Cause (investigated on the research period only, 1926-07 to 2005-12):
  1. **VW: tolerance below the data's precision.** Ken French prints returns in percent with
     two decimals, so each daily and monthly value carries up to ±0.5e-4 of rounding. VW: 45.99%
     of 43,878 research months within 1e-4 (between 42% and 48% in every decade); mean signed
     gap under 0.5 bp in every decade; correlation of compounded vs monthly 0.999822. A
     rounding-only simulation gives 52.3% within 1e-4. Shares within looser tolerances (VW,
     research): 2e-4 76.8%, 3e-4 90.4%, 5e-4 96.6%, 1e-3 98.4%, 5e-3 99.7%.
  2. **VW: a 1.4% tail beyond rounding.** 613 of 43,843 VW research months exceed the
     worst-case first-order rounding bound (n_days + 1) × 0.5e-4. Largest: RlEst 1932-04
     (−0.2074), Toys 1990-01 (−0.0950), Gold 1998-10 (−0.0842). Likely composition differences
     between the files (listings/delistings within the month); Unverified.
  3. **EW cannot reconcile by construction.** Compounding daily equal-weighted returns
     (rebalanced daily) is not the monthly equal-weighted return; research share within 1e-4 is
     2.40% and the mean gap is positive (11–221 bp a month by decade).
  No evidence of a parsing, date-alignment or compounding bug: a one-period shift would give
  gaps of whole percentage points and a non-zero mean.
- Reason: Changing the tolerance or share after seeing the data would be tuning (CLAUDE.md
  rule 9).
- Alternatives considered: VW-only with a rounding-aware bound (fails 99.5% anyway: 98.6%);
  more investigation of the 613 months (deferred).

## 009. Locked test period and data-integrity checks
- Date: 2026-11-09
- Task: D-2, D-3 (applies to all data checks)
- Decision (Kouki, 2026-11-09, option "full file, counts only"): Data-integrity checks
  (parsing, rule 2 dates, rule 3 missing values, rule 5 outlier flags, rule 4 reconciliation)
  run on every date so a broken test-period file is caught early. For dates from 2006-01-01 on
  only aggregate counts are reported: no values, row-level lists or plots. Row-level reports
  (`reports/data_flags_daily.csv`, `reports/data_reconciliation.csv`) contain research-period
  rows only. The boundaries live in `src/momlab/periods.py`.
- Reason: Resolves the conflict between CLAUDE.md rule 6 and PLAN D-2/D-3 acceptance tests
  that need the full file (e.g. last date ≥ 2026-09-30). Before this decision, D-2 and the first
  D-3 run had computed over all dates; only aggregate counts and shares were looked at.
- Alternatives: research period only (rejected: a test-period data problem would surface only
  when the vault opens at T-2).

## 010. Engine conventions fixed before E-2 to E-6
- Date: 2026-11-09
- Task: E-1 to E-6
- Decision:
  (a) **Arrays inside the loop.** Events and the handler carry NumPy arrays in the handler's
  asset order instead of `pd.Series` (PLAN §3.3 sketch); CLAUDE.md asks for NumPy in the event
  loop. Event arrays are read-only copies.
  (b) **Cash earns RF.** Daily gross return `R = Σ w_i r_i + (1 − Σ w_i)·rf`: a long-short
  book (net 0) earns its spread plus RF on the collateral (PLAN §3.4), a long-only book with
  net weight 1 earns no RF, and a book with zero leverage earns RF.
  (c) **Fills trade to target.** An order created at the close of t trades to its target
  weights at the close of t + fill_lag; the traded Δw is target minus the weights drifted to
  that close, and the cost is charged on that Δw: NAV × (1 − c), c = Σ|Δw|·bps for `FlatBps`.
  (d) **Missing return on a held asset** (e.g. the isolated missing days in Books, LabEq,
  MedEq, Toys): the position earns 0 that day (its price is carried); returns are never copied
  from another day. Each such asset-day is counted in `RunResult`.
  (e) **B4 volatility.** σ = sample standard deviation (ddof 1) of the last 126 daily returns of
  the *unscaled* 12-1 portfolio as held (it drifts between fills and is reset to the unscaled
  target at each fill), × √252; leverage = min(10% / σ, 2.0) (Barroso & Santa-Clara 2015
  scale by the realised variance of the strategy's own returns). Until 126 unscaled returns
  exist, leverage is 0 (B4 holds cash), so B4 starts about six months after B3.
  (f) **12-1 window.** At the rebalance at the end of month M (holding month t = M+1) the score
  uses months M−11 … M−1 (= t−12 … t−2), compounded from daily returns inside the view; an
  asset with a missing day in those months is excluded (rule 3).
  (g) **The trading calendar is known ex ante.** Month-end rebalance dates come from the
  calendar of the panel; exchange calendars are published in advance, so knowing that t is the
  last trading day of its month is not look-ahead.
  (h) **Real-data strategy runs wait for the pre-registration tag.** Like D-4, the E-6
  real-data engine-vs-oracle test computes strategy returns, so it is skipped until the
  `prereg-v1` tag exists (read-only check).
  (i) **Vault tests.** `test_vault_locked` sets `MOMLAB_UNLOCK_TEST` inside the test process
  (monkeypatch) on synthetic data with the git-tag check faked; this is the plan's own
  acceptance test. No real data is ever unlocked.
- Reason: PLAN §3.2 fixes the order of steps but not these formulas; both the engine and the
  independent oracle must implement the same ones.
- Alternatives: (c) executing the order's Δw computed at t (final weights would miss the
  target by one day of drift); (e) ex-ante vol of the current target from trailing asset
  returns (no warm-up, but not the realised strategy vol the hypothesis cites).

## 011. Poisoned-future test records decisions; NAV wipe-out stops a run
- Date: 2026-11-09
- Task: E-6
- Decision: The engine raises `RuntimeError("NAV wiped out …")` when a day's growth factor is
  ≤ 0 instead of continuing with a negative NAV. With every return after t set to +1000%, a
  long-short book whose drifted weights no longer net to exactly zero is wiped out after t, so
  the poisoned-future test records every signal and every risk-adjusted target through
  wrappers and accepts a wipe-out only when it happens after t. A separate test checks that
  the daily results up to t are bit-identical when the future is NaN.
- Reason: The plan's check is about decisions up to t; a bankrupt book after t says nothing
  about look-ahead.
- Alternatives: a softer poison value (would deviate from the plan's +1000%); letting NAV go
  negative (meaningless P&L).

## 012. Metric definitions and the pre-registered HAC t
- Date: 2026-11-09
- Task: E-7
- Decision: (a) Sharpe = mean / sample sd (ddof 1) of excess returns × √252 (daily) or √12
  (monthly); Sortino uses the QuantStats downside deviation sqrt(mean(min(x, 0)²)) over all
  periods; annual return = W^(P/n) − 1 counted in periods, not calendar days; max drawdown
  includes the starting wealth of 1 as the first peak; skew and kurtosis are population
  moments with raw (Pearson) kurtosis, as the PSR/DSR formulas expect.
  (b) Newey-West t uses statsmodels `cov_type="HAC"` (Bartlett kernel, no small-sample
  correction) with default lags floor(4 (T/100)^(2/9)) (Newey & West 1994) when none are given.
  (c) In `performance()`, `sharpe_hac_t` and `sharpe_lo` are computed on calendar-month
  **excess** returns (strategy minus RF, both compounded per month). PREREGISTRATION.md says
  "Newey-West t-stat of monthly net returns" and does not say whether RF is subtracted; the
  engine's long-short book earns RF on its collateral, so testing raw net returns would count
  the T-bill rate as momentum premium. Excess returns are the conservative reading (lower t).
  The raw-net t can be reported next to it. **Flagged for Kouki** to confirm before D-4.
  (d) The stationary bootstrap draws geometric block lengths (mean `mean_block`, wrapping at
  the end), resamples rows of 2-D input jointly, and seeds via `SeedSequence`.
- Reason: The plan names the metrics but not these details; PLAN §9 cross-checks Sharpe,
  Sortino, MDD and CAGR against QuantStats, so its definitions are used where they exist
  (CAGR in QuantStats uses calendar years, a difference to align in that cross-check).
- Alternatives: t on raw net returns (literal reading, inflated by RF); fixed lag 12 for the
  monthly HAC t; excess kurtosis.

## 013. Ledger head record, opt-in logging, metrics in each entry
- Date: 2026-11-09
- Task: E-8
- Decision: (a) Besides the backward hash chain (`prev_sha256` = sha256 of the previous line's
  bytes, 64 zeros for the first), the ledger keeps `experiments/ledger_head.json` with the line
  count and the sha256 of the last line. A chain alone cannot detect deleting the last line or
  appending a line by hand. `verify()` checks both, and `append()` refuses to write onto a
  broken ledger. Lines are canonical JSON (sorted keys, no spaces, LF); non-finite metric
  values are stored as null. The head file should be committed together with the ledger.
  (b) `engine.run(config, log=False)` is the default. Synthetic tests therefore never write to
  the real ledger. From P4 on, every research script must call `run(..., log=True)`; R-1's
  acceptance check "ledger lines = runs" enforces this.
  (c) Each entry's metrics come from `analytics.metrics.performance` on daily net returns with
  the daily Ken French RF and the run's daily turnover (DECISIONS 012). `rank_ic_*` is null for
  rule strategies. `data_manifest_hash` is the sha256 of `data/manifest.json` for runs on
  processed data and null for synthetic handlers. `phase` is "test" when the config's end
  date is on or after 2006-01-01.
- Reason: The plan asks that editing or deleting *any* line fails verification, and that the
  API has no update or delete method.
- Alternatives: logging by default (every unit test run would need a temp ledger or would
  pollute the real one); a signed head (no key management in a free-tools project).

## 014. P3 scope and the synthetic-market checks
- Date: 2026-11-09
- Task: P3 planning, V-1
- Decision: (a) The detailed P3 plan in IMPLEMENTATION_PLAN.md adds corrections C16–C19: the
  profile uses a synthetic panel with the real shape (C16); the bt cross-check runs on
  synthetic markets until `prereg-v1` (C17); purgedcv parity moves to B-2, where DSR and PBO are
  built (C18); and the §9.4 golden regression joins V-6 (C19).
  (b) S1 uses B3 at 0 bp. Its t is the Newey-West t (default lags) of calendar-month net
  returns after the first fill, and its band is `scipy.stats.binom.interval(0.95, 200, 0.05)`.
  (c) S2's "engine estimate within its 95% CI" is checked per holding period. The generator
  gives each period's expected buy-and-hold long-short return from its own picks
  (`(1 + βz/(n−1))^(n−1) − 1` per asset). For each seed, the test asks whether the 95% CI of
  the mean of realised minus expected contains 0. The engine's weights at each fill must equal
  the generator's picks exactly.
  (d) Finding: S2 cannot tell `fill_lag` 1 from 2. With 5 seeds, both covered 0 in 5/5,
  because the 12-1 score barely changes from one month to the next. S2 guards the window,
  the picks and the accounting. Fill timing is guarded by the E-4 unit tests and the hand 3×6
  fixture.
  (e) Seeds run in a `ProcessPoolExecutor`; the worker functions live in `synthetic.py` so
  that spawned Windows processes can import them. The two slow tests take about 2 min 45 s
  on 16 cores.
- Reason: PLAN §9.2 gives the targets but not the estimators.
- Alternatives: a lag-sensitive S2 with a non-persistent planted signal (that would no longer
  be the 12-1 signal the plan names).

## 015. bt cross-check set-up and the commission-rule replica
- Date: 2026-11-09
- Task: V-3
- Decision: (a) The cross-check code lives in `src/momlab/crosscheck.py`, which imports bt
  lazily (bt stays a dev dependency), so the test and `scripts/v3_crosscheck.py` share it.
  (b) The engine runs with RF = 0 in the cross-check, because cash earns nothing in bt.
  Missing returns become 0 in bt's price indices, which is what the engine does for held assets.
  (c) Cause (b) of PLAN §9.3 was read from bt's source (`SecurityBase.allocate`,
  `StrategyBase.rebalance`, `algos.Rebalance`, TOL 1e-16) rather than assumed. bt solves each
  trade so that quantity × price + commission = (w − u)·V; positions closed to zero pay the fee
  from the proceeds. My first guess, positions = target × pre-cost value, explained only about
  half the gap and was dropped. `crosscheck.bt_convention` replicates the real rule and matches
  bt to ≤ 6.4e-15 a day and 1.1e-13 in weights. So the 10 and 50 bp gaps (≤ 4.7 bp/yr on the
  synthetic market) are fully explained, and the engine's own convention (trade exactly to the
  target, pay `bps·Σ|Δw|` from NAV) stays as it is.
- Reason: PLAN §9.3 asks for each difference to be quantified, not tuned away.
- Alternatives: changing the engine to bt's convention (that would make the oracle and the hand
  fixture disagree with the plan's cost definition).

## 016. Profile on a synthetic full-size panel
- Date: 2026-11-09
- Task: V-5
- Decision: `scripts/profile_engine.py` (`tasks.py profile`) times B3 and B4 at 10 bp on a
  synthetic panel of 49 assets × 26,155 bars, the number of weekdays from 1926-07-01 to
  2026-09-30. The panel is dated to end 2005-12-30, because the data handler's vault drops rows
  from 2006 on (C16). Wall time is a plain run; component shares come from a separate
  pyinstrument run (1 ms sampling, self time attributed to the nearest momlab module); peak
  memory comes from a third run under tracemalloc. `reports/profile.html` (3.4 MB, regenerated
  by the target) is gitignored, and `reports/profile.md` is committed.
  Result: 11.15 s (B3) and 10.45 s (B4), target < 30 s met. The O(n²) copy in
  `Portfolio.state` is logged as a known optimisation and not done.
- Reason: rules 6 and 7; run time does not depend on the values.
- Alternatives: profiling the real research period after `prereg-v1` (can be added; 80 years
  instead of 100).

## 017. Golden synthetic regression and the core-coverage gate
- Date: 2026-11-10
- Task: V-6
- Decision: (a) `tests/regression/golden_synthetic.parquet` holds `metrics.performance` for B1,
  B3, B4 and B5 at 10 bp on `synthetic.null_market(n_assets=20, n_years=8, seed=7)` with a
  constant daily RF of 0.0001. Each strategy is loaded from `configs/base.yaml` plus its file
  in `configs/strategies/`, so the golden file also catches config drift. My first draft
  built B5 from `RunConfig` defaults and silently produced B3 (12-1). I caught it because B5's
  metrics equalled B3's, fixed it, and regenerated before first use. The tolerance is 1e-9
  absolute, NaN equals NaN, and a 1e-8 change is tested to fail. `GOLDEN_UPDATE=1` rewrites
  the file and skips the test; every rewrite needs an entry here.
  (b) `tasks.py test` (and so `check`), `tasks.py ci` and the GitHub workflow run
  `coverage report --include=<engine, execution, costs, data/handler> --fail-under=100` after
  pytest.
- Reason: PLAN §9.4.
- Alternatives: a relative tolerance (1e-9 absolute is the plan's wording; metrics are O(1)).
