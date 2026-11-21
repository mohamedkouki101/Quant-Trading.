# Quant strategy project: Phase 1 research

Nov 6, 2026 · @Kouki

## Recommendation and assumptions

**Build a momentum strategy, not mean-reversion.** Specifically: cross-sectional industry momentum (12-1 month) with volatility scaling, tested on survivorship-free Ken French industry portfolios back to 1926, then checked for implementability on liquid sector ETFs. Mean-reversion (short-term reversal) is the deliberate counter-feature and baseline, not the main strategy.

Why momentum wins for this project:

- **Evidence base is deeper and more recent.** Momentum shows up in US stocks, 58 futures markets, eight asset classes and 110+ years of data ([Jegadeesh & Titman 1993](https://ideas.repec.org/a/bla/jfinan/v48y1993i1p65-91.html), [Moskowitz, Ooi & Pedersen 2012](https://papers.ssrn.com/abstract=2089463), [Asness et al. 2013](https://www.aqr.com/library/journal-articles/value-and-momentum-everywhere), [Hurst et al. 2017](https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing)). High confidence.
- **Short-term reversal mostly dies after costs.** Its largest profits sit in illiquid stocks and are smaller than likely transaction costs ([Avramov, Chordia & Goyal 2006](https://ideas.repec.org/a/bla/jfinan/v61y2006i5p2365-2394.html)). High confidence. Strategies with monthly turnover above 50% rarely survive costs ([Novy-Marx & Velikov 2016](https://nber.org/papers/w20721)). High confidence.
- **Free data fits.** Monthly or daily momentum works on free end-of-day data. Credible intraday mean-reversion needs tick or minute data and realistic spreads, which free sources do not give (see Section 5). Medium confidence (my inference from the data sources reviewed).
- **Better story for the feature study.** ML papers find momentum, liquidity and volatility are the dominant predictors ([Gu, Kelly & Xiu 2020](https://nber.org/papers/w25398)), so a feature importance study has a known answer to test against. High confidence.
- **Known failure mode to study.** Momentum crashes are partly forecastable, and volatility management roughly doubles its Sharpe ratio ([Daniel & Moskowitz 2016](https://www.nber.org/papers/w20439), [Barroso & Santa-Clara 2015](https://econpapers.repec.org/RePEc:eee:jfinec:v:116:y:2015:i:1:p:111-120)). This gives you a real research question, not just a backtest. High confidence.

**Assumptions** (the prompt left these as placeholders, so I filled them in):

| Item | Assumed value |
| --- | --- |
| Skill level | Intermediate Python and ML |
| Time | 4 weeks at about 10 hours a week (40 hours total) |
| Tools | Python, pandas, NumPy, scikit-learn, LightGBM, SHAP, Streamlit |
| Show | A self-written backtest engine, a momentum vs mean-reversion comparison, and a feature importance study |
| Market | US equities, sector or industry level, daily and monthly bars |
| Budget | Free data, with an optional paid tier under $30 a month |

Confidence tags used below: **High** = primary source opened and it says this directly. **Medium** = secondary source, or my inference from primary sources. **Low** = weak or single secondary source. **Unverified** = no source; my judgement.

## 1. Problem and context

The problem: decide, from past prices alone, which assets to hold next period, then prove the edge is real after costs and not an artifact of the research process.

**The two families**

- **Momentum** buys recent winners and sells recent losers. Stock-level momentum pays over 3 to 12 month holding periods, and part of it reverses over the next two years ([Jegadeesh & Titman 1993](https://ideas.repec.org/a/bla/jfinan/v48y1993i1p65-91.html)). High. Time-series momentum (trend following) shows the same 1 to 12 month persistence in each of 58 futures markets ([Moskowitz, Ooi & Pedersen 2012](https://papers.ssrn.com/abstract=2089463)). High. Much of stock momentum is really industry momentum ([Moskowitz & Grinblatt 1999](https://ideas.repec.org/a/bla/jfinan/v54y1999i4p1249-1290.html)). High.
- **Mean-reversion** bets that recent moves undo. Weekly losers rebound and weekly winners fall ([Lehmann 1990](https://www.nber.org/papers/w2533)). High. Pairs trading earned up to 11% a year in excess returns on US stocks from 1962 to 2002 ([Gatev, Goetzmann & Rouwenhorst 2006](https://econpapers.repec.org/RePEc:oup:rfinst:v:19:y:2006:i:3:p:797-827)). High. Because of short-term reversal, academic momentum skips the latest month (the "12-1" signal) ([Alpha Architect summary](https://alphaarchitect.com/quantitative-momentum-research-short-term-return-reversal/)). Medium.

**Who uses it in industry**

- **Managed futures funds and CTAs** run trend following. Hurst, Ooi and Pedersen argue time-series momentum explains managed futures returns since the late 1980s ([AQR 2017](https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing)). High.
- **Factor and quant equity managers** hold momentum as a standard factor next to value ([Asness, Moskowitz & Pedersen 2013](https://www.aqr.com/library/journal-articles/value-and-momentum-everywhere)). High.
- **Statistical arbitrage desks** run market-neutral mean-reversion on residual returns, using PCA or sector-ETF factors ([Avellaneda & Lee 2010](https://ideas.repec.org/a/taf/quantf/v10y2010i7p761-782.html)). High.
- **Quant trading firms** frame this as ML forecasting on noisy, fat-tailed, non-stationary data, as in Jane Street's Kaggle competition ([competition page clipping](https://anilkeshwani.github.io/garden/Clippings/Jane-Street-Real-Time-Market-Data-Forecasting--Kaggle)). Medium (secondary copy of the Kaggle page).

**Why it matters**

- Most published edges shrink: across 97 predictors, returns are about 26% lower out of sample and 58% lower after publication ([McLean & Pontiff 2016](https://academicnewsletter.sufe.edu.cn/info/359722)). High.
- With hundreds of factors tested, a new factor should clear a t-statistic of 3.0, not 2.0 ([Harvey, Liu & Zhu 2016](https://www.nber.org/papers/w20592)). High.
- So the skill employers pay for is less "find a strategy" and more "test one honestly". A portfolio project that shows that discipline stands out. Unverified (my judgement).

## 2. Existing projects and solutions

Ten reference points: six papers, three open-source platforms and one Kaggle competition. Results are as reported by the authors, gross of real-world frictions unless stated. Confidence is High for every row (primary or official page opened) unless marked.

| Name | Approach | Data | Results | Limitations |
| --- | --- | --- | --- | --- |
| [Jegadeesh & Titman 1993](https://ideas.repec.org/a/bla/jfinan/v48y1993i1p65-91.html) | Cross-sectional stock momentum, 3–12 month formation and holding | US stocks | Significant positive returns over 3–12 months; partial reversal in years 2–3 | Abstract page gives no numbers; pre-cost; long sample is mostly pre-1990 |
| [Moskowitz, Ooi & Pedersen 2012](https://papers.ssrn.com/abstract=2089463) | Time-series momentum (trend) per instrument | 58 liquid futures: equity, FX, commodities, bonds | Momentum in all 58; diversified portfolio earns large abnormal returns; best in extreme markets | Futures data is not free; reverses at longer horizons |
| [Gatev, Goetzmann & Rouwenhorst 2006](https://econpapers.repec.org/RePEc:oup:rfinst:v:19:y:2006:i:3:p:797-827) | Pairs trading: match by normalised price distance, trade divergence | Daily US stocks 1962–2002 | Up to 11% annualised excess return | Sample ends 2002; later decay not covered here |
| [Avellaneda & Lee 2010](https://ideas.repec.org/a/taf/quantf/v10y2010i7p761-782.html) | Stat-arb mean-reversion on PCA or sector-ETF residuals | Broad US equity universe | Sharpe 1.44 (PCA, 1997–2007) net of costs; 0.9 for 2003–2007 | Performance fell after 2002–2003; needs daily rebalancing of a large universe |
| [Gu, Kelly & Xiu 2020](https://nber.org/papers/w25398) | Compare ML models for expected returns | US stocks with many firm characteristics (CRSP-based) | Trees and neural nets win; up to about 2x the Sharpe of regression strategies; momentum, liquidity and volatility dominate | Needs CRSP/Compustat (paid); small, illiquid stocks inflate long-short results (Unverified for this paper) |
| [Lim, Zohren & Roberts 2019](https://arxiv.org/abs/1904.04912) | Deep Momentum Networks: LSTM sizes positions, trained on Sharpe | 88 continuous futures | More than 2x Sharpe of classic TSMOM before costs; edge holds to about 2–3 bp costs | Edge fades past 2–3 bp costs; deep model is hard to audit |
| [Wood et al. 2021 Momentum Transformer](https://arxiv.org/abs/2112.08534) | Attention plus LSTM for momentum and mean-reversion regimes | Futures (per paper) | Beats TSMOM and mean-reversion baselines, including net of costs; adapted to the 2020 regime | Same authors' group; complex; results not independently replicated here |
| [Microsoft Qlib](https://github.com/microsoft/qlib/blob/main/README.md) | Full ML quant platform: data, models (LightGBM to Transformers), backtest; RD-Agent LLM factor mining | Alpha158/Alpha360 features, US and China | Benchmarks per model in repo | Official dataset disabled; Yahoo data "might not be perfect"; heavy framework, hides the engine |
| [zipline-reloaded](https://awesome.ecosyste.ms/projects/github.com%2Fstefan-jansen%2Fzipline-reloaded) and [backtesting.py](https://awesome.ecosyste.ms/projects/github.com%2Fkernc%2Fbacktesting.py) | Event-driven (zipline) and simple single-asset (backtesting.py) backtest libraries | Bring your own | Mature tools; 1.6k and 6.4k GitHub stars | backtesting.py is AGPL-3.0 and single-asset; neither shows your own engine skills |
| [Jane Street Real-Time Market Data Forecasting (Kaggle)](https://anilkeshwani.github.io/garden/Clippings/Jane-Street-Real-Time-Market-Data-Forecasting--Kaggle) | Predict anonymised responders from production features | Anonymised features from Jane Street systems; 11.5 GB download ([fintorch tutorial](https://fintorch.readthedocs.io/en/stable/tutorials/marketdata/marketdata.html)) | Leaderboard-based | Anonymised features make a feature importance study meaningless economically; Medium confidence (secondary pages) |

Takeaway: the papers prove the effects exist; the repos give engines you are told not to use. The open gap is a small, transparent engine plus an honest, overfitting-aware feature study, which none of these packages as one product. Unverified (my judgement).

## 3. Limits and common pitfalls

The biggest risk is a backtest that looks great because of how it was built. Each pitfall below gets a guard you will build into the engine.

| Pitfall | Type | What goes wrong | Guard in this project | Source and confidence |
| --- | --- | --- | --- | --- |
| Look-ahead bias | Technical | Signal uses a price not yet known at trade time (e.g. today's close to trade at today's close) | Signals at t, fills at t+1 open or close; a unit test that shifts data and fails on any future peek | [SR 11-7 on outcomes analysis](https://www.federalreserve.gov/supervisionreg/srletters/sr1107.htm) frames backtests on data not used in development; the test design is Unverified |
| Label leakage in CV | Methodological | Overlapping forward-return labels leak across folds | Purged k-fold with embargo, or CPCV | [López de Prado 2018, ch. 7 and 12](https://www.wiley-vch.de/de/fachgebiete/finanzen-wirtschaft-recht/advances-in-financial-machine-learning-978-1-119-48208-6) High; [purging and embargo overview](https://en.wikipedia.org/wiki/Purged_cross-validation) Low (Wikipedia, flagged for deletion) |
| Backtest overfitting | Methodological | Trying many variants and reporting the best | Log every trial; report Deflated Sharpe Ratio and PBO | [Bailey & López de Prado 2014](https://papers.ssrn.com/abstract=2460551), [Bailey et al. 2015](https://papers.ssrn.com/abstract=2326253) High |
| Multiple testing | Methodological | t > 2 is too easy with hundreds of tries | Use t > 3 hurdle | [Harvey, Liu & Zhu 2016](https://www.nber.org/papers/w20592) High |
| Single-path walk-forward | Methodological | One historical path gives a high-variance estimate | Add CPCV paths next to walk-forward | [Joubert et al. 2024, via overview](https://en.wikipedia.org/wiki/Purged_cross-validation) Low (not opened directly) |
| Survivorship bias | Data | Free stock lists omit delisted firms, flattering returns | Use Ken French industry portfolios and ETFs, not today's S&P 500 list | [Brown et al. 1992](https://ideas.repec.org/a/oup/rfinst/v5y1992i4p553-80.html) High; [Yahoo lacks delisted tickers](https://r-bloggers.com/2021/08/when-yahoo-finance-doesnt-have-de-listed-tickers-needed) Medium |
| Transaction costs and turnover | Finance | High-turnover strategies die after costs | Cost model with spread plus commission; sweep 0–50 bp; report turnover | [Novy-Marx & Velikov 2016](https://nber.org/papers/w20721) High |
| Reversal is a liquidity effect | Finance | Short-term reversal profits sit in illiquid names and are below costs | Treat reversal as a feature and baseline, not the product | [Avramov, Chordia & Goyal 2006](https://ideas.repec.org/a/bla/jfinan/v61y2006i5p2365-2394.html) High |
| Momentum crashes | Finance | Sharp losses in market rebounds after panics | Volatility scaling; market-state features | [Daniel & Moskowitz 2016](https://www.nber.org/papers/w20439), [Barroso & Santa-Clara 2015](https://econpapers.repec.org/RePEc:eee:jfinec:v:116:y:2015:i:1:p:111-120) High |
| Alpha decay | Finance | Published edges shrink after publication | Report pre- and post-1993 performance separately | [McLean & Pontiff 2016](https://academicnewsletter.sufe.edu.cn/info/359722) High |
| Misleading feature importance | ML | Impurity importance is biased to high-cardinality features and computed on train data; correlated features hide each other | Permutation importance on held-out folds; cluster correlated features | [scikit-learn docs](https://scikit-learn.org/stable/modules/permutation_importance.html) High |
| LLM look-ahead | ML | LLMs memorise pre-cutoff market data, so their "forecasts" are recall | Do not use LLM features on pre-cutoff periods | [Lopez-Lira, Tang & Zhu 2025](https://arxiv.org/html/2504.14765v2) High |
| Model risk | Regulatory | Unvalidated models drive bad decisions | Write a short model card: soundness, monitoring, outcomes analysis | [SR 26-2 (Apr 2026)](https://www.federalreserve.gov/supervisionreg/srletters/sr2602.htm) supersedes [SR 11-7](https://www.federalreserve.gov/supervisionreg/srletters/sr1107.htm) High |
| Marketing hypothetical returns | Regulatory | SEC fined nine advisers $850k total in Sept 2023 for hypothetical performance violations | Label all results "hypothetical backtest", state assumptions and limits; no return claims aimed at the public | [K&L Gates summary](https://www.klgates.com/thought-leadership/Hypothetical-Performance-Crackdown-Nine-Firms-Charged-With-Violations-of-Investment-Adviser-Marketing-and-Recordkeeping-Rules-9-13-2023) Medium (law-firm summary). The rule binds registered advisers, not a personal project; following it is good practice. Unverified |
| Data licence | Legal | Yahoo data is "intended for personal use only" | Do not redistribute raw Yahoo data in the repo or app | [yfinance README](https://pypi.org/project/yfinance/0.2.35/) High |

**Conflict: is there a replication crisis?** Harvey, Liu and Zhu argue many factors are likely false and raise the bar to t > 3 ([NBER w20592](https://www.nber.org/papers/w20592)). Jensen, Kelly and Pedersen find most factors replicate and work out of sample in 93 countries ([NBER w28432](https://www.nber.org/papers/w28432)). **I trust both, for different things.** JKP is newer, uses a Bayesian model and a much larger out-of-sample test, so momentum itself is likely real. Harvey et al. is about how *you* search: your own trials still need the higher hurdle. Medium (my reading of two High sources).

## 4. Research frontier (2023–2026)

The field is moving in three directions: more complex models, a backlash testing whether that complexity is real, and stricter validation. Your project can sit on the validation side, which is the most portfolio-friendly.

| Date | Development | Why it matters for you | Source and confidence |
| --- | --- | --- | --- |
| Oct 2026 | `purgedcv` 0.1.11: scikit-learn-compatible purged k-fold, CPCV, deflated Sharpe, PBO (MIT) | Validation tooling is now pip-installable; you can cross-check your own implementation against it | [PyPI](https://pypi.org/project/purgedcv/) High |
| Apr 2026 | Fed, OCC and FDIC issue SR 26-2, replacing SR 11-7 model risk guidance with a risk-based approach | Cite the current guidance, not SR 11-7, in your model card | [SR 26-2](https://www.federalreserve.gov/supervisionreg/srletters/sr2602.htm) High |
| Dec 2025 | Test for LLM lookahead bias ("Lookahead Propensity"): memorisation inflates LLM return forecasts by about 37% of the standalone effect | LLM sentiment features need a post-cutoff test window | [Gao, Jiang & Yan](https://arxiv.org/html/2512.23847v1) High |
| Aug 2025 | Nagel: "virtuous complexity" results are mostly volatility-timed momentum in disguise | A complex model can rediscover momentum; check yours against plain momentum | [NBER w34104](https://www.nber.org/papers/w34104) High |
| Apr 2025 | LLMs recall exact pre-cutoff market values; forecasting skill is not identified before the cutoff | Same as above | [Lopez-Lira, Tang & Zhu](https://arxiv.org/html/2504.14765v2) High |
| 2023–2025 | LLMs read news headlines: GPT-4 drift strategy Sharpe fell from 6.54 (2021Q4) to 1.22 (Jan–May 2024) as adoption grew | Text signals decay fast; out of scope for a 4-week build | [Lopez-Lira & Tang](https://arxiv.org/html/2304.07619v6) High |
| 2024 | Kelly, Malamud & Zhou: models with more parameters than observations predict market returns better | The "pro-complexity" side of the debate | [J. Finance 2024](https://econpapers.repec.org/RePEc:bla:jfinan:v:79:y:2024:i:1:p:459-503) High |
| 2024 | Chronos: pretrained time-series foundation models (T5-based, 20M–710M parameters), finance among training domains | Optional zero-shot baseline; no finance-specific results in the excerpt | [Ansari et al., TMLR 2024](https://arxiv.org/pdf/2403.07815) High |
| Aug 2024 | Qlib RD-Agent: LLM agents automate factor mining | Automated search raises multiple-testing risk | [Qlib README](https://github.com/microsoft/qlib/blob/main/README.md) High |
| 2023 | Jensen, Kelly & Pedersen: most factors replicate; public data for 153 factors, 93 countries (CC BY-NC 4.0) | Free, high-quality benchmark factor data | [NBER w28432](https://www.nber.org/papers/w28432), [data docs](https://rdrr.io/cran/tidyfinance/man/download_data_jkp.html) High |
| 2023 | Kelly & Xiu survey "Financial Machine Learning" | The best single map of the field | [SSRN](https://papers.ssrn.com/abstract=4501707) High |
| 2021–2022 | Momentum Transformer; follows Deep Momentum Networks (2019) | Deep learning for trend and reversal regimes | [arXiv 2112.08534](https://arxiv.org/abs/2112.08534) High |

**Conflict: does complexity help?** Kelly, Malamud and Zhou say yes, theoretically and empirically ([JF 2024](https://econpapers.repec.org/RePEc:bla:jfinan:v:79:y:2024:i:1:p:459-503)). Nagel shows their method builds the same momentum bet even on simulated data that reverses, where it then loses ([NBER 2025](https://www.nber.org/papers/w34104)). **I lean toward Nagel for your project**: it is newer, it directly tests the mechanism, and it implies a cheap check you can run (does your LightGBM beat a vol-scaled 12-1 momentum rule?). The debate is not settled; Nagel is a working paper, not yet peer reviewed. Medium.

## 5. Data and tools

Use Ken French industry portfolios as the primary research set and sector ETFs as the implementability check. Both are free and avoid the survivorship trap of stock lists.

**Datasets**

| Dataset | Use here | Size and coverage | Licence and access | Source and confidence |
| --- | --- | --- | --- | --- |
| Ken French Data Library: 5–49 industry portfolios, Mom and ST Rev factors, FF factors | Primary universe (49 industries) and benchmark factors | Daily and monthly; performance table runs to Sept 2026; long history (1926 start is Unverified from this page) | Free download; no terms shown on the page | [Data library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) High; terms Unverified |
| JKP Global Factor Data | Benchmark factor returns, robustness | 153 factors, 13 themes, daily or monthly, many countries | CC BY-NC 4.0 (non-commercial); public S3 | [tidyfinance docs](https://rdrr.io/cran/tidyfinance/man/download_data_jkp.html) High |
| Tiingo EOD | ETF and stock daily prices | 30+ years, 110k+ symbols; free tier 50 req/hour, 1,000/day, 500 symbols/month | Internal use only; $30/month individual plan | [Massive comparison page](https://massive.com/compare/massive-vs-tiingo.md) Medium (competitor's page) |
| Alpaca Market Data (Basic) | ETF daily bars, later paper trading | Since 2016; IEX feed only; 200 calls/min; latest 15 min excluded | Free; $99/month for full SIP | [Alpaca docs](https://docs.alpaca.markets/docs/about-market-data-api) High |
| Yahoo via yfinance | Quick prototyping only | Broad, but lacks delisted tickers | "Intended for personal use only"; yfinance is Apache-2.0 | [yfinance](https://pypi.org/project/yfinance/0.2.35/) High; [delisting gap](https://r-bloggers.com/2021/08/when-yahoo-finance-doesnt-have-de-listed-tickers-needed) Medium |
| Sharadar (via Nasdaq Data Link) | Optional stock-level extension | 20k+ US companies, includes delisted | Paid; price not listed on page | [QuantRocket page](https://quantrocket.com/pricing/data/sharadar) Medium |

**Libraries**

| Library | Role | Source and confidence |
| --- | --- | --- |
| pandas, NumPy | Engine core (write it yourself, vectorised) | Unverified (standard) |
| pandas-datareader `FamaFrenchReader` | Pull Ken French files | [Docs](https://pandas-datareader.readthedocs.io/en/latest/readers/famafrench.html) High |
| LightGBM 4.7 (`lambdarank`, `rank_xendcg`) | Cross-sectional ranking model | [Docs](https://lightgbm.readthedocs.io/en/stable/Parameters.html) High |
| scikit-learn `permutation_importance` | Held-out feature importance | [Docs](https://scikit-learn.org/stable/modules/permutation_importance.html) High |
| SHAP | Per-prediction attributions | [Lundberg & Lee 2017](https://papers.nips.cc/paper/7062-a) High |
| purgedcv | Cross-check your purged CV, DSR, PBO | [PyPI](https://pypi.org/project/purgedcv/) High |
| QuantStats (Apache-2.0, 5.6k stars) | Cross-check your metrics only | [Listing](https://awesome.ecosyste.ms/projects/github.com%2Franaroussi%2Fquantstats) High |
| Streamlit | Live app | [Community Cloud docs](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app) High |

**Compute.** 49 industries x about 1,200 months is roughly 60k rows monthly, or about 1.2M rows daily (my arithmetic, assuming a 1926 start). LightGBM on that fits on a laptop in minutes; CPCV with 15 splits multiplies that by 15. Unverified (estimate). For the app, Streamlit Community Cloud gives up to 2.7 GB RAM and 2 CPU cores, and sleeps after 12 hours without traffic ([docs](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app)). High. So precompute results offline and ship only small result files to the app.

## 6. Differentiation

Most student momentum projects run a moving-average crossover on today's S&P 500 list with yfinance and report one Sharpe ratio. Yours stands out by being the honest version. All points below are my judgement (Unverified) unless a source is linked.

1. **A small engine with tests that prove it cannot cheat.** A look-ahead unit test, a cost-model test and a reconciliation of your metrics against QuantStats. Libraries like zipline or backtesting.py hide this work ([section 2](https://awesome.ecosyste.ms/projects/github.com%2Fkernc%2Fbacktesting.py)).
2. **An overfitting ledger.** Log every configuration you try, then report the Deflated Sharpe Ratio and PBO for the whole search, not just the winner ([Bailey & López de Prado 2014](https://papers.ssrn.com/abstract=2460551), [Bailey et al. 2015](https://papers.ssrn.com/abstract=2326253)). Very few portfolio projects do this.
3. **A head-to-head that answers a real question.** Momentum vs short-term reversal vs a LightGBM ranker that sees both, on the same engine and costs. Then Nagel's test: does the ML model beat vol-scaled 12-1 momentum, or is it momentum in disguise ([Nagel 2025](https://www.nber.org/papers/w34104))?
4. **A feature study with a known answer.** Gu, Kelly and Xiu found momentum, liquidity and volatility dominate ([2020](https://nber.org/papers/w25398)). Check whether your held-out permutation importance and SHAP agree, with correlated features clustered first ([scikit-learn](https://scikit-learn.org/stable/modules/permutation_importance.html)).
5. **Crash analysis.** Show momentum's worst months, test whether market-state and volatility features predict them, and measure what vol scaling saves ([Daniel & Moskowitz 2016](https://www.nber.org/papers/w20439)).
6. **Survivorship-free by design.** Industry portfolios and ETFs avoid the delisting gap in Yahoo data, and the README says so.
7. **A cost curve, not one number.** Net Sharpe at 0, 5, 10, 25 and 50 bp, and the breakeven cost ([Novy-Marx & Velikov 2016](https://nber.org/papers/w20721)).
8. **A model card.** One page in the SR 26-2 spirit: purpose, data, limits, monitoring ([SR 26-2](https://www.federalreserve.gov/supervisionreg/srletters/sr2602.htm)).
9. **An interactive app** where a recruiter moves the cost slider and sees the edge shrink, with a "hypothetical backtest" label throughout.

## 7. Evaluation design

Judge every strategy on one engine, one cost model and one untouched final test period. Design choices are mine (Unverified) unless a source is linked.

**Metrics**

| Group | Metrics | Source and confidence |
| --- | --- | --- |
| Return and risk | Annualised return and volatility, Sharpe, Sortino, max drawdown, Calmar, skew, worst month | Unverified (standard) |
| Overfitting-aware | Probabilistic and Deflated Sharpe Ratio (with the number of trials), PBO via CSCV, t-stat vs 3.0 hurdle | [DSR](https://papers.ssrn.com/abstract=2460551), [PBO](https://papers.ssrn.com/abstract=2326253), [t > 3](https://www.nber.org/papers/w20592) High |
| Implementability | One-sided monthly turnover, net Sharpe at 0–50 bp, breakeven cost | [Novy-Marx & Velikov](https://nber.org/papers/w20721) High (turnover below 50% a month is the survivable zone) |
| Factor exposure | Alpha and betas vs Fama-French factors plus Mom and ST Rev | [Ken French library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) High |
| ML forecast quality | Rank IC (Spearman) per period and its t-stat, top-minus-bottom decile spread | Unverified (standard) |
| Feature importance stability | Rank correlation of importances across folds; permutation importance mean ± 2 std on held-out folds | [scikit-learn](https://scikit-learn.org/stable/modules/permutation_importance.html) High |

**Baselines** (every model must beat these net of costs)

1. Equal-weight all 49 industries, monthly rebalance.
2. Ken French Mom factor itself, as the published reference.
3. Plain 12-1 industry momentum, top vs bottom quintile ([Moskowitz & Grinblatt 1999](https://ideas.repec.org/a/bla/jfinan/v54y1999i4p1249-1290.html)).
4. Vol-scaled 12-1 momentum ([Barroso & Santa-Clara 2015](https://econpapers.repec.org/RePEc:eee:jfinec:v:116:y:2015:i:1:p:111-120)).
5. Short-term reversal (1-month losers minus winners) ([Lehmann 1990](https://www.nber.org/papers/w2533)).
6. Shuffled-label LightGBM, a null model whose Sharpe should be near zero.

**Validation method**

- **Split:** research period (e.g. 1927–2005) for all exploration; a locked final test (e.g. 2006–2026) opened once. Also report pre- and post-1993 to show publication decay ([McLean & Pontiff](https://academicnewsletter.sufe.edu.cn/info/359722)).
- **Inside the research period:** expanding-window walk-forward with yearly retraining, plus CPCV (e.g. 6 groups, 2 test groups, 15 paths) with purge equal to the label horizon and a 1% embargo ([López de Prado 2018, ch. 7 and 12](https://www.wiley-vch.de/de/fachgebiete/finanzen-wirtschaft-recht/advances-in-financial-machine-learning-978-1-119-48208-6)).
- **Timing rule:** features use data up to month-end t; trades fill at t+1; returns earned over t+1. Enforced by a unit test.
- **Second market:** re-run the frozen strategy on sector ETFs (2016+ from Alpaca, or longer from Tiingo) as an implementability check.

**What an honest result looks like**

- A modest positive net Sharpe for vol-scaled industry momentum that is visibly smaller than gross, smaller after 1993, and has a deep crash month. Unverified (expectation from the cited literature, not a computed number).
- The ML ranker matching or only slightly beating vol-scaled momentum, with a DSR that may fall below 95% once all trials are counted. That is a valid finding, not a failure ([Nagel 2025](https://www.nber.org/papers/w34104)). Medium.
- Short-term reversal looking good gross and dying at realistic costs ([Avramov et al. 2006](https://ideas.repec.org/a/bla/jfinan/v61y2006i5p2365-2394.html)). Medium (that paper is stock-level; industry-level may differ).
- Red flags: Sharpe above 2 on monthly data, no crash months, or a shuffled-label model that also makes money. Unverified (rule of thumb).

## 8. Pre-build research roadmap

About 9.5 hours, roughly the first week, before you write the execution plan. Do them in order; each step's exit criterion gates the next. Time estimates are mine (Unverified).

| # | Read, learn, test or verify | Time | Deliverable | Exit criterion |
| --- | --- | --- | --- | --- |
| 1 | Read the abstracts and main tables of [Jegadeesh & Titman](https://ideas.repec.org/a/bla/jfinan/v48y1993i1p65-91.html), [Moskowitz & Grinblatt](https://ideas.repec.org/a/bla/jfinan/v54y1999i4p1249-1290.html), [Daniel & Moskowitz](https://www.nber.org/papers/w20439) | 1.5 h | One-page notes: signal definitions (12-1, holding period, skip month), crash conditions | You can write the 12-1 industry momentum rule as pseudo-maths without looking |
| 2 | Verify data: download Ken French 49 industries (daily and monthly), Mom and ST Rev factors via [pandas-datareader](https://pandas-datareader.readthedocs.io/en/latest/readers/famafrench.html); check the library's terms | 1 h | Notebook with row counts, start and end dates, missing-value codes (e.g. -99.99) | Data loads, start date confirmed, and you know the terms of use |
| 3 | Sanity-check: compute plain 12-1 industry momentum by hand and correlate its monthly returns with the published Mom factor | 1.5 h | Correlation number and a cumulative-return chart | Positive, clearly non-zero correlation; if not, your signal timing is wrong |
| 4 | Verify ETF data path: pull 11 sector ETFs from [Alpaca](https://docs.alpaca.markets/docs/about-market-data-api) or [Tiingo](https://massive.com/compare/massive-vs-tiingo.md); read their terms | 0.5 h | Script plus terms note | Daily adjusted closes since at least 2016, and you know what you may publish |
| 5 | Learn purged CV and CPCV: [López de Prado ch. 7 and 12](https://www.wiley-vch.de/de/fachgebiete/finanzen-wirtschaft-recht/advances-in-financial-machine-learning-978-1-119-48208-6); run [purgedcv](https://pypi.org/project/purgedcv/) on toy data | 1.5 h | Diagram of your split scheme with purge and embargo sizes | You can explain why a 1-month label needs a 1-month purge |
| 6 | Learn DSR and PBO: read [Bailey & López de Prado](https://papers.ssrn.com/abstract=2460551) and [Bailey et al.](https://papers.ssrn.com/abstract=2326253) | 1 h | Formula sheet and a list of what to log per trial | You can compute PSR for a toy return series and match purgedcv's value |
| 7 | Learn importance pitfalls: [scikit-learn permutation importance](https://scikit-learn.org/stable/modules/permutation_importance.html) and the [SHAP paper](https://papers.nips.cc/paper/7062-a) | 1 h | Feature list (about 10–15 features) grouped into correlated clusters | Every feature has a definition, a lookback and a cluster label |
| 8 | Read the critique: [Nagel 2025](https://www.nber.org/papers/w34104) and [Novy-Marx & Velikov](https://nber.org/papers/w20721) | 1 h | List of falsification tests (shuffled labels, simulated-reversal data, cost sweep) | Each test has a pass or fail rule written down |
| 9 | Decide and freeze: universe, rebalance frequency, cost model, research and test periods, trial budget | 0.5 h | One-page pre-registration file committed to the repo | Signed off by you; no test-period data touched yet |

**Gate to Phase 2:** steps 2, 3 and 9 must pass. If step 3 fails, fix timing before anything else.

## 9. Delivery requirements

Ship a public GitHub repo, a Streamlit app on Community Cloud, a one-page model card and three quantified CV bullets.

**Deployment options**

| Option | Free resources | Catch | Fit | Source and confidence |
| --- | --- | --- | --- | --- |
| Streamlit Community Cloud | Up to 2 CPU cores, 2.7 GB RAM, 50 GB storage | Sleeps after 12 h idle; limits can change | **Recommended**: native to Streamlit, deploys from GitHub | [Docs](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app) High |
| Hugging Face Spaces | 2 vCPU, 16 GB RAM, 50 GB non-persistent disk | New Gradio and Docker Spaces need a paid plan; static Spaces are free; sleeps when idle | Backup, or a static results page | [Docs](https://huggingface.co/docs/hub/spaces-overview) High |
| Static site (GitHub Pages) of precomputed charts | Unverified | No interactivity | Fallback if the app sleeps during interviews | Unverified |

**Repo structure** (proposal, Unverified)

```text
momentum-lab/
  README.md            # results first, then how to run
  MODEL_CARD.md        # purpose, data, limits, monitoring
  PREREGISTRATION.md   # frozen choices from roadmap step 9
  pyproject.toml       # pinned deps; Makefile or justfile
  src/momlab/
    data/              # loaders, caching, calendar alignment
    features/          # momentum, reversal, vol, market state
    engine/            # portfolio, execution, costs, accounting
    validation/        # walk-forward, purged CV, CPCV, DSR, PBO
    models/            # baselines, LightGBM ranker
    importance/        # permutation, SHAP, clustering
  tests/               # look-ahead test, cost test, metric parity vs QuantStats
  experiments/         # trial ledger (CSV) and configs
  app/streamlit_app.py # reads precomputed results only
  reports/             # figures and final tables
  .github/workflows/   # CI: lint, tests
```

**README contents** (Unverified, my recommendation)

1. One-sentence result with the headline net numbers and a "hypothetical backtest" label.
2. Live app link and one equity-curve plus cost-curve image.
3. Question and hypotheses (momentum vs reversal vs ML).
4. Data: sources, licences, why survivorship-free.
5. Method: engine timing rule, costs, validation scheme.
6. Results table: all baselines, gross and net, DSR, PBO, number of trials.
7. Feature importance findings and how stable they are.
8. Limits and what would break it; link to MODEL\_CARD.md.
9. Reproduce: `make data && make test && make results`.

**CV-bullet format.** Use Laszlo Bock's "Accomplished \[X\] as measured by \[Y\] by doing \[Z\]" ([Business Insider](https://www.businessinsider.in/googles-former-hr-boss-says-this-is-the-key-to-a-perfect-resume/articleshow/54925993.cms)). Medium (press summary of his 2014 post). Templates to fill after Phase 2, with real numbers only:

- Built a vectorised backtest engine in Python (about \[N\] lines, \[M\] tests including a look-ahead guard) and validated metrics to within \[x\]% of QuantStats.
- Showed industry momentum earned a \[a\] net Sharpe at \[c\] bp costs over \[period\] vs \[b\] for short-term reversal, with Deflated Sharpe \[d\] across \[T\] logged trials.
- Ran a purged-CV feature importance study on \[F\] features; found \[feature group\] drove \[p\]% of held-out permutation importance, stable across \[k\] folds.
- Deployed an interactive Streamlit app with a live cost slider and crash analysis.

## 10. Risks and open questions

**Risks**

| Risk | Likelihood | Impact | Mitigation | Source and confidence |
| --- | --- | --- | --- | --- |
| 40 hours is too little for engine, ML study and app | High | Unfinished product | Cut stock-level and LLM work; precompute results; app last | Unverified |
| Industry momentum is weak in the recent test period | Medium | Dull headline | Report it honestly; post-publication decay is expected | [McLean & Pontiff](https://academicnewsletter.sufe.edu.cn/info/359722) High |
| ML adds nothing over vol-scaled momentum | Medium | Feature study looks empty | Frame as a test of Nagel's critique; a null result is a finding | [Nagel 2025](https://www.nber.org/papers/w34104) Medium |
| Hidden look-ahead in your engine | Medium | Results invalid | Shift-test in CI; reconcile with published Mom factor | Unverified |
| Data licence breach (redistributing Yahoo or vendor data) | Medium | Takedown, credibility | Keep raw data out of the repo; ship derived results | [yfinance](https://pypi.org/project/yfinance/0.2.35/), [Tiingo terms via comparison](https://massive.com/compare/massive-vs-tiingo.md) Medium |
| App sleeps or hits memory limits during a recruiter visit | Medium | Bad first impression | Small precomputed files; README screenshots; static fallback | [Streamlit docs](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app) High |
| Results read as investment advice or a performance claim | Low | Reputational | "Hypothetical backtest, not advice" on every page | [K&L Gates on SEC rule](https://www.klgates.com/thought-leadership/Hypothetical-Performance-Crackdown-Nine-Firms-Charged-With-Violations-of-Investment-Adviser-Marketing-and-Recordkeeping-Rules-9-13-2023) Medium |

**Open questions** (answer during the roadmap)

- [ ] What are the Ken French Data Library's terms of use for republishing derived results? (Not shown on the page I opened.)
- [ ] Monthly or weekly rebalance? Monthly fits the momentum literature; weekly is needed to give reversal a fair test.
- [ ] How to cost trades on industry portfolios that are not directly tradable? Proposal: use sector ETF spreads as the proxy and sweep 0–50 bp.
- [ ] Long-short or long-only? Long-short matches the papers; long-only matches what most readers could do.
- [ ] Label: next-month raw return rank, or excess over the cross-sectional mean?
- [ ] How many trials will you allow yourself? Fix the number before you start (it feeds DSR).
- [ ] Is a stock-level extension with paid survivorship-free data worth it later? ([Sharadar](https://quantrocket.com/pricing/data/sharadar))
- [ ] Does the 2006 test split leave enough crash months (2008–2009, 2020) to judge crash features?

## 11. Recommended skills, libraries and Claude tools

**Technical skills**

| Skill | Why | Where to learn | Confidence |
| --- | --- | --- | --- |
| Vectorised pandas on panel data (date x asset), shifting and alignment | Engine correctness and speed | Unverified (standard) | Unverified |
| Time-series CV: walk-forward, purging, embargo, CPCV | Leak-free model evaluation | [López de Prado ch. 7, 12](https://www.wiley-vch.de/de/fachgebiete/finanzen-wirtschaft-recht/advances-in-financial-machine-learning-978-1-119-48208-6), [purgedcv](https://pypi.org/project/purgedcv/) | High |
| Learning-to-rank with gradient boosting | Cross-sectional ranking target | [LightGBM params](https://lightgbm.readthedocs.io/en/stable/Parameters.html) | High |
| Model interpretation: permutation importance, SHAP, clustering correlated features | The feature study | [scikit-learn](https://scikit-learn.org/stable/modules/permutation_importance.html), [Lundberg & Lee](https://papers.nips.cc/paper/7062-a) | High |
| Testing (pytest), CI, packaging | Repo looks professional | Unverified | Unverified |
| Streamlit caching (`st.cache_data`) | Keep the app inside memory limits | [Streamlit](https://docs.streamlit.io/knowledge-base/deploy/resource-limits) | High |

**Domain skills**

| Skill | Why | Source | Confidence |
| --- | --- | --- | --- |
| Momentum construction (12-1, skip month, industry vs stock) | Correct signal | [Jegadeesh & Titman](https://ideas.repec.org/a/bla/jfinan/v48y1993i1p65-91.html), [Moskowitz & Grinblatt](https://ideas.repec.org/a/bla/jfinan/v54y1999i4p1249-1290.html) | High |
| Volatility scaling and crash risk | Main enhancement | [Barroso & Santa-Clara](https://econpapers.repec.org/RePEc:eee:jfinec:v:116:y:2015:i:1:p:111-120), [Daniel & Moskowitz](https://www.nber.org/papers/w20439) | High |
| Transaction costs and turnover | Net vs gross | [Novy-Marx & Velikov](https://nber.org/papers/w20721) | High |
| Factor regression (alpha vs FF + Mom) | Show what is new vs known | [Ken French library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) | High |
| Multiple testing and backtest statistics | Credibility | [Harvey et al.](https://www.nber.org/papers/w20592), [DSR](https://papers.ssrn.com/abstract=2460551) | High |
| Model risk governance | Model card | [SR 26-2](https://www.federalreserve.gov/supervisionreg/srletters/sr2602.htm) | High |

**Libraries** are listed in section 5. Keep the engine to pandas and NumPy; use QuantStats and purgedcv only to cross-check your own numbers.

**Claude skills, plugins and connectors** (what this project has access to today, as seen in this session; not web-sourced)

| Tool | Use it for |
| --- | --- |
| Consensus connector | Searching peer-reviewed papers during roadmap steps 1, 5–8 |
| `academic-research-skills:deep-research` (lit-review mode) | A structured literature review if you want one for the README |
| `data:statistical-analysis` and `data:validate-data` | Checking significance tests and QA of results before publishing |
| `dataviz` and `data:create-viz` | Consistent, accessible charts for README and app |
| `code-review`, `simplify` and `security-review` | Reviewing engine PRs for bugs, clean-ups and secrets |
| GitHub (attach your repo to a session) | PRs, CI fixes and review comments. The GitHub connector failed to connect in this session (proxy 403), so it may need a retry |
| Claude Docs | This document and the Phase 2 plan |
| Artifacts | An interactive results explainer next to the Streamlit app, if useful |

## 12. Handoff summary for Phase 2

Copy the block below into the Phase 2 prompt.

```text
PROJECT: momentum-lab. Self-written backtest engine + industry momentum vs
short-term reversal vs LightGBM ranker + overfitting-aware feature importance study.
Deployed as a Streamlit app. Portfolio piece for quant / DS roles.

CONSTRAINTS: intermediate Python/ML; 4 weeks x 10 h = 40 h (about 9.5 h of
roadmap already planned in week 1); free data; laptop compute; Streamlit
Community Cloud (2.7 GB RAM max, sleeps after 12 h idle).

DECISION: momentum is the main strategy. Short-term reversal is a baseline
and a feature. Reason: stronger, broader evidence; reversal profits mostly
below trading costs; free EOD data suffices.

DATA: Ken French 49 industry portfolios (daily + monthly), Mom, ST Rev, FF
factors via pandas-datareader = primary, survivorship-free. Sector ETFs via
Alpaca (free, since 2016) or Tiingo = implementability check. No raw vendor
data in the repo. yfinance for prototyping only (personal-use terms).

SIGNALS / FEATURES (about 10-15, clustered): returns over 1, 3, 6, 12-1
months; 1-month reversal; realised vol (1, 3 m); trend strength; market
state (past market return, market vol); industry dispersion.
LABEL: next-month cross-sectional return rank.

ENGINE: pandas/NumPy, vectorised, signals at t -> fills at t+1;
costs = spread + commission, sweep 0/5/10/25/50 bp; turnover tracked;
long-short quintiles + long-only variant; vol scaling option.
Tests: look-ahead shift test, cost test, metric parity vs QuantStats,
correlation of own 12-1 vs published Mom factor.

VALIDATION: research period about 1927-2005, locked test 2006-2026 opened once;
expanding walk-forward (yearly retrain) + CPCV (6 groups, 2 test, purge =
label horizon, 1% embargo); trial ledger; report DSR, PBO, t > 3 hurdle;
pre/post-1993 split; shuffled-label null model.

BASELINES: equal-weight; published Mom factor; plain 12-1; vol-scaled 12-1;
ST reversal; shuffled-label LightGBM.

FEATURE STUDY: permutation importance on held-out folds (mean +/- 2 std),
SHAP on test folds, correlated-feature clusters, stability across folds;
compare with Gu-Kelly-Xiu finding (momentum, liquidity, volatility dominate);
Nagel test: does ML beat vol-scaled momentum?

DELIVERABLES: repo (src/engine, validation, models, importance, tests,
app, experiments ledger), README (results first), MODEL_CARD.md (SR 26-2
spirit), PREREGISTRATION.md, Streamlit app with cost slider and crash view,
3-4 CV bullets in X-Y-Z format with real numbers only. All results labelled
"hypothetical backtest".

OPEN: Ken French terms for derived results; monthly vs weekly rebalance;
cost proxy for industry portfolios; long-short vs long-only headline;
trial budget number.
```

## Sources

Every page below was opened on 6 Nov 2026. Search-result snippets were not used as sources.

**Papers: momentum and mean-reversion**

1. [Jegadeesh & Titman (1993), Returns to Buying Winners and Selling Losers, J. Finance](https://ideas.repec.org/a/bla/jfinan/v48y1993i1p65-91.html)
2. [Moskowitz, Ooi & Pedersen (2012), Time Series Momentum, SSRN](https://papers.ssrn.com/abstract=2089463)
3. [Moskowitz & Grinblatt (1999), Do Industries Explain Momentum?, J. Finance](https://ideas.repec.org/a/bla/jfinan/v54y1999i4p1249-1290.html)
4. [Asness, Moskowitz & Pedersen (2013), Value and Momentum Everywhere, AQR](https://www.aqr.com/library/journal-articles/value-and-momentum-everywhere)
5. [Hurst, Ooi & Pedersen (2017), A Century of Evidence on Trend-Following Investing, AQR](https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing)
6. [Daniel & Moskowitz (2014/2016), Momentum Crashes, NBER w20439](https://www.nber.org/papers/w20439)
7. [Barroso & Santa-Clara (2015), Momentum Has Its Moments, JFE](https://econpapers.repec.org/RePEc:eee:jfinec:v:116:y:2015:i:1:p:111-120)
8. [Lehmann (1988/1990), Fads, Martingales, and Market Efficiency, NBER w2533](https://www.nber.org/papers/w2533)
9. [Alpha Architect (2015), short-term reversal summary](https://alphaarchitect.com/quantitative-momentum-research-short-term-return-reversal/)
10. [Avramov, Chordia & Goyal (2006), Liquidity and Autocorrelations in Individual Stock Returns, J. Finance](https://ideas.repec.org/a/bla/jfinan/v61y2006i5p2365-2394.html)
11. [Gatev, Goetzmann & Rouwenhorst (2006), Pairs Trading, RFS](https://econpapers.repec.org/RePEc:oup:rfinst:v:19:y:2006:i:3:p:797-827)
12. [Avellaneda & Lee (2010), Statistical Arbitrage in the US Equities Market, Quant. Finance](https://ideas.repec.org/a/taf/quantf/v10y2010i7p761-782.html)

**Papers: ML, overfitting, replication**

13. [Gu, Kelly & Xiu (2020), Empirical Asset Pricing via Machine Learning, NBER w25398](https://nber.org/papers/w25398)
14. [Lim, Zohren & Roberts (2019), Deep Momentum Networks, arXiv 1904.04912](https://arxiv.org/abs/1904.04912)
15. [Wood et al. (2021), Momentum Transformer, arXiv 2112.08534](https://arxiv.org/abs/2112.08534)
16. [Kelly, Malamud & Zhou (2024), The Virtue of Complexity in Return Prediction, J. Finance](https://econpapers.repec.org/RePEc:bla:jfinan:v:79:y:2024:i:1:p:459-503)
17. [Nagel (2025), Seemingly Virtuous Complexity in Return Prediction, NBER w34104](https://www.nber.org/papers/w34104)
18. [Kelly & Xiu (2023), Financial Machine Learning, SSRN](https://papers.ssrn.com/abstract=4501707)
19. [Bailey & López de Prado (2014), The Deflated Sharpe Ratio, SSRN](https://papers.ssrn.com/abstract=2460551)
20. [Bailey, Borwein, López de Prado & Zhu (2015), The Probability of Backtest Overfitting, SSRN](https://papers.ssrn.com/abstract=2326253)
21. [Harvey, Liu & Zhu (2014/2016), ...and the Cross-Section of Expected Returns, NBER w20592](https://www.nber.org/papers/w20592)
22. [McLean & Pontiff (2016), Does Academic Research Destroy Stock Return Predictability?](https://academicnewsletter.sufe.edu.cn/info/359722)
23. [Jensen, Kelly & Pedersen (2021/2023), Is There a Replication Crisis in Finance?, NBER w28432](https://www.nber.org/papers/w28432)
24. [Novy-Marx & Velikov (2014/2016), A Taxonomy of Anomalies and Their Trading Costs, NBER w20721](https://nber.org/papers/w20721)
25. [Brown et al. (1992), Survivorship Bias in Performance Studies, RFS](https://ideas.repec.org/a/oup/rfinst/v5y1992i4p553-80.html)
26. [Lundberg & Lee (2017), A Unified Approach to Interpreting Model Predictions (SHAP), NeurIPS](https://papers.nips.cc/paper/7062-a)
27. [Lopez-Lira & Tang, Can ChatGPT Forecast Stock Price Movements?, arXiv 2304.07619v6](https://arxiv.org/html/2304.07619v6)
28. [Lopez-Lira, Tang & Zhu (2025), The Memorization Problem, arXiv 2504.14765v2](https://arxiv.org/html/2504.14765v2)
29. [Gao, Jiang & Yan (2025), A Test of Lookahead Bias in LLM Forecasts, arXiv 2512.23847](https://arxiv.org/html/2512.23847v1)
30. [Ansari et al. (2024), Chronos: Learning the Language of Time Series, arXiv 2403.07815](https://arxiv.org/pdf/2403.07815)
31. [López de Prado (2018), Advances in Financial Machine Learning, Wiley (table of contents)](https://www.wiley-vch.de/de/fachgebiete/finanzen-wirtschaft-recht/advances-in-financial-machine-learning-978-1-119-48208-6)
32. [Purged cross-validation overview, Wikipedia (low confidence)](https://en.wikipedia.org/wiki/Purged_cross-validation)

**Regulators and legal**

33. [Federal Reserve SR 26-2 (Apr 2026), Revised Guidance on Model Risk Management](https://www.federalreserve.gov/supervisionreg/srletters/sr2602.htm)
34. [Federal Reserve SR 11-7 (2011), Guidance on Model Risk Management](https://www.federalreserve.gov/supervisionreg/srletters/sr1107.htm)
35. [K&L Gates (2023), SEC hypothetical performance enforcement summary](https://www.klgates.com/thought-leadership/Hypothetical-Performance-Crackdown-Nine-Firms-Charged-With-Violations-of-Investment-Adviser-Marketing-and-Recordkeeping-Rules-9-13-2023)

**Data**

36. [Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html)
37. [JKP Global Factor Data via tidyfinance docs](https://rdrr.io/cran/tidyfinance/man/download_data_jkp.html)
38. [Alpaca Market Data API docs](https://docs.alpaca.markets/docs/about-market-data-api)
39. [Massive vs Tiingo comparison (vendor page)](https://massive.com/compare/massive-vs-tiingo.md)
40. [yfinance 0.2.35 on PyPI](https://pypi.org/project/yfinance/0.2.35/)
41. [R-bloggers (2021), Yahoo Finance lacks delisted tickers](https://r-bloggers.com/2021/08/when-yahoo-finance-doesnt-have-de-listed-tickers-needed)
42. [QuantRocket Sharadar data page](https://quantrocket.com/pricing/data/sharadar)

**Software and platforms**

43. [Microsoft Qlib README](https://github.com/microsoft/qlib/blob/main/README.md)
44. [zipline-reloaded listing](https://awesome.ecosyste.ms/projects/github.com%2Fstefan-jansen%2Fzipline-reloaded)
45. [backtesting.py listing](https://awesome.ecosyste.ms/projects/github.com%2Fkernc%2Fbacktesting.py)
46. [QuantStats listing](https://awesome.ecosyste.ms/projects/github.com%2Franaroussi%2Fquantstats)
47. [purgedcv on PyPI](https://pypi.org/project/purgedcv/)
48. [scikit-learn permutation importance docs](https://scikit-learn.org/stable/modules/permutation_importance.html)
49. [LightGBM parameters docs](https://lightgbm.readthedocs.io/en/stable/Parameters.html)
50. [pandas-datareader Fama-French reader docs](https://pandas-datareader.readthedocs.io/en/latest/readers/famafrench.html)
51. [Streamlit Community Cloud: manage your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app)
52. [Streamlit resource limits](https://docs.streamlit.io/knowledge-base/deploy/resource-limits)
53. [Hugging Face Spaces overview](https://huggingface.co/docs/hub/spaces-overview)

**Competitions and careers**

54. [Jane Street Real-Time Market Data Forecasting (Kaggle page clipping)](https://anilkeshwani.github.io/garden/Clippings/Jane-Street-Real-Time-Market-Data-Forecasting--Kaggle)
55. [fintorch tutorial on the Jane Street data](https://fintorch.readthedocs.io/en/stable/tutorials/marketdata/marketdata.html)
56. [Business Insider, Laszlo Bock's resume formula](https://www.businessinsider.in/googles-former-hr-boss-says-this-is-the-key-to-a-perfect-resume/articleshow/54925993.cms)

**Not verified:** GitHub star counts and licences come from ecosyste.ms listings, because direct GitHub API access was blocked in this session. Ken French terms of use and the 1926 start date were not shown on the page opened.
