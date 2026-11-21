# Data

## Sources and terms

_Filled in at D-1 / D-2 (Ken French) and D-6 (ETFs)._

## Ken French file contents

Listed by opening each real CSV (vintage: "created using the 202609 CRSP database", downloaded
2026-11-08). All files are latin-1 text with CRLF line endings; missing values are -99.99 or -999.
Column names in the first monthly block are padded with spaces (`Food `, `Fun  `) and are stripped.

| File | Blocks (title → frequency, rows, first → last) | Used |
|---|---|---|
| `49_Industry_Portfolios.csv` | Average Value Weighted Returns -- Monthly (1203, 1926-07 → 2026-09); Average Equal Weighted Returns -- Monthly (1203, same); Average Value Weighted Returns -- Annual (99, 1927 → 2025); Average Equal Weighted Returns -- Annual (99); Number of Firms in Portfolios (monthly, 1203); Average Firm Size (monthly, $ millions, 1203); Sum of BE / Sum of ME (annual, 101, 1926 → 2026); Value-Weighted Average of BE/ME (annual, 101) | VW and EW monthly returns, number of firms, average firm size. Annual and BE/ME blocks are not used (BE/ME is excluded from core features, leakage item L4) |
| `49_Industry_Portfolios_Daily.csv` | Average Value Weighted Returns -- Daily (26,338, 1926-07-01 → 2026-09-30); Average Equal Weighted Returns -- Daily (26,338) | Both. The daily file has **no** number-of-firms or firm-size blocks |
| `F-F_Research_Data_Factors.csv` | Monthly Mkt-RF, SMB, HML, RF (1203, 1926-07 → 2026-09); annual (99) | Monthly |
| `F-F_Research_Data_Factors_daily.csv` | Daily Mkt-RF, SMB, HML, RF (26,338, 1926-07-01 → 2026-09-30) | All |
| `F-F_Momentum_Factor.csv` | Monthly Mom (1197, 1927-01 → 2026-09); annual (99) | Monthly. Mom is built from prior return months -12 to -2 |
| `F-F_Momentum_Factor_daily.csv` | Daily Mom (26,237, 1926-11-03 → 2026-09-30) | All |
| `F-F_ST_Reversal_Factor.csv` | Monthly ST_Rev (1208, 1926-02 → 2026-09); annual (99) | Rows from 1926-07 |
| `F-F_ST_Reversal_Factor_daily.csv` | Daily ST_Rev (26,467, 1926-01-26 → 2026-09-30) | Rows from 1926-07-01 |

Facts found while parsing (all from `reports/data_quality.json`):

- **Saturdays.** The daily panel has 1,158 Saturday sessions, the last on 1952-05-24 (NYSE
  traded on Saturdays until 1952). Rule 2 accepts Saturdays up to 1952-05-31 and no Sundays.
- **Missing industries.** -99.99 marks industries with no firms: 67,250 missing daily values per
  weighting (Soda, FabPr, Gold, Guns 10,420 days each; Softw 10,925; Hlth 11,903; Rubbr 1,495;
  Paper 927; PerSv 315) and 2,868 missing industry-months in the monthly file. In those months
  "Number of Firms" is 0 and "Average Firm Size" is -99.99.
- **Isolated missing days.** Books, LabEq and MedEq miss one day each and Toys two days in the
  daily file, while the monthly file has a value for those months. Rule 3: never filled.
- **Outliers (rule 5, daily, outside [-50%, +100%]).** 3 VW and 1 EW flags: MedEq VW -53.62% on
  1931-03-26 and +111.82% on 1931-03-27; Paper VW and EW +150.00% on 1932-08-11. Flagged, not
  clipped; the row-level list is in `reports/data_flags_daily.csv` (local only, gitignored).
- **Factor coverage.** Factor daily dates equal the industry daily dates. Mom is missing for the
  first 101 trading days (to 1926-11-02) and the first 6 months (1926-07 to 1926-12).

## Schema

Processed files in `data/processed/` (gitignored), long format, written by
`uv run python tasks.py data`:

