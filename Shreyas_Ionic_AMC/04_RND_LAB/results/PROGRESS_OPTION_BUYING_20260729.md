# PROGRESS — NIFTY 50 option-buying / momentum mandate (2026-07-29, DESK-100)

**GOAL (Principal, this session):** momentum strategy on NIFTY 50 using EMA, option BUYING only
("check futures also"), intraday only, multi-filter (supertrend / volume / PCR / candle / liquidity
sweep of prev+current day swing H-L on 15min / weekly-monthly S-R), best risk-adjusted return,
"consistent month-by-month positive returns". Plus a SEPARATE covered-call programme on a NIFTY 50
holding (1/2 lot, 5% margin assumed, premium swept into more underlying each cycle, "batman"
structure, trend + overbought/oversold optimized).

## MANDATE WIDENED (Principal, 22:27) — SUPERSEDES the constraints above
"not necessary this and all prev rules just find best everything is flexible".
**Objective is now simply: BEST RISK-ADJUSTED RETURN. No constraint on structure, holding period,
instrument, trade count, or target size.** Explicitly LIFTED: intraday-only; option-buying-only;
10-100 trades/month; 10-30 pt targets; EMA as the signal.
=> multi-day / swing holds, debit & credit spreads, ratio structures, delta-1 futures, and
vol-SELLING are all now in scope and must be ranked in ONE comparison table on the same honest basis.
**RETAINED (not preferences — these are what make "best" measurable):** pre-registration before
running, held-out 2026-01..06 forward set, real 1-min fills, red-team, trials/DSR accounting,
gross-vs-net reporting. Without these the winner is just the luckiest overfit (see the 4-condition
confluence cell: best raw number in the session at 20.74 pts, n=35, t=1.73 = noise).

**COST CORRECTION (Principal, 22:21):** transaction cost is **Rs25/lot/side** => Rs50/lot round trip
= **0.67 premium points**, plus ATM slippage ~0.25-0.5 pt/side => **~1.2-1.7 premium points all-in.**
**RETRACTION:** my earlier "ATM option needs 0.30-0.50% / 60-100 index points to break even" was
INHERITED from REPORT.md prose, never derived, and is too harsh for short intraday holds at these
costs. The "30-75x too small" multiples quoted for the EMA cells were overstated on that basis.
The EMA kill nonetheless STANDS on cost-independent grounds: futures cost 4.47-5.97 pts (published
STT rates) vs edge 1.25-2.17 pts; hit rate 50.2-51.3%; MFE/|MAE| = 1.00-1.02.
CONSEQUENCE: **theta over the hold, not transaction cost, is the binding constraint for buyers.**
Note the running workflow uses the harsher legacy model (~1.7 pts) — it biases AGAINST finding edge,
so anything that survives it also survives Rs25/side; only MARGINAL failures need a re-check.

**PRINCIPAL METHOD RULING (mid-session):** heuristic required-move formulas are REJECTED
("0.4 x IV x sqrt(h/365) x (1+vig) + kappa" — arbitrary coefficient). All pay/no-pay questions must be
settled by MEASURING REAL 1-MIN OPTION P&L from the parquet option chain. No formula proxies.
This is now binding on every arm.

---

## DONE (all pre-registered before running; nothing tuned after seeing results)

### 1. Intraday EMA option buying — **KILLED** (Stage-1 gate failed, Stage-2 never built)
`results/EMA_INTRADAY_BUYING_20260729/` — pre-reg: `ideas/20260729_intraday_ema_option_buying.md`
Signed forward move 0.0040-0.0101% vs the 0.30% pass bar (**30-75x too small**); hit rate 50.2-51.3%
(coin flip); **MFE/|MAE| = 1.004-1.018 (zero convexity)**. Independently reproduces the 2026-07-01
study's MFE/MAE~1.00 via a different signal (intraday EMA vs that study's ORB/daily-EMA) — the one
untested gap is now closed too.
Gate-3 placebo deliberately skipped on failed cells (can only reject, never rescue) — disclosed.

### 2. EMA futures arm (delta-1, no theta/VRP) — **net NEGATIVE**
Gross **+Rs8,13,867** vs costs **Rs21,49,351** = net **-Rs13,35,484**. Costs = **2.6x the gross edge.**
NW t **-2.4 to -4.6** (significantly negative). Gross edge 1.25-2.17 pts vs round-trip cost
**4.47 pts (STT 0.0125% pre-Oct-2024) / 5.97 pts (0.020% post)** + 0.5pt slippage = 5.0-6.5 pts.
Edge is 2-4x too small EVEN IN FUTURES. => futures cost bar for any trigger is **>6.5 gross pts**.
DEFECT NOTED: fixed 1-lot on Rs3L drove equity negative, so that script's CAGR/maxDD print
nan / -468% and are UNDEFINED, not "very negative". Being fixed with margin-based sizing in the
sweep-futures arm. Do not quote those two numbers.

