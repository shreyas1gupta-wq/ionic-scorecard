# SHARED CONTEXT — NIFTY 50 "find the best strategy" mandate (2026-07-29, DESK-100)
**Every agent on this mandate MUST read this file first. Do not re-derive any of it.**

## THE MANDATE (Principal, as widened at 22:27)
"just find best, everything is flexible." **Single objective: BEST RISK-ADJUSTED RETURN.**
No constraint on structure, holding period, instrument, trade count, or target size.
LIFTED: intraday-only, option-buying-only, 10-100 trades/month, 10-30pt targets, EMA-as-signal.
In scope: intraday AND multi-day/swing, long options, debit/credit spreads, ratio/backspreads,
calendars/diagonals, delta-1 futures, covered calls, vol-SELLING. All must be rankable on ONE
honest basis so a single comparison table can be built at the end.

## ★★★ MANDATORY: `lib/pathsafe.py` FOR ANY STOP / TRAIL / TARGET RESULT (Principal order 2026-07-30)
**Three failures today, all the same error class — a path-dependent claim made from data that could
not resolve the path, resolved in the flattering direction:**
| claim | reported | honest | error |
|---|---|---|---|
| ITM option + fixed 25pt trail | **+3.03 pts => 69% CAGR** | -0.46 pts | fill-convention |
| S1 z-score, endpoint P&L clipped at -40 | **Calmar 9.88 / 226% CAGR** | Calmar 0.043 / 0.7% | **230x** |
| overshoot vs pre-spike IV | **+9.58 pts** | +2.12 (median -0.16) | 4.5x |
Every one ran in the direction the researcher was hoping for. **Vigilance is not a control; code is.**

**USE `Shreyas_Ionic_AMC/04_RND_LAB/lib/pathsafe.py`. It enforces three rules:**
- **R1 — no path, no claim.** `require_path()` raises on endpoint-only data.
  **`clip_pnl_as_stop()` raises unconditionally**: clipping endpoint P&L at -X credits a stop's benefit
  (trades ENDING worse than -X are truncated) while ignoring its cost (trades that DIP to -X and then
  RECOVER are stopped out). That single shortcut was the 230x error.
- **R2 — both bounds, always.** `simulate_exit()` returns `pnl_pessimistic` (intra-bar ties resolved
  AGAINST the position) AND `pnl_optimistic`. **There is no API returning a single number**, and
  `.pnl` aliases the PESSIMISTIC bound so the honest figure is the easy one. Targets are treated as
  resting LIMITs (exact fill, unambiguous); only stops and trails drive the spread.
- **R3 — a wide spread must be reported as a RANGE.** `summarize()` prints both means plus the
  ambiguous-trade fraction; `.assert_reliable()` RAISES if the spread exceeds 25% of the pessimistic
  mean. Self-test verified: it discriminates properly (a stop+trail-8 config showed 0% spread despite
  10.8% ambiguous bars, i.e. ambiguity that does not matter is not flagged).
```python
from pathsafe import simulate_exit, summarize
res = [simulate_exit(bars_after_entry, entry, direction=+1, stop=60, trail=60) for ...]
summarize(res).assert_reliable()      # raises rather than letting you quote one number
```
**HONEST LIMIT OF THIS GUARD: it catches the PATH-DEPENDENCE class (failures 1 and 2), NOT all
measurement error.** Failure 3 was a variable-alignment bug (a pre-spike price inverted against the
POST-spike spot) — a different class that pathsafe does not detect. For paired-timestamp inputs, assert
explicitly that both legs are read at the SAME timestamp before combining them.

## ★★ EVALUATION FRAMEWORK — CORRECTED 2026-07-30 (Principal ruling; SUPERSEDES t-stat-as-kill-switch)
Principal: *"do not fail just basis t p stats stuff, look logic, look pnl, look if it can work in certain
simple regime like iv filter and 20dma or 50dma or rsi etc, and no overfit and also not too large mdd."*
This restates a standing firm convention — **low t at small n means low POWER, not evidence of no effect.**
Bonferroni/DSR set the CLAIM TIER; they are NOT a kill switch.