| File | Columns | Rows (2026-09 vintage) |
|---|---|---|
| `industry_daily.parquet` | `date` (timestamp), `asset` (category, 49), `weighting` (category `vw`/`ew`), `ret` (float64, simple decimal), `available_at` (= `date`), `n_firms` (Int64, previous month's value), `avg_size` (float64, $ millions, previous month's value), `source_vintage` (category) | 2,581,124 |
| `industry_monthly.parquet` | same columns; `date` is the calendar month-end | 117,894 |
| `factors_daily.parquet` | `date, mkt_rf, smb, hml, rf, mom, st_rev` (decimals) on the FF3 daily dates | 26,338 |
| `factors_monthly.parquet` | same, monthly (month-end) | 1,203 |

Missing returns stay as NaN rows (never dropped, never filled), so every date has all 49 assets.
`n_firms` and `avg_size` on a row in month m are Ken French's values for month m-1 (leakage item
L3, `test_available_at_lag`). `source_vintage` = `crsp=<CRSP vintage>;sha256=<first 16 hex of the
daily zip>`.

## Cleaning rules and their tests

| PLAN §5.3 rule | Function (`src/momlab/data/clean.py`) | Tests |
|---|---|---|
| 1. -99.99 / -999 → NaN; percent → decimal | `rule1_missing_codes` | `test_rule1_missing_codes_and_percent`, `test_rule1_counts_not_scaled`, `test_kenfrench_parse_monthly_returns`, `test_no_missing_codes_left` (data) |
| 2. Dates strictly increasing, unique, trading days; monthly = month-end | `rule2_dates` | `test_rule2_monthly_ok_and_failures`, `test_rule2_daily_weekends`, `test_daily_date_range_matches_manifest` (data), `test_monthly_dates_are_month_ends` (data) |
| 3. No forward-fill of returns; consumers exclude assets with NaN in the lookback | `rule3_missing_returns` (report only) | `test_rule3_reports_missing_and_never_fills` |
| 4. Daily-compounded months match monthly within 1e-4 | D-3 | D-3 |
| 5. Daily values outside [-0.5, +1.0] flagged, not clipped | `rule5_flag_outliers` | `test_rule5_flags_without_clipping` |

## Vintages and hashes

_From `data/manifest.json`; filled in at D-1 / D-2._

## Daily vs monthly reconciliation

Rule 4 (task D-3), `scripts/d3_reconcile.py`, function `clean.reconcile_panels`. Daily returns
are compounded to calendar months (a month with any missing day has no compounded value) and
compared with the monthly file. **Criterion as written: ≥ 99.5% of industry-months within 1e-4.
Result: 24.6117% (all dates, VW and EW) → FAILED, recorded, not changed (DECISIONS 008).**

| Weighting | Research months compared (1926-07 to 2005-12) | Within 1e-4 | One side missing | Test period (counts only) |
|---|---|---|---|---|
| VW | 43,878 | 20,179 (45.99%) | 35 | 6,083 of 12,201 within |
| EW | 43,878 | 1,051 (2.40%) | 35 | 291 of 12,201 within |

Why it fails, in short: Ken French prints returns to 0.01%, so rounding alone puts about half of
VW months outside 1e-4 (simulation: 52.3% within). VW gaps show no bias (mean under 0.5 bp per
decade, correlation 0.99982); 1.4% of VW months exceed a worst-case rounding bound, probably
composition effects (largest: RlEst 1932-04, −20.7 pp). EW cannot match by construction
(daily-rebalanced vs monthly equal weighting). Full numbers: DECISIONS 008 and
`reports/data_reconciliation_summary.json`; the row-level list (research period, every mismatch
marked `within_tol = False`) is `reports/data_reconciliation.csv` (local only).

Consequence for the project: VW daily returns are the engine's input; their monthly compounding
agrees with the published monthly VW file up to rounding in about 98.6% of months. EW results
(an ablation) are built from daily EW returns and will **not** equal the published monthly EW
series.

## Leakage items L3, L10, L11

_Filled in at D-8._

## ETF data and spread estimate

_Filled in at D-6 / D-7._
