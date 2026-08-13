# Option-Buying Roadmap — structured thinking, not a backtest
**R&D Head: Aditya Verma | 2026-07-29 | Stage: pre-registration for Gate-2/3 (RESEARCH_SOP §7)**

**Scope note:** this document formalizes the Principal's four named archetypes (trend catcher, bull
pulse, volatility-breakout directional long, bear/bull counterparts) into falsifiable hypotheses
with derived DTE/moneyness, a ranked test queue, and honest priors. It does **not** re-run signal
magnitude measurement — that is Arjun Rao's concurrent job
(`results/EMA_INTRADAY_BUYING_20260729/SUMMARY.md`), and I use his output as given evidence below,
not as something to reproduce. [DATA] tags mark verified firm numbers; [INFERENCE] marks derivations
from option-pricing mechanics; [OPINION] marks my judgment calls.

## 0. The evidence this roadmap is built on (given, not re-derived)
- [DATA] Intraday indicator signals on NIFTY: gross edge +1.25 to +2.17 index pts; futures
  round-trip cost 4.5–6.5 pts; ATM weekly option breakeven ~60–100 pts (0.30–0.50% of spot)
  (`EMA_INTRADAY_BUYING_20260729/SUMMARY.md`, `stage1_report.json`, `futures_report.json`).
- [DATA] Same study, futures arm, 61 months: gross ₹8.1L vs costs ₹21.5L (costs = 2.6x gross),
  Newey-West t −2.4 to −4.6, 62.3% of months positive on GROSS vs **24.6% positive on NET**.
- [DATA] MFE/|MAE| ≈ 1.00–1.02 across every trigger tested (EMA cross, ORB, mean-rev, shakeout,
  doji, gap-fade, RSI/MACD/S-R, 0.7Δ/0.3Δ) — **no exploitable asymmetry in any indicator-triggered
  intraday setup.** Hit rates 50.2–51.3% (coin flip). K-001: 14 variants; this study: 3 more —
  17 trials, all dead, same conclusion from two independent builds.
- [DATA] `KNOWLEDGE_BASE.md` lesson 1: "VRP is the meta-edge in Indian options: implied > realized
  persistently → selling wins, buying loses. Every profitable option sleeve we have is short-vol."
- [DATA] `COST_STANDARDS.md`: options round-trip cost ≈ brokerage (₹20×2) + STT 0.1% premium
  (sell side) + exchange txn ~0.035%×2 + 18% GST on those + slippage max(1 tick, 0.25% premium)/side
  for liquid ATM index options (2-3x that for thin days). This is the "vig" in every inequality below.

**The one honest question this roadmap answers:** the buyer pays theta + VRP + spread + costs
structurally. Direction-prediction cannot pay that tax — a correct-direction, wrong-magnitude bet
still loses. The only place a long-option trade wins is where **realized volatility over the
holding period systematically exceeds the volatility priced in at entry, by more than costs.**
Everything below is organized around finding — or ruling out — that gap.

---

## 1. The buyer's budget constraint (the gate every idea must pass)

