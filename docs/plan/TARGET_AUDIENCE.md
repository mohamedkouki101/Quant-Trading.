# What internship screeners look for

Research date: 2026-11-06. Every source below was opened today. Postings are for Summer 2027 or the 2027 cycle unless noted. Aggregator copies are tagged Medium because I did not see the firm's own page.

## 1. Evidence

| # | Firm and role | What the posting says (quoted or close paraphrase) | Source | Confidence |
|---|---|---|---|---|
| A1 | Jane Street, Quantitative Researcher Internship | Interns "analyse large datasets, build and test models, and create new trading strategies"; want "A strong programmer who's comfortable with Python"; "We don't expect you to have a background in finance"; research experience a plus; clear communication. | [janestreet.com](https://janestreet.com/join-jane-street/position/7524506002) | High |
| A2 | Two Sigma, Quantitative Researcher Intern 2027 | "Use the scientific method to develop sophisticated investment models"; "Apply quantitative techniques like machine learning"; "Performed an in-depth research project, examining real-world data"; "You don't need a background in finance." | [careers.twosigma.com](https://careers.twosigma.com/careers/JobDetail/New-York-New-York-United-States-Quantitative-Researcher-Intern-2027-Summer/13945) | High |
| A3 | IMC, Quantitative Research Intern (BS/MS) 2027 | "Superior numerical, analytical, and critical thinking skills"; "passion for research"; "eager to develop trading intuition"; Python, C or C++ "highly desired". | [imc.com](https://www.imc.com/ap/careers/jobs/4907399101) | High |
| A4 | Optiver, Quantitative Research Internship (2027 start, Amsterdam) | Turn "financial market data into quantitative insights and trading strategies"; test hypotheses on large datasets; "Excellent research, analytical and modelling skills"; ML and time-series analysis a plus. | [optiver.com](https://optiver.com/join-us/jobs/quantitative-research-and-machine-learning/amsterdam/quantitative-research-internship-2027-start) | High |
| A5 | Aquatic Capital, Quantitative Researcher Intern 2027 | "design, implement, and evaluate research systems components using rigorous statistical methodologies"; "Proficiency in Python"; "conducting and completing statistical or applied mathematical research"; math competitions a plus. | [greenhouse.io](https://job-boards.greenhouse.io/aquaticcapitalmanagement/jobs/8489186002) | High |
| A6 | D. E. Shaw, Quantitative Analyst Intern 2027 | "exploring a variety of statistical modeling techniques and writing software to analyze financial data"; Python data manipulation preferred; "no previous finance experience is necessary". | [Kadoa aggregator copy](https://www.kadoa.com/quant/job/d-e-shaw-careers-quantitative-analyst-intern-new-york-summer-2027-14f62c93) | Medium |
| A7 | JPMorganChase, QR Markets Summer Analyst 2027 | "Conduct alpha research, calibrate model parameters"; "Demonstrates research skills (through coursework, projects, or academic work)"; "Presents findings clearly to non-technical audiences"; preferred: "manage projects independently", ML and data science. | [Built In NYC copy](https://www.builtinnyc.com/job/2027-quantitative-research-markets-summer-internship-analyst-united-states/10498025) | Medium |
| A8 | JPMorganChase, QR Risk and Treasury Summer Associate 2027 | "Conduct back testing and assess strategies"; "Assess models for conceptual soundness, risks, and enhancements"; Python and/or C++; "Excellent communication skills". | [UMB careers copy](https://aces.umb.edu/jobs/jpmorganchase-2027-quantitative-research-risk-and-treasury-summer-internship-associate-united-states/) | Medium |
| A9 | Goldman Sachs, AWM Quantitative Strategists Summer Analyst | "construct quantitative models"; "advanced training in mathematics, programming and logical thinking"; "talents for research, analysis". | [higher.gs.com](https://higher.gs.com/roles/171550) | High |
| A10 | BlackRock, 2027 Quantitative Masters Internship (Investments) | Systematic team "emphasizes data-driven insights, scientific testing of investment ideas"; "Coding & programming skills (Python or similar)"; "Ability to distill and communicate large amounts of information succinctly"; "Passion for investing". | [careers.blackrock.com](https://careers.blackrock.com/job/san-francisco/2027-quantitative-masters-internship-program-investments-portfolio-management-san-francisco/45831/100661849744) | High |
| P1 | Tradermath, "Backtesting interview questions" (prep site, author unnamed, Sept 2026) | Interviews test whether you can judge how much a result should be trusted: leakage first, then sample size, selection, costs; purged and embargoed CV; survivorship and point-in-time data; count every variant tried (deflated Sharpe); costs and capacity; "Identify your project's weaknesses and fixes before the interviewer does." Theme: "given how this result was produced, how much should anyone believe it?" | [tradermath.org](https://www.tradermath.org/articles/backtesting-interview-questions) | Medium (prep site) |
| P2 | Quantt, "Quant resume guide" (prep site) | "Recruiters skim for evidence: repos, competitions, research, measurable outcomes"; "Interviewers will probe anything on your CV"; bullet = "action + method + quantified result". | [quantt.co.uk](https://www.quantt.co.uk/resources/quant-resume-guide) | Low–Medium (prep site; see conflict C7 in the inventory) |

Not covered: Citadel and Hudson River Trading pages failed to load today. Sell-side risk roles are represented only by A8.

## 2. Signals the project must send

| ID | Signal | Evidence | Plan elements that deliver it |
|---|---|---|---|
| SG1 | Strong, clean Python | A1, A3, A5, A6, A7, A8, A10 | Event-driven engine with typed interfaces (§3), tests and coverage report (§9), CI, profile (§3.7), pinned env (§4) |
| SG2 | Scientific method: hypothesis first, then test | A2, A4, A10 | Pre-registration before results (§2), falsification tests, two-sided hypotheses, locked test vault (§5.4) |
| SG3 | Statistical rigour | A5, A6, A4, P1 | HAC t-stats, DSR, PBO, Harvey-Liu haircut, block bootstrap, purged walk-forward and CPCV (§7, §8) |
| SG4 | A finished, in-depth project on real data | A2, A5, A7 | 100 years of daily industry data plus a tradable ETF leg; shipped repo, app, model card (§10, §11) |
| SG5 | Can backtest and assess a model's soundness | A8, A7, P1 | Engine verification triangle: hand-computed trades, synthetic known-answer markets, bt cross-check (§9); model card in SR 26-2 spirit (§11) |
| SG6 | Calibrated trust in own results | P1 | Honesty protocol with 10 self-deception tests (§8), trial ledger, 5 proactive weaknesses (§12) |
| SG7 | Explains clearly to non-specialists | A1, A7, A8, A10 | 60-second demo, 3- and 10-minute talk tracks, README results-first, app with a cost slider (§1, §11, §12) |
| SG8 | Applied ML, with judgement | A2, A4, A7 | LightGBM vs linear vs rules progression, Nagel test, grouped permutation importance and SHAP with stability (§7) |
| SG9 | Market intuition | A3, A10 | Costs, borrow, capacity, crash analysis, regime sub-periods, why the edge might exist and what kills it (§2, §8) |
| SG10 | Independent ownership | A2, A4, A7 | Solo end-to-end build with an experiment log, risk register and decisions log (§6, §14) |

## 3. What the project does not do for you

- Several postings say finance knowledge is not required (A1, A2, A6). Depth of method and code matters more than finance vocabulary, so the plan spends effort on verification and statistics, not on exotic finance.
- Math competitions and probability are screened separately (A5 lists IMO and Putnam). No project replaces probability and mental-math prep; the learning path flags this at the end.
- Trading-firm roles (A3, A4) emphasise options and fast decisions. This project is a medium-frequency research project; say so rather than stretch it.
