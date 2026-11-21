# Interview kit

Rule: every number comes from your results and is traceable to a ledger `trial_id`. Never invent or round up. Brackets are blanks.

## 1. CV bullet templates

Format: action + method + quantified result ([Quantt](https://www.quantt.co.uk/resources/quant-resume-guide), Low–Medium; Phase 1's [Bock X-Y-Z](https://www.businessinsider.in/googles-former-hr-boss-says-this-is-the-key-to-a-perfect-resume/articleshow/54925993.cms), Medium). For research roles, lead with how much the result can be trusted ([Tradermath](https://www.tradermath.org/articles/backtesting-interview-questions), Medium).

1. **Engine:** "Built an event-driven backtest engine in Python ([N] lines, [M] tests, [C]% coverage) that rules out look-ahead by construction; verified against hand-computed trades, synthetic markets with known answers, and the open-source bt library (within [x] bp/yr)."
2. **Research:** "Tested vol-scaled industry momentum on 100 years of data under a pre-registered protocol: net Sharpe [a] at [c] bp costs (1927–2005), [b] in a locked 2006–2026 test, deflated Sharpe [d] across [T] logged trials."
3. **ML + importance:** "Compared a LightGBM ranker with [F] features against rule-based momentum using purged walk-forward CV; [result: e.g. 'no significant gain, Sharpe difference [Δ], 90% CI [lo, hi]']; grouped permutation importance attributed [p]% to [group], stable in [k] of [K] folds."

Variant for DS/risk roles: swap bullet 2 for "Wrote a model card and validation suite (SR 26-2 spirit) covering conceptual soundness, outcomes analysis and [n] documented limitations."

## 2. Twenty-five probing questions with answer outlines

**Engine and verification**
1. *How do you know there is no look-ahead?* AsOfView with cursor bound; fill_lag ≥ 1 validated; poisoned-future test (decisions bit-identical when future set to NaN or extreme); engine equals vectorised oracle; bt agreement.
2. *Why event-driven rather than vectorised?* Mirrors live order flow; timing becomes structural; extends to fills and costs per order. Cost: speed and complexity, handled by the oracle for sweeps once parity is proven ([QuantStart](https://www.quantstart.com/articles/Event-Driven-Backtesting-with-Python-Part-I)).
3. *Walk me through one rebalance.* Month-end close t: mark-to-market, signal from data ≤ t, risk scaling, order, fill at t+1 close with cost on |Δw|, returns from t+2.
4. *Why did your engine and bt differ by [x]?* Decomposition from `reports/crosscheck.md`: trade timing convention, commission handling, cash residuals, floating point.
5. *What was the hardest bug?* Your real story; show the test that now guards it.
6. *How fast is it and where is the time spent?* Profile numbers; what you optimised and why you stopped.

**Data**
7. *Why industry portfolios, not stocks?* Survivorship-free and free; much of stock momentum is industry momentum ([Moskowitz & Grinblatt](https://ideas.repec.org/a/bla/jfinan/v54y1999i4p1249-1290.html)); trade-off: not tradable, so the ETF leg exists.
8. *Is your data point-in-time?* Industry membership set each June from prior-year SIC (Ken French details); lagged n_firms/size; vintage hashes; residual risk: CRSP revisions.
9. *How did you handle missing data?* -99.99/-999 → NaN; exclude asset from that cross-section; never forward-fill returns.

**Strategy and finance**
10. *Why should momentum exist at all?* Under-reaction and slow diffusion vs risk compensation (crash risk); evidence across assets; what kills it: crowding, decay, rebounds.
11. *Why skip the most recent month?* Short-term reversal at stock level; at industry level you tested the 1-month sign two-sided (your H4 result).
12. *What happened in 2009?* Momentum crash in the rebound after a bear market ([Daniel & Moskowitz](https://www.nber.org/papers/w20439)); what vol scaling saved in your data.
13. *How did you model costs, and would this survive real trading?* Industry: sweep and break-even; ETF: measured spreads, borrow, square-root impact, capacity curve; [Frazzini, Israel & Moskowitz](https://www.aqr.com/Insights/Research/Working-Paper/Trading-Costs-of-Asset-Pricing-Anomalies) on real costs.
14. *What is your capacity?* ETF curve; AUM where impact eats half the alpha; industry leg has none by design.
15. *Is your alpha just the Mom factor?* Factor regression with HAC t; alpha vs loadings.

**Statistics and overfitting**
16. *How many things did you try?* Exact ledger count; trial budget pre-registered; DSR and PBO computed on all of them.
17. *Explain the deflated Sharpe ratio.* Probability the true Sharpe exceeds the expected maximum Sharpe from N trials of noise, adjusting for skew, kurtosis and length ([Bailey & López de Prado](https://papers.ssrn.com/abstract=2460551)).
18. *Why not ordinary k-fold?* Serial dependence and overlapping labels leak; purge and embargo; walk-forward plus CPCV.
19. *How confident is your Sharpe?* Standard error, Lo adjustment for autocorrelation ([Lo 2002](https://ideas.repec.org/a/taf/ufajxx/v58y2002i4p36-52.html)), block bootstrap CI; 20 years of test is short.
20. *Why t > 3?* Multiple testing across the profession ([Harvey, Liu & Zhu](https://www.nber.org/papers/w20592)); your own haircut ([Harvey & Liu](https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF)).
21. *What would convince you the strategy is dead?* Pre-registered kill criteria; monitoring triggers from the model card.

**ML and feature importance**
22. *Did ML beat simple momentum?* Your H3 result with CI; Nagel's argument; momentum-only ablation.
23. *What does permutation importance actually measure?* Drop in held-out score when a feature group's link to the label is broken; model-specific; correlated features share credit, hence grouping ([scikit-learn](https://scikit-learn.org/stable/auto_examples/inspection/plot_permutation_importance_multicollinear.html)).
24. *SHAP vs permutation: which do you trust?* Different questions: SHAP attributes predictions (direction, shape), permutation measures predictive reliance; interventional vs path-dependent SHAP treat correlation differently ([SHAP docs](https://shap.readthedocs.io/en/stable/generated/shap.TreeExplainer.html)); agreement across both and across folds is the finding.
25. *If you had a quant's budget, what next?* Point-in-time stock data, live paper trading, transaction-cost data, other countries, a proper execution model.

## 3. Five weaknesses to disclose proactively

1. Industry portfolios are not tradable; the ETF leg has only 9 assets and ~27 years.
2. The locked test (2006–2026) is short for Sharpe inference; the CI is wide.
3. No liquidity features at industry level, so the comparison with Gu-Kelly-Xiu is partial.
4. Costs are modelled, not observed (except sampled ETF spreads from IEX-only quotes); borrow is assumed.
5. I already knew the momentum literature, including the 2009 crash, before designing the test; pre-registration limits but cannot remove that bias.

## 4. Talk tracks

**3 minutes**
- 0:00 Question: does momentum survive honest testing, and does ML add anything?
- 0:30 Why it matters: most backtests fool their authors; my product is an engine that can't peek, plus a protocol that counts every trial.
- 1:00 Engine: daily clock, as-of view, next-day fills; three independent checks agree within [x].
- 1:40 Results: net Sharpe [a] at [c] bp; break-even [y] bp; deflated Sharpe [d] across [T] trials; locked test [b].
- 2:20 ML: [result]; importance says [group], stable in [k]/[K] folds; it's [not] momentum in disguise.
- 2:45 What I'd do next, and one weakness I'd fix first.

**10 minutes**
1. (1 min) Question, hypotheses, what was pre-registered.
2. (2 min) Engine design: timing diagram, interfaces, the poisoned-future test, a bug it caught.
3. (1 min) Verification triangle and the bt difference decomposition.
4. (1 min) Data: why industries, point-in-time issues, ETF leg.
5. (2 min) Results: baseline table, cost curve, crash months, sub-periods, locked test.
6. (1.5 min) ML and importance: grouped permutation vs SHAP, stability, Nagel test.
7. (1 min) Five weaknesses, and what result would change my mind.
8. (0.5 min) Engineering: tests, coverage, profile, reproducibility in one command.
