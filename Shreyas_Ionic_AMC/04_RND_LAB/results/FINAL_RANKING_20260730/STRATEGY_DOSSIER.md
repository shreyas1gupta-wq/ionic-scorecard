# TOP 5 STRATEGIES — DOSSIER + CORRELATION RECHECK
**Built 2026-07-30, DESK-100. Every number rebuilt from the real per-trade CSV on disk by
`build_ranking.py` — nothing re-typed from prose.** Scope: NIFTY 50 only, futures + options.
Costs Rs25/lot/side + slippage; futures margin 10% unhedged / 5% same-expiry hedged;
futures P&L via spot proxy + 0.5%/month carry (longs pay, shorts receive).

---
## ⚠ READ THIS BEFORE COMPARING CAGRs
**CAGR is NOT comparable across these five.** They have wildly different capital utilisation at
1 lot on Rs10L: SWEEP trades ~32x/month (1,578 active days), the CALENDAR trades ~1x/month
(178 trades in 15.5yr), SWING ~1x/month (54 active days). A strategy that sits in cash 95% of the
time shows a tiny CAGR while having an excellent per-trade edge.
**Compare on Sharpe / PF / NW_t / Calmar. Use CAGR only within the same utilisation class.**
Sizing to equalise risk is a separate, unresolved exercise (see §OPEN).
**Also excluded from this ranking:** the `BOOK_*` rows in `metrics_all.csv` — my script applied a
Rs10L capital base to the Rs1cr stacked book, so their CAGR/maxDD are scale artifacts (BOOK_total
shows an impossible -146% maxDD). Correlations are unaffected (computed on P&L, not returns).

---
## THE RANKING

### #1 — SWEEP_E : liquidity-sweep / stop-hunt reversal, 3-day swing hold
**THE SESSION'S FLAGSHIP. Only candidate clearing the multiple-testing bar.**

| | |
|---|---|
| **Logic** | On 15-min bars, price sweeps the **PRIOR DAY's** swing high/low — running the stop-losses clustered at that obvious level — and then **RECLAIMS** the level (closes back inside). Trade the reversal, direction = back into the range. This IS the "stop-hunting / manipulation" mechanism: liquidity is hunted at the obvious level, then price reverts. The CONTINUATION variant does NOT work; only the RECLAIM does. |
| **Entry** | Next 1-min bar OPEN after the 15-min signal bar closes (never same-bar). Window 09:20-14:30. |
| **Exit** | Trailing stop 60 pts from peak; hard stop 60; max 3 sessions then flat 15:25. **Mean actual hold 5.25 sessions** (trail keeps winners alive). |
| **Instrument** | Delta-1 NIFTY futures (spot proxy + carry). 10% margin. |
| **Span / n** | **2015-01..2026-05, 11.33 yrs, 4,378 trades (~32/mo)** |
| CAGR | **15.33%** |
| maxDD | **-18.02%** |
| Calmar / Sharpe | 0.85 / **1.84** |
| **NW t** | **4.35** |
| PF | 1.45 |
| Months positive | **65.7%** (90/137) |
| Max single day | 4.2% of total profit (healthy, not fragile) |
| Trade shape | mean 16.0 pts, **p95 202.5 pts, max win 606.7**, worst -60.5. **Win rate only 47.6%** — earns on payoff asymmetry, not hit rate. |
| **Why it matters most** | **54.5% SHORT / 45.5% long = near-market-neutral.** It made money 2015-2026 while NIFTY rose a lot, so it CANNOT be disguised beta. And COVID was its BEST stretch (+30.2% over 2020-02-28..03-26, +37.2% Feb15-Apr15). |
| Evidence quality | Holds on the **pristine never-searched 2015-2021 segment** (PF 1.37, t=3.04) which contains COVID. t=4.35 clears Bonferroni at m=133 (3.55) AND at the firm's cumulative ~382 trials (3.82). |
| **Concerns** | **2025 was the worst year in the whole 11-yr sample** (H2-2025 lost 6 of 7 months) — possible live decay. Spot-as-futures proxy (no basis/roll modelling). **2015-2020 segment has never passed D-009 verification** and it carries the strongest OOS claim. DSR/PBO still owed. |

### #2 — SWEEP_D : same signal, overnight hold — **the low-drawdown variant**
Identical entry logic to #1; exit = trailing 40 pts, max 1 extra session.
CAGR **10.83%** | maxDD **-11.39%** (best of any candidate) | **Calmar 0.95** (best) | Sharpe 1.45 |
NW t 3.58 | PF 1.34 | months positive 64.2% | max day 7.3% of profit | 4,378 trades.
**⚠ MUTUALLY EXCLUSIVE WITH #1 — correlation 0.82 monthly / 0.84 quarterly (same entry signal).
Size ONE, never both.** Choose D if the binding constraint is drawdown; E if it is return.

