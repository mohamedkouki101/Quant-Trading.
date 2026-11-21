# Hand-worked trades: 3 assets × 6 days (`hand_trades_3x6.csv`)

Worked out from the formulas below with exact fractions (Python `fractions.Fraction` used as a
calculator; no `momlab` code involved), then written to the CSV as floats. The engine must match
every number to 1e-12 (`tests/unit/test_engine.py::test_hand_computed_trades_3x6`).

Setup: assets X, Y, Z; daily rf = 0.0001; flat cost 10 bp; `fill_lag = 1`; start with NAV 1 in
cash. Targets are decided at the close of day 0, 2 and 4 and fill at the close of day 1, 3, 5:

| Decided | Fills | Target (X, Y, Z) |
|---|---|---|
| 2001-01-01 | 2001-01-02 | 0.5, 0.3, −0.2 |
| 2001-01-03 | 2001-01-04 | 0.2, 0.2, 0.2 |
| 2001-01-05 | 2001-01-08 | −0.1, 0.4, 0.0 |

Formulas for each day t (weights `w` are those held into the day):

1. gross: `R_t = Σ w_i r_i,t + (1 − Σ w_i) · rf`
2. growth: `g_t = 1 + R_t` (no holding cost here)
3. drift: `w_i ← w_i (1 + r_i,t) / g_t`; `NAV ← NAV · g_t`
4. on a fill day: `Δw = target − w` (drifted weights), `turnover = Σ|Δw|`
5. `cost = 0.001 · turnover`
6. `NAV ← NAV · (1 − cost)`; `w ← target`
7. net: `NAV_t / NAV_{t−1} − 1`

Worked lines:

- 2001-01-01: no position, `R = rf = 0.0001`, net 0.0001, NAV 1.0001.
- 2001-01-02: still no position, `R = 0.0001`; fill to (0.5, 0.3, −0.2): turnover 1.0, cost
  0.001; net = 1.0001 × 0.999 − 1 = −0.0009001.
- 2001-01-03: `R = 0.5(−0.02) + 0.3(0.01) − 0.2(0.02) + 0.4(0.0001) = −0.01096`; drift
  X = 0.5 × 0.98 / 0.98904, Y = 0.3 × 1.01 / 0.98904, Z = −0.2 × 1.02 / 0.98904.
- 2001-01-04: `R = w_X(0.03) + w_Y(0) + w_Z(−0.02) + (1 − Σw)(0.0001) ≈ 0.0190286`; then the fill
  to (0.2, 0.2, 0.2) trades from the weights drifted again by that day's returns.
- 2001-01-05: `R = 0.2(0.01 + 0.02 + 0.01) + 0.4(0.0001) = 0.00804`.
- 2001-01-08: drifted weights earn their returns, then the fill to (−0.1, 0.4, 0).