### 3. THE HEADLINE TRAP (most reusable finding of the session)
Same futures arm: **62.3% of months positive on GROSS, only 24.6% on NET** (longest losing streak
14 months). The Principal's requested "consistent month-by-month positive returns" was achievable
ONLY as a cost-modelling artifact. **Standing check: always demand the gross-vs-net monthly table.**

### 4. Signal budget — 22 triggers measured (`EMA_INTRADAY_BUYING_20260729/signal_budget/`)
Verdict line: `ALL_FAIL_signal_magnitude_below_option_budget`. Best of each family (build set):
| trigger | n | signed % | pts | t | conc |
|---|---|---|---|---|---|
| **sweep_priorday_reclaim** | 1775 | **0.0560** | **10.03** | **3.10** | 0.13 |
| sweep_intraday_continue | 5836 | 0.0336 | 6.52 | 2.94 | 0.11 |
| supertrend_15m_ATR14x3 | 79 | 0.0431 | 9.65 | 1.80 | 0.26 |
| supertrend_15m_ATR10x3 | 156 | 0.0429 | 8.65 | 2.30 | 0.14 |
| volbrk_orb_volfilter | 994 | 0.0279 | 5.60 | 2.23 | 0.07 |
| sr_month_reject | 1363 | 0.0243 | 5.37 | 1.53 | 0.22 |
| **sweep_intraday_reclaim** | 3557 | **-0.0070** | -1.44 | **-3.64** | 0.05 |

**TWO REAL POSITIVES:** (a) `sweep_priorday_reclaim` is the FIRST trigger ever to clear the ~6.5pt
futures cost bar (10.03 pts, t=3.10, n=1775) — genuinely new, on-mandate, worth a real futures test.
(b) `sweep_intraday_reclaim` is significantly INVERTED (t=-3.64) → its FADE is the tradeable side.

### 5. Confluence stacking — **stacking buys APPEARANCE, not significance**
| conditions | n | pts | t | conc |
|---|---|---|---|---|
| 1 | 18,697 | 0.25 | 0.66 | 0.19 |
| 2 | 6,634 | 2.79 | 1.57 | 0.19 |
| 3 | 463 | 2.03 | 0.46 | **0.79** |
| 4 | **35** | **20.74** | 1.73 | 0.28 |
n collapses, per-trade edge inflates, **t never clears 2**, and at 3 conditions 79% of the edge is ONE
day. The 4-condition cell (20.74 pts — best number in the session) is 35 trades in 4.6 yrs at t=1.73:
noise. This is the exact cell a retail multi-indicator build would select. Answers the Principal's
"club indicators with volume/PCR/candle/sweep/S-R" question: it does not fix magnitude.

### 6. Roadmap delivered — `results/OPTION_BUYING_ROADMAP_20260729/ROADMAP.md`
Archetypes formalized (trend-catcher vs bull-pulse DTE mechanics, event-pulse, vol-breakout,
gap-risk), ranked research queue with pre-registered kills, STOP rule, honest priors
(trend-catcher ~10%, indicator-pulse ~2%, event-pulse ~15%, vol-breakout ~20-25%, gap-risk ~10-15%).
NOTE: its required-move FORMULA is superseded by the Principal's real-price ruling above; the
archetype/DTE reasoning and the queue remain valid.

---

---
# ★ THE SESSION'S ONE REAL SURVIVOR — LIQUIDITY SWEEP (stop-hunt), delta-1 NIFTY 50
`results/SWEEP_11YR_20260729/` (sweep_11yr.py, sizing_fix.py, carry_adj.py, heatmaps, trade CSVs)

**NEW DATA FOUND (changes the statistics): `intraday_options_strategy/datasets/processed/nifty_1min.parquet`
= 1,047,541 bars, 2015-01-09..2026-05-14, **11.34 YEARS** (the session had been using a 5.03-yr file).
Matching `vix_1min.parquet` same span. Provenance: almost certainly Kaggle debashis74017/nifty-50-minute-data.
=> 2015-01..2021-04 is a PRISTINE out-of-sample segment never touched by any of today's search, and it
CONTAINS COVID-2020 + 2015-16 correction + 2018 IL&FS. Every MDD quoted from the 5-yr file is
optimistic by construction (no crisis in that sample).

**Signal:** `sweep_priorday_reclaim` on 15-min bars = price sweeps PRIOR DAY's swing high/low (running the
stops parked there) then RECLAIMS the level -> trade the reversal. PIT-safe (prior-day levels only;
intraday reference shifted 2 bars). This IS the "stop-hunting / manipulation" mechanism the Principal
asked about — already found and quantified. The CONTINUE variant does NOT work; only the RECLAIM does.