### #3 — CALENDAR_1x1_3d : ATM/ATM calendar, exit 3 days before near expiry
| | |
|---|---|
| **Logic** | Sell near-month ATM CE, buy next-month ATM CE, 1x1 (defined risk). Short near-month vol (fast theta) + long far-month vol (slow theta, long vega). It is a **volatility TERM-STRUCTURE trade**, not a price bet. |
| **★ The load-bearing rule** | **EXIT 3 DAYS BEFORE near expiry.** Holding to expiry yields **+0.10 pts (t=0.02, friction 97.5% of gross) = literally nothing.** Exiting 3 days early yields **+9.58 pts NET (t=2.49, PF 1.65)**. The final days' gamma gives back the entire edge. This single rule is worth ~9.5 pts/trade. |
| **Span / n** | **2011-01..2026-07, 15.46 yrs, 178 trades** (longest history of any candidate) |
| CAGR (see caveat) | 0.75% — *artefact of 1 lot idle most of the month*, not a weak edge |
| maxDD | **-1.91%** |
| Calmar / Sharpe | 0.39 / **2.85** (highest Sharpe of the five) |
| NW t | 2.25 |
| PF | **1.60** |
| Months positive | 57.2% |
| Risk | **Max loss BOUNDED at the net debit.** Worst trade -191 pts. |
| **Rejected variants** | ATM ratio 2x1 (-10.9 pts) and 3x2 (-1.3 pts) are **outright losers** with -943 to -1,380 pt tails — selling ATM in ratio leaves you lethally short gamma at the strike. OTM25D 3x2 makes +45 pts but with -795 pt tails and **UNBOUNDED** risk; extra return ≈ proportional to extra tail, so no risk-adjusted gain. **Only the 1x1 is defined-risk.** |
| **Term-structure filter DOES NOT HELP** | Inversion genuinely predicts near-IV falling (-3.67 to -5.44 vol pts = 79-117 CE pts of vega tailwind) BUT co-occurs with much larger underlying moves (3.99% vs 2.31%) that punish short gamma. The two effects cancel: every best cell is `unconditional`. |
| **★★ REGIME SPLIT — DOWNGRADES THIS CANDIDATE (found 2026-07-30 on a Principal challenge)** | The Principal asked how there could be options data before 2019 when weeklies launched Feb-2019. **Data check PASSED** — the backtest used MONTHLY pairs throughout (0 of 178 trades have a weekly gap; gap median 28d, range 26-36; near_dte ~31 / far_dte ~62; 10-13 trades/yr = 12 monthly cycles; monthly NIFTY options exist since 2001). **But the check exposed that the ENTIRE EDGE IS POST-2019:** pre-2019 (2011-2018) n=93, mean **+0.88 pts/trade ≈ zero**; 2019-2026 n=85, mean **+18.32 pts**. Yearly pre-2019: -9.6, -4.7, -1.1, +3.6, +13.6, -0.6, +5.1, +2.0. **CONSEQUENCE: the effective sample is 85 trades over ~7 years, NOT 178 over 15.46 years — the long span DILUTES rather than supports the claim, and an earlier framing of "longest history of any candidate = a strength" was WRONG.** t=2.25 is weaker than it appears because the pre-2019 half contributes noise, not confirmation. **[INFERENCE, fitted after seeing the split, needs independent testing]:** weekly options launched Feb-2019 and transformed NIFTY's front end (India became the largest options market by contract count, heavy retail weekly demand) — front-month vol may be structurally richer vs next-month since then, which is exactly what a calendar monetises. Note this is a SECOND structural break to add to the Oct-2024 SEBI change already under investigation; any backtest spanning 2019 is mixing two different markets. |
| **Concerns** | **t=2.25 does NOT clear the ~140-cell Bonferroni bar (~3.4)** — suggestive, not established, and now weaker still given the regime split above. Held-out 2026H1 has **n=1** and is useless for validation. Cross-expiry margin is ambiguous (between 5% and 10%; broker SPAN-dependent). |
| K-012 differentiation | The firm's killed FF calendar was single-STOCK, single-CE, factor-driven with a lookahead bug, and died because 61.3% of signals fired into dead back-leg markets. Here 100% of trading days have a liquid CONTRACTS>0 near+far ATM pair, so that failure mode cannot occur. |

### #4 — SWING_priorweek_f10 : prior-WEEK sweep, daily bars, 10-session hold
| | |
|---|---|
| **Logic** | Same stop-hunt mechanism as #1/#2 but on the **prior WEEK's** swing levels, signalled on daily closes, held a fixed 10 sessions. Delta-1 long. ~12-13 trades/year. |
| **Span / n** | 2021-07..2026-05, 4.87 yrs, 54 active days |
| CAGR | 9.92% | maxDD -21.46% | Calmar 0.46 | **Sharpe 2.41** | NW t **1.02** | PF 1.46 |
| Months positive | 49.2% |
| **★ Why it earns a slot despite t=1.02** | **On MARGINAL contribution, not standalone.** Blending it into the book cut book **maxDD -18.4% -> -9.5%** and worst month **-9.6% -> -4.9%**. A low-frequency, low-correlation sleeve can cut book tail risk more than a high-frequency sleeve that duplicates existing exposure. |
| **Concerns — serious** | **Max single day = 34.7% of total profit** — above the 30% fragility flag. t=1.02 is PROVISIONAL. The parent 50-cell grid saw **7 of 9 build-set survivors go net-negative out of sample**. **PAPER ONLY**, DSR/PBO owed on the 45-cell family. |