For an option bought at DTE = T (calendar days), moneyness offset κ (0 = ATM; >0 = OTM in the
trade's direction), held for h ≤ T days, using the standard near-the-money approximation that ATM
option value ≈ 0.4 × S × σ × √(T/365) [INFERENCE — textbook BS approximation, not re-derived from
scratch here]:

```
REQUIRED MOVE (as % of spot) to break even ≳ 0.4 × IV_entry × √(h/365) × (1 + vig) + κ
```

where `vig` = round-trip cost & slippage load as a fraction of fair premium (empirically ~0.5–1.0x
of premium for liquid ATM index weeklies, per COST_STANDARDS — consistent with Arjun's measured
0.30–0.50% breakeven, so this is a decomposition check on his number, not a competing one).

Equivalently, and this is the reframing that matters:

```
BUYER WINS  ⟺  RV_realized(entry → exit) / IV_priced(entry)  >  1 + vig
```

**Direction does not appear in this inequality except as the sign multiplying delta.** A perfect
coin-flip direction call with realized/implied vol ratio > 1+vig still makes money; a 100%-accurate
direction call with RV/IV ≤ 1+vig still loses. This is why 17/17 indicator-triggered variants are
dead **regardless of hit rate** — MFE/MAE ≈ 1.00 means RV/IV was never systematically above 1 in
the tested windows, full stop. It is also why the research program below is NOT "find a better
indicator" — it is "find a state where RV/IV is systematically above 1+vig before the fact."

**Illustrative required-move table** (IV≈13%, a representative NIFTY level — [OPINION]/illustrative,
recalibrate against live `indices_close` India VIX before any real test; qualitative √T scaling is
the point, not the exact number):

| DTE (h=T, held to expiry) | Required move (0-vig) | Required move (vig=0.5) | What this says |
|---|---|---|---|
| 1 (0DTE/weekly Mon-Thu) | 0.27% | 0.41% | matches Arjun's measured 0.30–0.50% band almost exactly |
| 7 (full weekly) | 0.72% | 1.08% | ~65–100 pts on 9000-level spot |
| 30 (monthly) | 1.50% | 2.24% | a move NIFTY clears often — magnitude is not the monthly bottleneck |

The table itself contains the trend-catcher-vs-pulse answer: **short-DTE structures fail on
magnitude** (0.005% actual vs 0.3–0.5% required = 30–75x short, proven); **long-DTE structures
usually clear the magnitude bar easily** (2% moves in a month are common) but fail on
**predictability** — whether a trend filter can call the sign and persistence of that move ahead
of time. Two archetypes, two different failure modes, and therefore two different cheap tests.

---

## 2. Archetype formalization

### 2a. Why "trend catcher" and "bull pulse" need different DTE — the mechanism

An ATM option's time value decays as √(remaining time) — decay **accelerates** as expiry nears
(roughly a third of an option's remaining time value evaporates in its last ~1/9th of life; this
is the standard theta-acceleration curve, [INFERENCE]/textbook, not a firm-measured number).
Two consequences:

- **Near expiry (0–3 DTE):** theta bleed per day is severe in % terms, but premium is cheap in ₹
  terms and gamma is high — the payoff is maximally convex to a move **that happens right now**.
  This structure is a bet on an **impulse**: a big move inside a very short window. If the move
  doesn't arrive within roughly the holding window, theta erases the position before a slower
  trend could ever pay it back. → this is mechanically what "bull pulse" must be: short DTE,
  ATM/near-ATM, betting on speed not persistence.
- **Further from expiry (2–5 weeks):** theta bleed per day is small in % terms (you're paying for
  a large pool of remaining time value, but it drains slowly), gamma is low (today's wiggle barely
  moves the P&L), but delta accumulates as a trend develops over many days, and there is enough
  runway for a modest daily edge to compound into the illustrative-table's 1.5–2.5% required move.
  This structure is a bet on **persistence**, not speed. → this is "trend catcher": longer DTE,
  ATM-to-slightly-OTM (or, per the well-known "stock-replacement" convention, deep-ITM delta
  ~0.7–0.8 to minimize theta/vega drag at the cost of more capital per lot — worth costing out if
  this archetype survives its cheap test).

So the Principal's intuition is mechanically correct, and the reason is a **horizon-matching
problem between the shape of theta decay (front-loaded near expiry) and the shape of the move you
are trying to capture (instantaneous vs. cumulative).** Buying the wrong DTE for the archetype
means paying for convexity you don't need (long-DTE gamma is wasted on an impulse thesis) or not
buying enough duration to let a real trend outrun decay (short-DTE theta kills a trend thesis
before it can develop).

### 2b. The archetype table

| Archetype | Economic mechanism | Required move & horizon | Implied optimal DTE / moneyness | Falsifier | Cheapest test |
|---|---|---|---|---|---|
| **Trend Catcher** (bull/bear) | Ride a multi-day/week directional drift; delta accumulates faster than theta bleeds | ~1.5–2.5% cumulative over 2–4 weeks (magnitude usually clearable — see table) | 20–35 DTE monthly, enter with 3–5wk left, exit/roll by ~7–10 DTE (before theta-acceleration zone); ATM-to-slightly-OTM, or deep-ITM stock-replacement variant | Daily/weekly return autocorrelation conditioned on trend filters (ADX/DMA) ≈ 0, OR hit rate on directional continuation ≈ 50% (same failure mode already proven at intraday granularity — untested at daily/weekly) | Pure statistical persistence test on NIFTY spot/futures — no options, no P&L layer, reuses existing PIT panel + `lib/guards.py` |
| **Bull/Bear Pulse — indicator-triggered** | Capture a violent 1–2 day impulse via short-dated near-ATM options, harvesting gamma before decay | 0.3–0.5% intraday / ~1% over 2-3 days | 0–2 DTE weekly, ATM | **ALREADY FALSIFIED** — MFE/MAE≈1.00, hit rate ~50%, 17 trials across 2 studies (K-001 + this file's evidence) | N/A — nothing left to test on this branch; only path back in is K-001's resurrection condition (sniper entry, <5 trades/mo, net+ at 2x costs, fresh OOS window) |
| **Bull/Bear Pulse — event-triggered** | Same impulse-capture logic, but entry keyed to a scheduled information event (RBI/Budget/expiry) instead of a price/indicator pattern — the only source of a genuinely asymmetric (fat-tailed) move | 0.3–0.7% same-day around the event | 0–1 DTE at event date, ATM straddle-then-directionalize | Event-day MFE/MAE ≈ non-event MFE/MAE (no extra convexity around scheduled events), OR event IV already prices the realized move (RV/IV ≈ 1 on event days specifically) | Event-day MFE/MAE + RV/IV ratio vs. matched non-event days — same script/methodology as the killed EMA study, trigger swapped from indicator-cross to calendar date (`board_meetings_all.json` + macro calendar + existing NIFTY 1-min panel) |
| **Volatility Breakout Directional Long** | Buy directional exposure after a vol-compression regime, betting realized vol expands **faster than IV re-prices it** (the one archetype that directly targets inverse-VRP) | Needs forward RV/IV > 1+vig, not just RV expanding in absolute terms (RV expanding off a compressed base is close to tautological — mean reversion — and does NOT by itself imply the buyer wins if IV re-prices concurrently) | 1–3 weeks: long enough to survive the wait for compression to resolve without excess theta, short enough to cap loss if breakout never comes; ATM-to-near-ATM, direction confirmed only after breakout | Compression (low IV-percentile / low ATR-percentile) does NOT predict forward RV/IV > 1 — i.e., compression predicts RV expansion (probably true, mean reversion) but IV re-prices in step, preserving VRP | India VIX percentile-trough screen (`indices_close/indices_{yyyy}.parquet`, D-009 verified) → forward N-day realized vol from spot AND forward N-day ATM straddle P&L (existing NIFTY weekly options panel) — pure historical conditioning, no new data |
| **Gap-risk day long premium** | Weekend/holiday/pre-event overnight gaps may be underpriced by continuous-time IV annualization, which smooths over discrete-time tail risk | Realized overnight gap variance vs. the option-implied expected overnight variance, isolated to weekend/long-weekend/pre-event nights | Held overnight only, near-ATM strangle-ish structure entered Friday/pre-holiday close | Realized gap distribution matches (or is smaller than) implied overnight variance — no discrete-time premium exists | Friday-close implied overnight variance vs. realized Monday-gap variance, isolate long weekends & pre-event nights, using existing spot + option chain data |

---

## 3. Ranked research queue — cheapest/highest-information first, pre-registered kills

Ordering principle: pure-statistics tests on data already on disk, with **zero option P&L
computation**, come first — they can kill an archetype for a few minutes of compute before any
Gate-4 build is justified. Only a niche that survives its cheap test earns a full options-P&L
backtest.

| # | Test | Archetype it kills/confirms | Pre-registered kill criterion | Est. cost |
|---|---|---|---|---|
| **Q1** | Daily/weekly trend-persistence (autocorrelation + hit-rate conditioned on ADX/DMA filters) on NIFTY spot/futures | Trend Catcher | Autocorrelation not distinguishable from 0 at 95% CI, OR conditional hit-rate ≤ 53% (barely above coin-flip, indistinguishable from the intraday result) | Cheapest — pure stats, minutes |
| **Q2** | IV-percentile-trough → forward RV/IV ratio (India VIX + NIFTY realized vol, no option P&L yet) | Volatility Breakout Directional Long | Forward RV/IV_entry ≤ 1+vig in the compression-conditioned sample, i.e., IV re-prices concurrently with RV expansion (VRP preserved through the transition) | Cheap — vol-series stats only |
| **Q3** | Event-day MFE/MAE + RV/IV vs. matched non-event days (RBI/Budget/expiry/Fed-adjacent gap days) | Bull/Bear Pulse — event-triggered | Event-day MFE/MAE ≈ non-event MFE/MAE (≤1.05), OR event-day RV/IV ≤ 1+vig | Cheap — reuses killed-EMA-study script, swap trigger |
| **Q4** | Friday/pre-holiday implied overnight variance vs. realized gap variance | Gap-risk day long premium | Realized gap variance / implied overnight variance ≤ 1+vig, i.e., no discrete-time premium | Cheap — spot + chain data only |
| **Q5 (conditional)** | Full options-P&L Gate-4 build, ONLY for whichever of Q1–Q4 shows a surviving RV/IV or persistence edge beyond 1+vig with t≥2 | Whichever niche survives | Standard RESEARCH_SOP Gate-4/5 battery (DSR>0.95, PBO<25%, 2x-cost survival, no catastrophic regime slice) | Full backtest cost — only spent if earned |

**STOP rule (abandon option buying entirely, pivot to vol-selling side):** if Q1–Q4 ALL fail their
pre-registered kill criteria — which, given 17/17 prior trials dead, KB lesson 1 (VRP is the
meta-edge), and that Q1–Q4 are testing genuinely different mechanisms than what's already been
killed, is the base-rate expectation — then directional option BUYING is closed firm-wide as a
return-generating sleeve (not just K-001's narrower indicator-triggered branch), and this family
graduates to KILLED_IDEAS with the same discipline as K-001: a named resurrection condition (a
verified RV/IV > 1+vig regime discovered later, on fresh OOS data, not re-mined from this sample).
R&D's own time budget then moves fully to the pivot option in §6.

---

## 4. Honest priors (probability each survives its Q-test) — not inflated

| Archetype / test | My prior of clearing its cheap-test kill bar |
|---|---|
| Trend Catcher (Q1, daily/weekly persistence) | **~10%.** Index-level time-series momentum in a liquid, heavily-arbitraged benchmark has decades of thin, cost-fragile global evidence. Our OWN cross-sectional equity momentum (I-017) works — but that is stock-PICKING, a completely different mechanism from single-index time-series trend-following. The intraday version of "does an indicator cross predict continuation" already failed at 50.2–51.3% hit rate; there is no strong reason to expect daily/weekly to look structurally different, though the horizon is genuinely untested and deserves the cheap look. |
| Bull/Bear Pulse — indicator-triggered | **~2%.** Already dead on 17 trials, two independent studies, MFE/MAE≈1.00. Effectively closed; listed only for completeness. |
| Bull/Bear Pulse — event-triggered | **~15%.** Plausible mechanism (real information shocks are the one legitimate source of fat tails), but the firm's OWN prior work on event vol (the FF term-structure family, ~34 trials) found IV rich into scheduled events, not cheap — i.e., existing evidence points toward event-vol SELLERS winning, which is evidence against this niche for a buyer. Some chance a narrow sub-window (surprise-timing mismatch, not surprise-existence) still has an edge, hence not zero. |
| Volatility Breakout Directional Long | **~20–25%, the best prior in this roadmap.** It is the only archetype whose test explicitly conditions on IV being cheap AND separately checks whether RV subsequently outpaces the repriced IV (not just "vol expanded," which is close to tautological after compression). Still below even odds because IV typically re-prices concurrently during compression→expansion transitions (a well-documented stylized fact), and because the pattern is well-mined globally (crowding risk per KB lessons 45/47 on post-publication decay). |
| Gap-risk day long premium | **~10–15%.** Real mechanism (discrete-time gap risk vs. continuous-time IV annualization) but Indian index weekend/holiday gaps are historically modest and reasonably well anticipated by the market; needs the cheap empirical look before any confidence. |
| Bearish counterparts generally | **Structurally harder than the bullish mirror, not equal-and-opposite.** NIFTY puts typically carry a skew premium (downside strikes richer in IV than equidistant calls) — the budget-constraint inequality's IV_entry term is bigger for the same κ, so the required move is bigger. Partial offset: selloffs are faster/fatter-tailed (leverage effect raises realized vol asymmetrically). Net effect on the priors above: treat bearish variants as ~20–30% relatively worse odds than the bullish number in the same row, not identical. |

---

## 5. Direct answer: is "consistently profitable, month-by-month positive" achievable?

**No — not for a directional option-BUYING strategy, and building one that visually appears
"consistent" is the overfitting trap, not the goal.** Concretely:

- A trend-following long-option structure **whipsaws in range-bound/choppy months by
  construction** — that is not a bug to be tuned away, it is the mechanism: the same delta
  exposure that profits in a trend loses to theta+chop when the trend doesn't materialize. Any
  parameter search that eliminates red months is, by definition, fitting to the exact chop pattern
  of the sample rather than finding a mechanism (D-035: no silent assumptions, no fabricated
  smoothness).
- **We already have the smoking-gun example of this exact trap, from today's evidence, not a
  hypothetical**: the same EMA-cross futures signal showed **62.3% of months positive on GROSS
  P&L, but only 24.6% positive on NET P&L** (longest losing streak 14 months). A backtest that
  under-modelled costs, or that quoted gross returns, would have produced almost exactly the
  "consistent month-by-month positive" curve the mandate asks for — as a **pure artifact of
  omitted costs**, not a real property of the strategy. This is now a standing check I am
  registering for any future "consistent returns" ask: **demand the gross-vs-net monthly table
  before trusting the equity curve, always.**
- The realistic monthly win-rate distribution for an honestly-costed directional option-buying
  book, based on everything measured so far, is **lumpy and negatively skewed on the buy side**:
  most months mildly negative (theta bleed grinding), a minority of months strongly positive when
  a real trend or vol-expansion event lands, net expectation at or below zero unless a genuine
  RV/IV>1+vig niche is found (§2–4). This is the mirror image of the seller's book (mostly small
  positive months, rare large negative tail months) — consistency claims should be judged against
  which shape is actually being described.
- **Consistency IS achievable — on the vol-SELLING side**, which is exactly why KB lesson 1
  and the firm's entire validated options edge sit there (15–25% CAGR ceiling, Sharpe 0.9–1.2,
  KB lessons 24/45/47). If "consistent month-by-month positive" is the real requirement (as
  opposed to "participate in trend, defined risk, convex-ish payoff"), the honest recommendation
  is to not fight the VRP current at all — see §6.

---

## 6. The pivot option — presented fairly, with honest tradeoffs

If §3's queue comes back negative (my base-rate expectation), here is what still serves the
Principal's underlying intent — participate in trend, defined risk, convex-ish payoff — without
fighting the same structural tax:

| Structure | How it addresses the budget constraint | Honest tradeoff |
|---|---|---|
| **Debit spreads** (long call + short further-OTM call, same expiry) | Selling the far leg finances ~40–60% of the premium, cutting the theta/vig burden roughly proportionally — moves the required-move hurdle down | Caps upside at the short strike; still a net debit paying time value; still needs the SAME directional persistence question (Q1) answered favorably to have positive expectancy — cheaper insurance, not a new edge |
| **Ratio backspreads** (e.g., sell 1 near strike, buy 2 further OTM) | Can be entered near-zero or negative net premium — removes most of the theta tax entirely | Defined-but-real risk in the "trap" zone between strikes if the big move doesn't happen; still needs a genuine breakout/tail thesis (i.e., this is really the Volatility Breakout archetype's natural vehicle, not the Trend Catcher's) |
| **Trend-filtered vol SELLING** (e.g., sell puts with defined-risk spread structure when in an established uptrend; sell calls when in a downtrend) | Stays on the side of the proven edge (VRP) while attaching a directional/trend view for extra income tilt — literally the opposite polarity of "buying," dressed to still express a trend opinion | This is not "participating in the trend's upside" in the unlimited-convexity sense the Principal may be picturing — it is defined-risk INCOME with a trend-direction tilt, capped gains, tail risk on a sharp reversal against the trend. It is the closest thing to "consistent monthly positive" that is honestly achievable, because it inherits the seller's favorable RV<IV geometry instead of fighting it |

**My honest recommendation, if forced to rank:** trend-filtered vol selling is the only one of
these three that is not itself contingent on a niche this roadmap has not yet tested — it inherits
an edge the firm has already validated (VRP). Debit spreads and ratio backspreads are genuine
partial fixes to the budget constraint, but they only pay off if the underlying directional/vol
thesis (Q1/Q2 above) is actually true — they reduce the tax, they do not create the edge.

---

## 7. Pipeline / family-ledger notes (RESEARCH_SOP §7 plug-in)

- **New family, NOT a K-001 resurrection**, except one branch. K-001 = "directional intraday
  option buying keyed to price/indicator triggers, direction is the forecast target" — 17 trials,
  dead, resurrection condition already on file (sniper entry, <5 trades/mo, net+ at 2x costs).
  The niches in this roadmap (Q1, Q2, Q4, and the Trend Catcher branch) bet on a **different
  target — magnitude (RV vs IV), not direction** — and should carry their own trials ledger
  starting at zero, per RESEARCH_SOP DSR-honesty rules, so as not to understate K-001's honest
  kill count or overstate this family's.
- **The event-triggered Bull/Bear Pulse (Q3) is the one branch that inherits partial lineage**
  from K-001 (still an indicator/trigger-based intraday structure) — if it proceeds, log it as a
  K-001-family variant (trial #18), not a fresh-zero family, for DSR honesty.
- All five queue items (Q1–Q4, plus the conditional Q5) are currently **pre-1-INTAKE / staged for
  Gate-2 triage** — none have consumed a Gate-3 cheap-test slot yet. Recommend logging Q1–Q4 as
  four intake rows on the next `IDEA_PIPELINE.md` board update (I have not edited that file myself
  in this pass — this document is the one-pager input to that board entry, per RESEARCH_SOP's
  "no one-pager, no work" rule).
- Capacity/D-009/data-sourcing note: Q2 uses `indices_close/indices_{yyyy}.parquet` (India VIX,
  D-009 verified 2026-07-11) and the existing NIFTY weekly options panel — both already on disk,
  no new scraping needed. Q3 uses `board_meetings_all.json` + the macro calendar — already on disk.
  No Data Officer gate is triggered by anything in this queue; all four cheap tests run on data the
  firm already owns.

---

## Bottom line

The budget constraint is `RV_realized/IV_priced > 1+vig`, and it is direction-blind — this is why
17 direction-focused variants died identically regardless of hit rate. The Principal's DTE
intuition is mechanically correct (theta's front-loaded decay curve genuinely separates an
impulse-capture structure from a persistence-capture one), but correct mechanics do not by
themselves clear the inequality — that requires a genuine RV>IV niche, and the queue in §3 is the
cheapest possible path to finding one, if one exists. My honest expectation, given 17/17 trials
already dead and the firm's own VRP evidence, is that most of this queue also fails — the single
best remaining candidate is the Volatility Breakout archetype's IV-percentile-trough screen (Q2,
~20–25% prior), everything else is a longer shot. "Consistently positive months" from a directional
buying book is not a realistic target and chasing it invites the exact gross/net overfitting trap
already caught today; consistency, if that is truly the requirement, lives on the vol-selling side.