**HARD KILLS (these catch FAKE results — non-negotiable):**
1. fails its own PLACEBO (block-permuted / randomized control)
2. any lookahead, same-bar fill, or full-sample percentile
3. **profit concentration >30% from a single trade** (FRAGILE — this is what killed trend-catcher at 309%)
4. **maxDD > 25%** (Principal's hard cap)
5. fills on zero/thin volume that could not have been executed

**SOFT — sets tier, NEVER kills:** t-stat, Bonferroni (p<0.05/466 ~ 0.000107 currently), DSR/PBO.
**MANDATORY TIER LABELS — never collapse the middle two into "dead":**
`CERTIFIED` / `FORWARD-TEST CANDIDATE` / `UNDERPOWERED-UNRESOLVED` / `DEAD`.

**RANK ON:** (1) mechanism — an economic reason statable in one sentence; (2) effect size in points;
(3) NET P&L and its full distribution; (4) robustness across eras, **especially 2025-2026 which the
Principal has made the priority**; (5) maxDD.

**SIMPLE REGIME CONDITIONING IS NOW EXPLICITLY REQUESTED** — report trade P&L conditioned on IV percentile,
price vs 20/50DMA, and RSI(14) bands. TWO GUARDS so it does not become subset-mining:
- **Report ALL buckets with their n, not just the profitable ones.** Selective reporting is the failure mode.
- A conditional result counts only if it (a) has a stateable mechanism, (b) holds in BOTH pre- and
  post-Oct-2024 halves, and (c) has adequate n. **A filter working in only one era is a FITTED PATCH.**

**RE-READ OF TODAY'S KILLS UNDER THIS FRAMEWORK (what changed):**
- STILL DEAD on hard gates: intraday EMA option buying (MFE/|MAE|=1.00 = mechanism failure + negative P&L);
  trend-catcher (309% of profit in 1 trade); swing 50-cell grid (7 of 9 failed held-out); 22/28 regime cells
  and 43/56 MA-RSI cells (failed PLACEBO).
- **NOT DEAD — reclassified UNDERPOWERED-UNRESOLVED:** the **12 MA/RSI cells** flagged underpowered
  (month-end RSI snapshots rarely close in the 30/70 band — never actually tested); the **5 regime cells that
  BEAT placebo** (incl. trend-slope x S1F, p=0.005).
- **UPGRADED to FORWARD-TEST CANDIDATE:** **CALENDAR 1x1 3d-before** (PF 1.60, 15 yrs, bounded max loss,
  **cal-2025 PF 3.90**) — an earlier read leaned too negative on its Bonferroni miss; and the two completed
  **intraday option cells** (build P&L +Rs361k / +Rs134k POSITIVE at t=1.19/0.89 — low-t positives are exactly
  what this ruling covers, though the ITM4 cell did lose on the 2026 held-out set).

## RETAINED GATES (not preferences — these are what make "best" measurable; binding, D-035)
- **Pre-register kill criteria to a file BEFORE running.** Never tune after seeing results.
- **Split:** build 2021-05..2025-12. Forward **2026-01..2026-06 is HELD OUT** — report it, select nothing on it.
- **No lookahead:** entry fills at the NEXT 1-min bar's OPEN after the signal bar closes. Never same-bar.
  Indicators computed PER DAY so no state leaks across sessions. Prior-day levels must use only prior-day data.
- Report **GROSS and NET separately**, and **monthly win-rate on BOTH.**
- Flag concentration: if >30% of profit is one day/trade, call it FRAGILE.
- Tag [DATA] / [INFERENCE] / [OPINION]. Never fabricate. If a metric is undefined, say so and explain.
- Report your honest **trials count** (every config/cell you evaluated) for later DSR/PBO accounting.
- A KILL is a valid, valuable result. Never soften it. Never inflate a survivor.

## COSTS (Principal-supplied, authoritative for this mandate)
- **Options: Rs25 per lot per side** => Rs50/lot round trip = **0.67 premium points** (lot=75).
  Add ATM bid-ask slippage ~0.25-0.5 pt/side => **~1.2-1.7 premium points all-in round trip.**
- **Futures:** round trip **4.47 index pts** (STT 0.0125% pre-2024-10-01) / **5.97 pts** (0.020% after)
  + ~0.5pt slippage => 5.0-6.5 pts. Apply the CORRECT STT rate per era, not one rate throughout.
- Firm reference (more conservative, fine to also report): `06_TRADING_DESK/COST_STANDARDS.md` (D-021),
  `intraday_options_strategy/buying/engine.py::_costs`, `frictions.py::option_costs/slippage_pct`.
- **RETRACTED, do NOT use:** the claim that an ATM option "needs 0.30-0.50% / 60-100 index points to
  break even." That was inherited prose, never derived, and is too harsh for short holds at Rs25/side.
- **CONSEQUENCE: theta over the hold — not transaction cost — is the binding constraint for buyers.**
- **METHOD LAW (Principal):** NO heuristic required-move formulas (he explicitly rejected
  "0.4 x IV x sqrt(h/365) x (1+vig) + kappa" as arbitrary). Settle every pay/no-pay question by
  MEASURING REAL 1-MIN OPTION P&L. If you need IV, derive it from real prices; never assume a level.

## MARGIN RULING (Principal, 22:56) — SUPERSEDES any earlier margin assumption
- **Unhedged / naked short leg: 10% of notional.**
- **Hedged / defined-risk (spread, condor, covered): 5% of notional.**
- Test BOTH where a structure can be run either way and **choose whichever gives the better
  risk-adjusted return** — report both, do not silently pick one.
- This REPLACES the "spot x 75 x 0.15" (15%) figure given to the vol-selling arm. 10%/5% is more
  aggressive (more leverage per rupee) and will RAISE CAGR on margin — so it also raises tail risk
  per rupee of capital. **Report maxDD and worst-day as % of the margin-based capital**, not just in
  rupees, or the leverage advantage will look free when it is not.
- Still binding: margin must be DYNAMIC (scales with spot), never a flat hardcoded rupee figure.
  The firm was burned once by a flat-margin assumption that inflated a CAGR from 12.6% to 28.9%.

## BREADTH PROTOCOL (Principal 22:56 asked for "100 other stuffs"; reconciled with "no overfit")
Broad search is permitted and encouraged, but under these terms, because breadth has a real
statistical price that must be paid openly:
1. **Every trial enters the trials ledger** (`results/OVERFIT_AUDIT_20260729/TRIALS_LEDGER.csv`).
   No unlogged exploration. The ledger, not the winner's t-stat, is the honest record.
2. **The significance bar RISES with the count.** Bonferroni at m=100 needs |t| ~ 3.48; at the firm's
   cumulative ~349 trials it needs ~3.80. **Consequence the Principal must see: the session's current
   flagship (`sweep_priorday_reclaim`, t=3.10) does NOT clear a 100-trial correction.** Expanding the
   search actively DESTROYS the claim-ability of the current lead.
3. **Therefore broad search = HYPOTHESIS GENERATION, not validation.** Survivors are forward-test
   candidates, never "validated strategies". Anything promoted must earn it on data untouched by the
   search — the held-out 2026 H1 (whose power is itself thin, ~5 months) or a live forward clock.
4. **Orthogonality requirement (empirically established TODAY):** stacking correlated price-derived
   trend proxies bought NOTHING (confluence: n collapsed 18,697->35 while t never cleared 2). So a new
   candidate earns its place only if it draws on a genuinely DIFFERENT information source or mechanism
   — not another transform of the same price series. Prefer 10 orthogonal families over 100 correlated
   variants; 100 correlated variants is precisely the failure mode already demonstrated.

## ★★ BACKTEST QUEUE — MANDATORY ARCHITECTURE (Principal ruling 2026-07-30 01:30)
Last session ~10 agents each ran a big pandas backtest simultaneously; a numpy MemoryError killed
the debit-spreads arm and bash could no longer fork. **Fix: parallelism is decoupled from RAM.**
- **DO NOT run a heavy backtest yourself.** Write it as a self-contained argument-free `.py`
  (writing its own outputs to its own results dir) and DROP IT IN:
  `Shreyas_Ionic_AMC/04_RND_LAB/results/BACKTEST_QUEUE_20260730/queue/NNN_yourname.py`
  Lower NNN = higher priority; use 100+ unless your job gates others.
- A serial runner (`runner.py`, already running) executes ONE job at a time, logs to
  `logs/NNN_yourname.log`, moves the script to `done/`, and records exit status in `status.json`.
  Jobs exceeding 1h are KILLED and marked TIMEOUT, so no runaway can block the queue.
- **While you wait, do CHEAP work:** write the pre-registration, define signals, inspect schemas
  with column-subset reads, analyse CSVs that already exist, draft the SUMMARY.md skeleton.
- Small/cheap probes (a few thousand rows, column-subset reads) may still be run directly.
  Anything scanning the full 0.5-1M-bar 1-min files or looping the whole option chain MUST be queued.
- Poll `logs/` and `status.json` for your result. Never assume a queued job succeeded.

## ★★ LONG-DATED OPTIONS *ARE* TESTABLE — corrects an earlier "not testable" verdict
An earlier check of the 1-min option tree found max ~10 DTE and I wrongly concluded long-dated
options could not be tested. **WRONG — the firm has a 16-year daily F&O archive:**
`Shreyas_Ionic_AMC/05_DATA_OFFICE/data/fo_bhavcopy_hist/fo_idx_{2011..2026}.parquet`
cols: INSTRUMENT, SYMBOL, EXPIRY_DT, STRIKE_PR, OPTION_TYP, OPEN, HIGH, LOW, CLOSE, SETTLE_PR,
      CONTRACTS, OPEN_INT, CHG_IN_OI, TIMESTAMP   (filter SYMBOL=='NIFTY', INSTRUMENT contains 'OPTIDX')
Measured traded (CONTRACTS>0) depth on a sampled year: **max DTE traded = 1,794 days (~5 yrs)**
| DTE band | traded rows | distinct expiries |
|---|---|---|
| 7-20 | 70,178 | 54 |
| 20-45 | 62,950 | 55 |
| 45-100 | 42,131 | 16 |
| 100-200 | 5,892 | 6 |
| 200-400 | 5,279 | 8 |
=> **biweekly, monthly, bimonthly and 6-month structures (income AND portfolio hedges) are all
testable at DAILY granularity over 16 years** (longer history than the 11.34-yr 1-min series).
**★ NEW LANDMINE (found 2026-07-30 02:05, killed 2 queued jobs in <7s) — MIXED DATE FORMATS.**
`EXPIRY_DT` and `TIMESTAMP` are STRINGS with INCONSISTENT formats. The first row of each year looks
4-digit ('27-Jan-2011', '01-JAN-2026'), which lulls you into `format='%d-%b-%Y'` — but **the LONG-DATED
expiry rows use a 2-DIGIT year ('14-May-12', '31-May-12')**. So the very rows you need for long-dated
work are the ones that break the parse. Also note case varies ('Jan' vs 'JAN') across years.
**THE FIX (verified: parses all 16 years, 0 unparsed rows):**
```python
d["EXPIRY_DT"] = pd.to_datetime(d["EXPIRY_DT"], format="mixed", dayfirst=True)
d["TIMESTAMP"] = pd.to_datetime(d["TIMESTAMP"], format="mixed", dayfirst=True)
```
`dayfirst=True` is REQUIRED — without it '14-May-12' could resolve to 2014-05-12 instead of 2012-05-14,
silently shifting expiries by years. Never pass an explicit `%d-%b-%Y`.

**CRITICAL GATES for this dataset (violating these fabricates results):**
1. **Only 231,973 of 394,283 OPTIDX rows have CONTRACTS>0** — 41% are LISTED-BUT-UNTRADED with model
   settles. **Gate EVERY leg on CONTRACTS>0**, and fall back to the liquid expiry, else you silently
   skip months (CLAUDE.md landmine #9).
2. **NEVER read an expiry-day option SETTLE_PR as the option price** — on expiry day it is the
   UNDERLYING's final settlement level. This once produced -15,428 fake points. Cash-settle at
   intrinsic from the underlying instead.
3. Daily granularity => intraday stops/trailing CANNOT be modelled here. Use close-to-close, state it,
   and do not claim intraday exit precision. For intraday realism use the 1-min tree (2021+, <=10 DTE).

## ★★ TWO STRUCTURAL BREAKS IN THE NIFTY OPTION MARKET — check every option backtest against both
**BREAK 1: WEEKLY OPTIONS LAUNCHED FEB-2019.** Verified from the bhavcopy archive itself (traded
expiries per year): **2011-2018 = exactly 12/yr, Thursday** (monthly ONLY — weeklies did not exist);
**2019 = 47**; 2020-2024 = 52-53; **2025 = Thu 34 + Tue 17** (the mid-2025 Thursday→Tuesday switch);
**2026 = Tue 32** (fully switched). The archive independently reproduces all three real changes.
CONSEQUENCES:
- Any strategy needing a WEEKLY expiry **cannot be tested before Feb-2019.** A pre-2019 "weekly"
  result is fabricated. MONTHLY options are fine — they trade since 2001.
- **Empirically it is not just a data constraint, it is a REGIME break.** The monthly calendar
  candidate earns **+0.88 pts/trade pre-2019 (n=93, i.e. nothing)** vs **+18.32 pts 2019-2026
  (n=85)**. Its whole edge is post-weekly-launch. So a long span can DILUTE a claim rather than
  support it — always split pre/post 2019 and report both.
- [INFERENCE] plausible mechanism: weekly options transformed the front end (India = largest options
  market by contract count, heavy retail weekly demand), so front-month vol may be structurally
  richer vs next-month since 2019. Fitted after seeing the split → needs independent testing.
**BREAK 2: Oct/Nov-2024 SEBI F&O tightening** (lot sizes raised, weekly expiries rationalised to one
per exchange; futures STT 0.0125%→0.020% on 2024-10-01) and the **Sept-2025 Thu→Tue expiry swap.**
Still under test. **If confirmed, every pre-2024 backtest here has reduced relevance to today.**
**STANDING REQUIREMENT: every option-strategy result must report pre-2019 / 2019-2024 / 2024+ splits
separately.** Delta-1 FUTURES work is exempt from Break 1 (NIFTY futures trade since 2000).

## ★ REVERSE-THE-STRONG-NEGATIVE RULE (Principal, standing convention)
"If some strategy is too negative we can look just opposite of it too." Auto-test the reversal of any
strongly-negative result. **BUT the critical distinction:** reversal only rescues DIRECTIONAL losses,
never COST-DOMINATED ones — if a strategy loses because friction ate it, the reverse ALSO loses to
friction. Always report gross pre-cost edge on BOTH sides to tell which case you are in.
Already-established instances:
- Long ATM straddle unconditional: -22.93 pts, t=-1.73 -> its reverse IS S1-F, the firm's certified
  best strategy (12.57% CAGR). Coherence check PASSED.
- **IV top-decile buying: -75.77 pts, t=-1.98 -> reverse = SELL premium when IV is top-decile.**
  Strongest actionable lead from the inverse-VRP arm.
- `sweep_intraday_reclaim` continuation: t=-3.64 -> its FADE is the tradeable side.
- Overnight straddle BUY: t=-2.5..-2.6 killed (K-017). Note overnight SELL was ALSO killed (NS-1) =>
  this pair is COST-DOMINATED, not directional. Do not "reverse" it again.

## DATA (verified today)
- **NIFTY 1-min SPOT:** `intraday_options_strategy/datasets/raw/hf_index_options_1m/index/NIFTY.parquet`
  463,826 bars 2021-05-24..2026-06-03. cols timestamp(tz+05:30)/open/high/low/close/volume/trading_day/symbol.
  **index `volume` is 0/unusable.** **LANDMINE: filter time>=09:15** — 09:00-09:07 bars are PRE-OPEN
  AUCTION prints and are present in this file (will corrupt any gap/open calc).
- **NIFTY weekly OPTIONS 1-min:** `.../hf_index_options_1m/options/NIFTY/{expiry}.parquet` — 261 valid
  weekly expiries 2021-05..2026-06. Each file = the FULL multi-day life of that expiry at 1-min,
  ~78-145 strikes. cols +volume/open_interest/strike/option_type(CE|PE)/expiry.
  Skip CORRUPT `2023-06-29` and stub `2026-06-09`. **OI only partially populated 2025+** → any
  PCR/OI signal has thin, short history; state that explicitly, never hide it.
- **REUSE, do not rewrite:** `intraday_options_strategy/buying/chain.py` →
  `build_expiry_index()`, `load_expiry(exp)`, `day_chain(exp,day)`, `nearest_expiry(day,min_dte,max_dte)`,
  `load_index()`. Also `engine.py` (STEP=50, `_costs`), `frictions.py`, `engine_swing.py` (multi-day
  long-CE engine incl. trail/target/stop and debit-spread support — closest existing thing to a swing engine).
- **LANDMINE #9:** never read an expiry-day option settle as a price. Cash-settle held-to-expiry
  positions at INTRINSIC from the underlying.
- Other data: `datasets/etf_gold_silver/niftybees_daily.parquet` (2013-26), `datasets/index_daily/
  nse_official_all_indices.parquet` (174 indices, OHLC+PE/PB, 2016-2026).

## WHAT IS ALREADY SETTLED TODAY (do NOT re-test; build on it)
Full detail: `04_RND_LAB/results/PROGRESS_OPTION_BUYING_20260729.md` and
`.../EMA_INTRADAY_BUYING_20260729/SUMMARY.md`.
1. **Intraday EMA option buying = KILLED.** Signed move 0.0040-0.0101%; hit 50.2-51.3% (coin flip);
   **MFE/|MAE| = 1.004-1.018 (ZERO convexity)**; t=0.6-1.3.
2. **EMA delta-1 futures arm = NET NEGATIVE.** Gross Rs8.14L vs costs Rs21.49L (**costs 2.6x gross
   edge**), NW t -2.4..-4.6. Gross edge 1.25-2.17 pts < the 5.0-6.5 pt futures cost bar.
3. **THE TRAP (most reusable finding):** that same arm was **62.3% of months positive on GROSS but
   only 24.6% on NET** (longest losing streak 14 months). The Principal's original "consistent
   month-by-month positive returns" ask was reachable ONLY as a cost-modelling artifact.
   **Always produce the gross-vs-net monthly table.**
4. **22 triggers measured** (`EMA_INTRADAY_BUYING_20260729/signal_budget/`, reuse its indicator code):

| trigger | n(build) | signed % | pts | t | conc |
|---|---|---|---|---|---|
| **sweep_priorday_reclaim** | 1775 | **0.0560** | **10.03** | **3.10** | 0.13 |
| sweep_intraday_continue | 5836 | 0.0336 | 6.52 | 2.94 | 0.11 |
| supertrend_15m_ATR14x3 | 79 | 0.0431 | 9.65 | 1.80 | 0.26 |
| supertrend_15m_ATR10x3 | 156 | 0.0429 | 8.65 | 2.30 | 0.14 |
| volbrk_orb_volfilter | 994 | 0.0279 | 5.60 | 2.23 | 0.07 |
| sr_month_reject | 1363 | 0.0243 | 5.37 | 1.53 | 0.22 |
| supertrend_5m_ATR10x3 | 1269 | 0.0236 | 4.81 | 2.76 | 0.07 |
| sr_week_reject | 2935 | 0.0206 | 3.98 | 2.00 | 0.11 |
| **sweep_intraday_reclaim** | 3557 | **-0.0070** | -1.44 | **-3.64** | 0.05 |

**Two real positives:** (a) `sweep_priorday_reclaim` (sweep of PRIOR day's swing high/low then
reclaim, 15-min bars) is the FIRST trigger ever to clear the ~6.5pt futures cost bar. (b)
`sweep_intraday_reclaim` is significantly INVERTED (t=-3.64) → its **FADE** is the tradeable side.
5. **Confluence stacking buys APPEARANCE, not significance:**

| conditions | n | pts | t | conc |
|---|---|---|---|---|
| 1 | 18,697 | 0.25 | 0.66 | 0.19 |
| 2 | 6,634 | 2.79 | 1.57 | 0.19 |
| 3 | 463 | 2.03 | 0.46 | **0.79** |
| 4 | **35** | **20.74** | 1.73 | 0.28 |

n collapses, per-trade edge inflates, **t never clears 2**; at 3 conditions 79% of edge is ONE day.
The 4-stack (best raw number of the session) is 35 trades in 4.6 yrs at t=1.73 = **noise.**
This is the cell a naive multi-indicator build would ship. Treat any high-mean/low-n cell as suspect.
6. **Prior art, do not re-litigate:** `intraday_options_strategy/buying/REPORT.md` (2026-07-01) killed
   ~14 option-BUYING structures. `KNOWLEDGE_BASE` lesson 24: NIFTY's robust edge is vol SELLING (VRP),
   realistic ceiling ~15-25% CAGR / Sharpe 0.9-1.2 post-cost.

## THE KEY OPEN QUESTION (why the multi-day arms matter most)
Everything killed today died on **MAGNITUDE** (move too small for the premium+costs). Longer holds
largely solve magnitude — a 15-35 DTE swing gives the index room to travel 1-3% — and instead face
**PREDICTABILITY** risk. These are DIFFERENT failure modes, so today's intraday kills do NOT transfer
to swing horizons. Multi-day/swing is genuinely UNTESTED here and carries the best remaining odds
(roadmap prior ~10% for trend-catcher, the highest of the buying archetypes).

## BENCHMARK TO BEAT (the firm's certified live strategy)
**S1-F**: NIFTY weekly 0DTE naked ATM short straddle, real-fill validated.
**12.57% CAGR / -4.44% maxDD / Calmar 2.83 / Sharpe 2.15 / PF 2.21 / n=204 / win 74%.**
Any candidate must be compared against this. If something beats or genuinely diversifies it, that is
a significant finding → flag for IC review, do not bury. Also note the firm's honest S1-F caveat:
its Sharpe 2.15 sits ABOVE the documented VRP ceiling, and a DSR/PBO run on its ~150 in-sample
design cells is still OWED — so do not treat 2.15 as an easy bar to clear honestly.

## ENVIRONMENT
Python: `C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe`
(the bare `python` alias is BROKEN). Always set `PYTHONIOENCODING=utf-8`, `PYTHONUNBUFFERED=1`
(console is cp1252). pandas needs freq alias **`'5min'` not `'5T'`**. PowerShell 5.1 has no `&&` —
write Python to .py files rather than here-strings. Long jobs: run in background, write results to disk.
**NO real-money trades, ever** (Angel account is data-only). Everything here is research/paper.