### #5 — book_s1f : the firm's existing certified 0DTE short straddle (incumbent benchmark)
Weekly 0DTE naked ATM short straddle, 09:20 entry -> 15:25 flat, no re-entry.
On its own 2022-2025 series: CAGR 9.50% | maxDD -4.65% | **Calmar 2.04** | Sharpe 1.52 | NW t 3.00 |
PF **1.65** | months positive **72.9%** (best) | max day 9.6%.
**Included as the bar every new candidate must clear.** Registered figures (spec-true, dyn margin,
2021-2026) are CAGR 12.57% / maxDD -4.44% / Calmar 2.83 / Sharpe 2.15.
**Its own caveats stand:** Sharpe sits ABOVE the firm's documented VRP ceiling (0.9-1.2) and a
DSR/PBO run over its ~150 in-sample design cells is **still owed**. Beta to NIFTY is ~0 both
full-sample (-0.004) and tail-conditional (-0.013): it is a same-day structure with no gap exposure,
and it contributed **exactly Rs0** on the book's worst 10 days.

---
## ★ CORRELATION RECHECK (the Principal's specific ask)
Method: monthly AND quarterly must AGREE IN SIGN before a verdict is issued — the firm has
established that DAILY sleeve correlation is an artifact (stacked book 0.08 daily -> 0.53 quarterly).
Each pair uses only its overlapping dates; overlap counts reported because spans differ (2011-2026
vs 2015-2026 vs 2021-2026 vs 2022-2025). Firm ceiling for "too correlated" = 0.53.

| pair | overlap (mo) | monthly | quarterly | verdict |
|---|---|---|---|---|
| **SWEEP_E vs SWEEP_D** | 137 | **0.821** | **0.839** | **TOO CORRELATED — size only ONE** |
| SWEEP_E vs CALENDAR | 137 | 0.082 | 0.168 | **GREEN orthogonal** |
| SWEEP_D vs CALENDAR | 137 | 0.147 | 0.185 | **GREEN orthogonal** |
| SWEEP_E vs SWING | 59 | **-0.230** | **-0.114** | **GREEN (negatively correlated)** |
| SWEEP_D vs SWING | 59 | -0.220 | -0.190 | **GREEN (negatively correlated)** |
| SWING vs CALENDAR | 59 | 0.104 | 0.244 | **GREEN orthogonal** |
| CALENDAR vs BOOK | 48 | -0.168 | -0.382 | YELLOW (usefully negative) |
| SWING vs BOOK | 48 | 0.362 | 0.410 | YELLOW |
| SWEEP_E vs BOOK | 48 | 0.102 | -0.019 | NOISE (sign disagrees) |
| SWEEP_D vs BOOK | 48 | 0.022 | -0.023 | NOISE (sign disagrees) |
| IVLOW vs SWEEP_E/D | 40 | -0.308 / -0.300 | -0.243 / -0.096 | GREEN |
| CALENDAR vs IVLOW | 40 | -0.248 | -0.505 | YELLOW |

**HEADLINE: SWEEP (one variant) + CALENDAR + SWING are MUTUALLY ORTHOGONAL — all three pairs GREEN,
and SWEEP-vs-SWING is genuinely NEGATIVE at both frequencies.** That is a real three-sleeve
diversification set, not three views of the same bet. The only hard exclusion is E-vs-D.

---
## OPEN / OWED (nothing below is done)
1. **DSR/PBO** on every candidate at the true trials count. The ledger already caught an undercount:
   the 23-trigger budget searched 5 horizons each = **115 sub-trials, not 23**; EMA stage-1 was 12, not 3.
2. **Risk-equalised sizing** so CAGRs become comparable across utilisation classes.
3. **D-009 verification of the 2015-2020 data segment** — it carries SWEEP's strongest OOS claim.
4. CALENDAR: cross-expiry SPAN margin (real broker number, Tara Singh), and a held-out window with n>1.
5. SWING: DSR/PBO on its 45-cell family; the 34.7% single-day concentration must be explained.
6. The three-way combined book has **never been stress-tested through a real crash** with all sleeves
   simultaneously active; every book-level VaR figure is crash-blind (2022-2025 window).
7. Long-dated SELLING arm (`111`) and STRUCTURAL/expiry arm (`113b`) **both failed on MemoryError**
   (machine had 4.67GB free of 15.6GB) — they load all 7.67M rows at once and must be rewritten to
   process per-year. Their results are MISSING from this ranking.

## FILES
`build_ranking.py` (regenerates everything) · `metrics_all.csv` · `correlation_verdicts.csv` ·
`corr_daily.csv` / `corr_monthly.csv` / `corr_quarterly.csv` · `series_meta.json` (source path,
n, span, %short per series).