**HEADLINE (1 lot, Rs10L, era-correct STT, WITH Principal's +0.5%/mo futures carry):**
| config | n | pts | CAGR | maxDD | Calmar | Sharpe | PF | t | mo+ |
|---|---|---|---|---|---|---|---|---|---|
| **E 3-day hold, trail 60** | 4378 | 16.01 | **15.33%** | **-18.02%** | 0.85 | **1.84** | 1.40 | **4.35** | 90/137 (65.7%) |
| **D overnight, trail 40** | 4378 | 10.43 | 10.83% | **-11.39%** | **0.95** | 1.45 | 1.29 | 3.58 | 88/137 (64.2%) |
| E, no carry (earlier quote) | 4378 | 14.66 | 14.40% | -21.66% | 0.66 | 1.65 | 1.34 | 3.92 | 83/137 |

Windows (E, with carry): OOS_2015-2021 **CAGR 19.41% / MDD -18.02% / PF 1.37 / t=3.04**;
IS_2021-2025 25.54% / -11.33% / PF 1.45 / t=3.05; FWD_2026 (n=135, thin) 28.77% / -7.89%.
**Holds on the pristine never-searched segment — the strongest validation evidence of the session.**

**WHY CARRY HELPS (and why it matters more than the CAGR):** the book is **54.5% SHORT / 45.5% LONG.**
Long futures PAY carry (buy at premium, decays to spot); shorts RECEIVE it. So a short-tilted book nets
carry income. **Consequence: this is a near-market-neutral, slightly short-biased strategy that made money
across 2015-2026 while NIFTY rose a lot => it CANNOT be disguised beta.** That is what makes it a genuine
portfolio diversifier rather than another long-equity proxy — see PORTFOLIO_MARGINAL_20260729.
Trade profile: mean 16.0 pts, **p95 202.5 pts, max win 606.7 pts**, worst -60.5, largest single trade only
**1.3% of total profit** (healthy distribution, NOT the fragile 4-of-22-trades pattern). ~32 trades/month.
Win rate **47.6%** — it earns on payoff asymmetry (trailing), not on hit rate.

**SIZING (Principal asked 1-lot vs 0.1-Kelly). Two of my own bugs found and fixed — disclosed:**
the original `kelly01` output (maxDD -266%/-319%/-409%, CAGR 8.2e10%/1.4e17%) was INVALID: lot count
compounded with equity with no ruin constraint AND drawdown was computed as CAPITAL+cumsum over a
compounding path. Corrected in `sizing_fix.py` (equity-path metrics, ruin floor, margin+max-lots caps).
| risk/trade | CAGR | maxDD | Calmar | Sharpe | med lots |
|---|---|---|---|---|---|
| 1 lot fixed (E) | 14.4% | **-21.7%** | 0.66 | 1.65 | 1 |
| 0.50% | 35.5% | -35.9% | 0.99 | 1.75 | 4 |
| 0.75% | 61.0% | -52.8% | 1.16 | **1.85** | 21 |
| 1.90% (=0.1 Kelly, Kelly f*=0.19) | 75.9% | **-77.7%** | 0.98 | 1.62 | 200(cap) |
| 5.00% | 78.4% | -79.6% | 0.98 | 1.25 | 200(cap) |
**KEY: leverage does NOT improve risk-adjusted return — Calmar stays 0.66-1.36 across a 10x size range and
Sharpe PEAKS at ~0.75% then DEGRADES.** 0.1-Kelly buys 76% CAGR at -78% MDD => fails the low-MDD goal.
**For the Principal's low-MDD priority: 1 lot (or <=0.5% risk).** At 0.25% risk it cannot trade at all
(<1 lot) => **Rs10L is near minimum viable capital** at lot granularity.

**HONEST CONCERNS (do not bury):**
1. **2025 is the WORST year in the 11-yr sample** (config D -Rs247k; H2-2025 lost 6 of 7 months). Live decay
   signal in the most recent complete year, partially offsetting the strong 2015-2021 OOS.
2. **Spot used as futures proxy** — no NIFTY futures 1-min data exists (searched HF + Kaggle 2026-07-30;
   none found; only index 1-min and possibly single-stock F&O). Mitigated by the Principal's +0.5%/mo carry
   adjustment, now applied. Real basis/roll behaviour still unmodelled.
3. **2015-2020 segment has NEVER passed the firm's D-009 data verification** — and it carries the strongest
   OOS claim. VERIFY BEFORE RELYING ON IT.
4. Calmar 0.85 (E) / 0.95 (D) is still BELOW certified S1-F (Calmar 2.83, Sharpe 2.15). Not a replacement —
   its case is as a market-neutral DIVERSIFIER.
5. Trials: still needs the session-wide DSR/PBO correction (OVERFIT_AUDIT_20260729). At t=4.35 it clears
   Bonferroni for m=100 (3.48) and m=349 (3.80), but that is the naive correction, not DSR.

# ★ HARD DATA LIMIT — kills the long-dated-hedge idea (measured 2026-07-30)
Sampled 12 NIFTY expiry files for max DTE carrying REAL traded volume:
**max DTE with any traded volume = 20 days (ONE 2021 expiry); MEDIAN per-expiry max traded DTE = 10 days.**
Each expiry parquet holds only ~the last 10 days of that contract's life.
=> **6-month hedges: NOT TESTABLE. Bimonthly selling: NOT TESTABLE. >~10-20 DTE: no data at all.**
Biweekly (~10d) is at the very edge. Any "result" beyond ~10 DTE would come from LISTED-but-UNTRADED
model-priced strikes (firm landmine: far expiries carry model settles with CONTRACTS=0) = fabricated.
The trend-catcher arm was re-scoped mid-flight because of this.
Also confirmed: **index 1-min `volume` = 0 across ALL 477,738 rows** (unusable), but **option-chain volume
is FULLY populated** (350,745/350,745 nonzero on a sampled expiry; OI full for 2024, ~34% for 2025)
=> volume/OI/PCR microstructure must be sourced from the OPTION CHAIN, and only 2021-05 onward.

# PRINCIPAL RULINGS ADDED LATE IN SESSION
- **Scope narrowed: NIFTY 50 ONLY, futures + options only.**
- Margin: **10% unhedged / 5% if hedged with the SAME EXPIRY**, % of notional.
- Futures proxy: spot **+0.5%/month** cost of carry, scaled to holding period (longs pay, shorts receive).
- Low-frequency strategies ARE acceptable if they add portfolio value ("think like quant") — judge on
  MARGINAL book contribution, not standalone. NOTE the distinction that matters: low TRADE COUNT is not
  disqualifying; low STATISTICAL RELIABILITY is. The 4-stack confluence cell failed on t=1.73, not on n=35.
- Breadth ("100 other stuffs") permitted as HYPOTHESIS GENERATION under the ledger + rising significance
  bar; survivors go to forward test, never straight to "validated".

## IN FLIGHT
- **Workflow `wf_a1fb9469-ea1`** (9 agents, 3 concurrent per D-023):
  Harness (`results/OPTION_PL_HARNESS_20260729/opt_pl.py`, must include a random-entry control that
  MUST lose) → 3 measure arms (bullish sweep x DTE{0-1,2-3,4-7} x moneyness; bearish on real PE with
  skew cost measured; confluence+vol-breakout with real entry-IV percentile) → sweep FUTURES arm
  benchmarked vs certified S1-F (12.57% CAGR / -4.44% MDD / Calmar 2.83 / Sharpe 2.15) → 3 red-team
  lenses (lookahead+fills / selection+overfit at the TRUE trials count / cost+liquidity at 1.5x-2x
  slippage) → synthesis to `results/SESSION_VERDICT_20260729.md`.
- **Covered-call agent** → `results/COVERED_CALL_NIFTY_20260729/DESIGN.md` (not yet on disk).
  Must resolve: "unlimited loss after 2sd upside" contradicts a TRUE covered call (upside is CAPPED
  because the underlying is owned) — unlimited loss only if calls are written on MORE notional than
  held. "1/2 lot of underlying holding" is ambiguous (write against half the holding = safe, vs write
  1-2 lots regardless of holding = possibly naked). BOTH interpretations costed at +2sd/+3sd.
  Also: "5% margin" implies a LEVERED FUTURES holding (~20x), not cash ETF units — changes drawdown
  maths completely and must not be assumed away.

## NEXT STEP (exact)
1. Read workflow result → `results/SESSION_VERDICT_20260729.md`.
2. If the sweep futures arm survives red-team, it is the first IC-worthy candidate from this line —
   route to IC, do not bury. If it dies, record the kill with numbers.
3. Update `01_COMMAND_CENTER/SESSION_JOURNAL.md` + `CURRENT_STATE.md` (session protocol) and log
   the trials count into the ledger (this session added ~22 budget triggers + 3 EMA cells +
   the DTE/moneyness grids — material for DSR/PBO accounting).
4. Not committed to git (not requested).

## HARD CONSTRAINTS IN FORCE
No real-money trades (Angel is data-only). Costs only from COST_STANDARDS.md (D-021).
Landmines respected: bars >=09:15 (pre-open auction), next-bar-open fills, per-day indicator state,
no expiry-day option settle as a price (#9). Index 1-min `volume` is 0 → volume/PCR must come from
the option chain, where OI is only partial 2025+ (thin PCR history — state, don't hide).
