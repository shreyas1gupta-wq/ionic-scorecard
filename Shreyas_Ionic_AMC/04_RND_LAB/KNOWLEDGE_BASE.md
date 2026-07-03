# KNOWLEDGE BASE — what the firm knows (methods, lessons, references)
R&D Head curates; quarterly pruning. Backtests+logic live with their ideas; THIS file holds transferable knowledge.

## A. Firm-earned lessons (paid for with real mistakes — never re-learn)
1. **VRP is the meta-edge in Indian options:** implied > realized persistently → selling wins, buying loses. Every profitable option sleeve we have is short-vol; every buying family died (K-001, K-004).
2. **Measurement artifacts we have personally produced** (Red Team trophy wall): return-on-net-debit denominator (FF "+80%"); spreading trade P&L across holding days (Sharpe 7-10, Kelly 300); monthly-compounded sleeve CAGRs (+246%/+681% "annualized" fantasies); near-expiry return-on-premium explosions (+357% earnings "wins"); partial-year data reading as "positive every year". Antidotes: exit-period booking, stable denominators (premium/spot), per-trade edge as the headline metric, periods-per-year coverage checks.
3. **Lookahead in stock selection:** any filter built from realized outcomes (the "16 landmines") is untradeable. Live filters must be ex-ante: IV at entry (corr −0.23 with future worst-case), liquidity/OI, event calendar, walk-forward-proven history rules only for stocks that HAVE history.
4. **Tails are unforecastable at trade level; survivable at portfolio level.** DMA/vol/downside filters, stops (gap through), and bought wings (theta bleed + unpriceable strikes) all FAILED to cap the FF tail. What works: small size × many concurrent idiosyncratic positions, inverse-IV sizing, staggered entries (April-2026 one-day cluster = correlated blowup), event gates.
5. **Cap-tier gating is strategy-specific:** premium harvesting (IV/RV, strangle) IMPROVES on mid-caps (richer IV) with sizing discipline; structure/liquidity-sensitive strategies (calendars) and binary-event strategies (earnings) degrade — large-cap only.
6. **Event gates are the cheapest tail insurance:** IT earnings gap −31..−47% through a short straddle; banks cluster on one Saturday; defence order flow and FDA letters are un-calendarable → sector analysts own the calendars, desk trades AROUND them.
7. **Data coverage is alpha:** expanding 88→210 F&O names (free NSE bhavcopy) roughly doubled every strategy's sample and surfaced fresh tradeables. Check coverage before inventing signals.
8. **Angel purges expired option contracts** — capture before expiry (15:45 task) or lose the data forever. NSE archives (nsearchives) DO work through the corporate proxy; only some /api endpoints are blocked.

## B. Reference library (from Principal's mandate — study before reinventing)
**Books:** Lopez de Prado *Advances in Financial ML* + *ML for Asset Managers* · Grinold & Kahn *Active Portfolio Management* · Ilmanen *Expected Returns* · Gray & Vogel *Quantitative Momentum* · E. Chan *Algorithmic Trading* · Minervini ×2 · Weinstein *Stage Analysis* · O'Neil *CANSLIM*.
**Papers:** Jegadeesh-Titman 1993 · Fama-French 2015 · Novy-Marx profitability · Piotroski F-score · Sloan accruals · Bernard-Thomas PEAD · Frazzini-Pedersen BAB · Asness QMJ · Harvey-Liu-Zhu (demand t>3) · Bailey-López de Prado (DSR, PBO) · McLean-Pontiff (post-publication decay) · Raju SSRN (India factors).
**Repos:** microsoft/qlib · vectorbt · stefan-jansen/ml4t + zipline-reloaded · alphalens/pyfolio-reloaded · quantstats · Riskfolio-Lib · skfolio · pandas-ta · mlfinlab · OpenBB · jugaad-data (NSE; office-proxy-blocked) · **wilsonfreitas/awesome-quant** (index).
**HF models:** ProsusAI/finbert (tone) · FinGPT (reference only). **GPU escape hatch:** Kaggle 2×T4 ~30h/wk (D-011).
**Agent craft:** docs.claude.com sub-agents + prompt-engineering · anthropic.com/engineering (building-effective-agents, claude-code-best-practices) · github.com/anthropics/skills.
**India method:** NSE index methodology PDFs · SEBI circulars · AMFI · screener.in · trendlyne (candidate estimates feed — D-009 gate).

## C. Strategy families — current standing (detail in STRATEGY_REGISTER)
Short-vol option sleeves (IV/RV, earnings-crush, FF-calendar-CE, managed strangle): VALIDATED forward on 210 universe, gating rules apply. Equity momentum+lowvol: positive, below high bar, diversifier value. Track-1 index short-straddle w/ 0.45% filter: deploy-ready per pre-firm work. Momentum machine (Track-2) & dealer-gamma (Track-3): data-ready, build pending.
