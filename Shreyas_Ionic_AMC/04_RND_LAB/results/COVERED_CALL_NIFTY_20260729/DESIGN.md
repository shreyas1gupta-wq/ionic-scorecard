# NIFTY 50 Covered-Call / Overwriting Programme — Structuring Memo
**Owner:** Aakash Jain (Derivatives Structurer) | **Date:** 2026-07-29 | **Status:** DESIGN + first-pass illustrative backtest (NOT Gate-4 certified — no lookahead audit, no red-team, no sensitivity pass yet)

Data used (all real, no synthetic series): NIFTY 50 index daily `datasets/index_daily/nifty50.parquet` (2016-01→2026-07, [DATA]), India VIX `datasets/index_daily/india_vix.parquet` ([DATA]), NIFTYBEES ETF daily `datasets/etf_gold_silver/niftybees_daily.parquet` (2013-26, [DATA]), and **official NSE F&O index bhavcopy** `Shreyas_Ionic_AMC/05_DATA_OFFICE/data/fo_bhavcopy_hist/fo_idx_{2016..2026}.parquet` for real traded NIFTY CE closes ([DATA], catalog-verified complete 2011-2026). Costs per `06_TRADING_DESK/COST_STANDARDS.md` (APPROVED, D-021). Scripts: `covered_call_backtest_v1.py`, raw cycles in `cc_bhav_cycles.csv` (both this folder).

---

## 1. The contradiction, resolved

The brief describes a covered call ("long underlying + short call") but also says "unlimited loss after 2sd on upside." **A true 1:1 covered call cannot produce unlimited upside loss** — the short call's loss above strike is exactly offset, point for point, by the long holding's gain, up to a hard cap. Unlimited upside loss only exists if you are short MORE call notional than you hold long (a ratio write with a naked leg). So the brief's own risk description only makes sense under one specific reading of the ambiguous phrase "1/2 lot of underlying holding." I disambiguate three readings [INFERENCE — the brief does not specify which]:

| Reading | What it means | Upside risk |
|---|---|---|
| **(A) Partial overwrite** — "1/2" = write calls against only **half** the holding notional (e.g. hold 2 lots, sell 1 lot of calls) | Conservative; the uncovered half rides the full uptrend | **Capped on the written half, uncapped on the other half.** No naked risk anywhere. |
| **(B) Fixed lot count regardless of holding** — "1/2" = "sell 1 to 2 lots" as an absolute number, independent of what's actually held | If sold lots ever exceed held lots, the excess is a **naked short call** | **Unlimited on the excess (naked) lots** — this is what produces the Principal's "unlimited loss after 2sd" |
| **(C) Deliberate ratio write** (2 short calls per 1 long lot, a named strategy family) | Same mechanics as (B), but chosen on purpose, not by ambiguity | Same unbounded upside tail as (B), by design |

**Verdict: the Principal's own risk description (unlimited loss on the upside) can ONLY be produced by reading (B)/(C) — an over-written / partly-naked call sale.** That is almost certainly what "1/2 lot" was gesturing at, but it directly conflicts with the firm's capital-protection charter and with calling this a "covered" call at all. **I recommend reading (A) — never sell more call notional than is held, full stop** — as the only version of this programme I am willing to structure. Section 3 quantifies exactly what (B) costs in rupees so the Principal can see the price of the other reading with his own eyes, not just take my word for it.

This is the single most consequential design decision in this memo. A hard rule follows from it (§7).

---

## 2. Vehicle: how the underlying is actually held (the second thing the brief glosses over)

The brief assumes "5% margin requirement," which is only sensible for a **futures/leveraged holding**. A cash **NIFTYBEES ETF** holding requires 100% capital, no margin, no leverage — a structurally different economics.

| | Cash ETF (NIFTYBEES) | NIFTY futures @ Principal's 5% margin | NIFTY futures @ realistic ~12% SPAN [INFERENCE, no live SPAN file in repo — verify with Tara before sizing] |
|---|---|---|---|
| Capital for 1 lot (75 units @ ~₹24,271) | ₹18,20,314 | ₹91,016 | ₹2,18,438 |
| Effective leverage | 1.0x | **~20x** | **~8.3x** |
| A routine -1σ monthly move (-3.75%) costs | -₹68,262 (0.4% of capital) | -₹68,262 (**-75% of margin**) | -₹68,262 (-31% of margin) |
| A -2σ monthly move (-7.5%) costs | -₹1,36,523 (0.75% of capital) | -₹1,36,523 (**-150% of margin — wipes it out and goes negative**) | -₹1,36,523 (-62.5% of margin) |

**This is a second, independent "unlimited loss" mechanism the brief never names**: even a properly-covered (reading A) call write, if the *underlying itself* is held on 5% futures margin, turns an ordinary — not even tail — monthly move into a margin wipeout and forced liquidation. Leverage doesn't change the covered-call payoff *shape* (still capped/bounded in index points), but it changes the *probability of ruin* from "near zero" to "routine." **[OPINION]** A programme sold to the Principal as a conservative income overlay should not be quietly built on 20x leverage.

**Recommendation: hold the underlying as NIFTYBEES ETF (cash, unleveraged).** If the Principal specifically wants leveraged NIFTY exposure, that is a separate trading-line sizing decision under D-031/D-032 and RISK_LIMITS, requiring explicit sign-off — it should not be smuggled in via a "5% margin" assumption inside what is pitched as an income overlay. One caveat for fairness **[INFERENCE]**: SPAN gives real margin relief for a *bona fide covered* position, so "5%" might have meant the *incremental* margin for the short call on top of an already-held future, not 5% for the whole position — this reading is more defensible, but still requires a futures-based (leveraged) holding underneath, so §2's leverage table still applies to the underlying leg regardless.

---

## 3. The +2σ / +3σ upside shock table (the numbers behind §1)

Current snapshot [DATA, 2026-07-03]: NIFTY spot 24,270.85; India VIX ~11.8-13.6%; realized vol (20d) ~12.75% ann. Using 13% ann vol → monthly σ = 3.75%. Strike = spot × (1 + 1.0σ), rounded to nearest 50 = **25,200** (3.83% OTM). Black-Scholes premium at this strike ≈ **101 pts (0.41% of notional)**, delta ≈ **0.20** — this cross-checks almost exactly against the real backtested average premium of 0.41%/month (§6), which is reassuring: the model and the market agree.

**1 lot = 75 units.**

| Scenario | Spot | Interpretation A (1 lot held, 1 lot short — fully covered) | Interpretation B (1 lot held, 2 lots short — 1 lot naked) | Excess loss from over-writing |
|---|---|---|---|---|
| Entry | 24,271 | — | — | — |
| **+2σ** | 26,093 (+7.5%) | Long +₹1,36,625; call leg −₹59,397; **NET +₹77,228** | Long +₹1,36,625; call leg −₹1,18,794; **NET +₹17,831** | **−₹59,397** |
| **+3σ** | 27,003 (+11.3%) | Long +₹2,04,937; call leg −₹1,27,709; **NET +₹77,228 (identical to +2σ)** | Long +₹2,04,937; call leg −₹2,55,419; **NET −₹50,482** | **−₹1,27,709** |

Read that middle row twice: **Interpretation A's net P&L at +2σ and +3σ is the exact same number, ₹77,228.** That is the defining, physical property of a covered call — once the spot clears the strike, the position is flat/capped no matter how far it runs (P-01: max profit = (strike−spot₀)×lot + premium, a hard bound, full stop). **Interpretation B has no such floor on the loss side** — it goes from a shrunken gain (+₹17,831) at 2σ to an outright loss (−₹50,482) at 3σ, and every index point beyond that costs another ₹150 (2 lots × ₹75) with nothing offsetting it. That is the mechanism, in rupees, behind the Principal's "unlimited loss after 2sd."

*(Weekly-tenor footnote [INFERENCE]: at the same 13% ann vol, weekly σ ≈ 1.83% (13% × √(5/252)); a weekly 1σ strike would sit only ~1.8% OTM, with proportionally smaller shock rupee-amounts than the monthly table above but the same A-vs-B mechanism.)*

---

## 4. Is the "batman" (twin-peak / neutral) overlay appropriate here? **No.**

A batman payoff (double calendar, double butterfly, or call-ratio + put-ratio combination) is a **delta-neutral, pinned-range** structure — it makes money if the underlying sits still and loses if it moves far in *either* direction. The whole point of this programme is a **long-delta holding** (you own the index because you believe in its drift, and NIFTY has a strong positive historical drift — see §6). Stacking a neutral, range-betting structure on top of a directional long position does not "complement" it — **it fights it**:

- The put-side of a batman is a **short put** (or long put wing depending on construction) that either adds *more* downside exposure on top of an already-fully-exposed long holding (if short puts), or caps upside further via an extra call leg beyond the single call already discussed.
- It materially changes the **net delta profile** mid-holding in a way that's hard to reason about and harder to explain to an investor: you'd be running a directional-long book with a market-neutral overlay bolted onto it, which is neither a clean income overlay nor a clean neutral vol trade.
- Every historical mention I could find in this firm's own book of a "sell calls at market turns" idea (the `BOND_COLLAR_NIFTY` 2026-07-17 result) shows trend/regime-timed short options are the fragile part of these designs, not the robust part — adding a second, more complex neutral structure on top makes this *worse*, not better.

**Verdict: reject the batman overlay for this mandate.** [OPINION — structuring judgment] If the Principal wants a genuine range/neutral options book, that is a *separate, non-directional* sleeve (already covered by the firm's existing short-strangle/VRP-selling work, KNOWLEDGE_BASE lesson 24) — it should not be bolted onto a long-NIFTY holding whose entire purpose is to capture drift.

---

## 5. Recommended structure (exact rules)

**Vehicle:** NIFTYBEES ETF holding (cash, unleveraged) — see §2. Futures variant available only under explicit Principal/CIO sign-off on the leverage, sized under RISK_LIMITS, never silently.

**Tenor: Monthly**, not weekly. Reasoning: monthly gives ~4x fewer round-trips than weekly for the same notional exposure period → lower cumulative cost drag (COST_STANDARDS per-order + STT + slippage compound every roll) and lower whipsaw-from-adjustment risk, at the cost of slightly coarser theta capture and slower reaction to regime change. Given the firm's own VRP edge is modest (KB lesson 24: 15-25% CAGR ceiling for a *dedicated* short-vol sleeve, and this is a much smaller overlay on top of a directional holding — see §6), the lower-turnover monthly cadence is the better trade-off. [OPINION]

**Strike:** delta ≈ 0.20 call, equivalently spot × (1 + 1.0 × monthly-realized-σ), rounded to nearest 50. Re-derived fresh each cycle from trailing 20-day realized vol (not a fixed % — this keeps the strike distance vol-adaptive with a single parameter, k=1.0σ).

**Coverage rule (hard, non-negotiable):** short-call lots sold ≤ lots held, always. No ratio writes, no "1-2 lots regardless of holding." This is the direct fix for §1's ambiguity.

**Adjustment / roll rules (pre-specified, not discretionary):**
- If spot reaches or exceeds the strike with >5 trading days left to expiry → buy back the call and roll up to a new strike at spot×(1+1.0σ_remaining), same expiry (one roll per cycle, in the certified spec — the first-pass backtest below does NOT simulate this roll; see §7 gaps).
- At expiry−1 trading day: if the call is ITM, buy it back at that day's close (never let it exercise — avoids the STT-on-intrinsic-at-exercise trap per COST_STANDARDS). If OTM, let it expire worthless.
- Never trade on the expiry-day settlement price (landmine #9 — index options settle-price ≠ tradeable option price).

**Trend / overbought-oversold overlay (single indicator, two canonical thresholds — tiny parameter count, per the brief's own overfitting warning):** RSI-14 on the daily index close, at entry.
- RSI14 ≥ 70 (overbought) **or** RSI14 ≤ 30 (oversold) → **SKIP writing this cycle** (stay fully uncovered / long only).
- 30 < RSI14 < 70 → write normally at the vol-based strike.

*Why this exact form, and not something fancier:* I tested a first alternative (skip only in a "moderate uptrend, RSI 50-70" zone, keep writing when RSI≥70) modeled on a lesson from `BOND_COLLAR_NIFTY` (2026-07-17) that RSI>70 was the least-bad time to sell calls in a *net-short-bond* context. Transplanted onto a covered-call context it did NOT hold up — see §6. **The version above (skip both RSI tails, 30/70) is the one that survived first-pass real-data testing** without hurting the base case; the first version made things worse and I am flagging it explicitly as a rejected variant, not quietly dropping it. [DATA — see backtest]

---

## 6. First-pass backtest (real data, illustrative — NOT Gate-4 certified)

**Method:** 124 monthly cycles, 2016-04 → 2026-07 (10.25 years), NIFTY 50 index spot + real traded NIFTY CE closes from official NSE bhavcopy (`fo_idx_2016..2026.parquet`). 119/124 cycles had a liquid print at the target strike on both entry and exit day (5 skipped for no print — a genuine, reported liquidity gap, not smoothed over). Exit always on T-1 to expiry (never on settle). Costs per COST_STANDARDS (brokerage, STT, exchange txn, GST, stamp, 0.25% slippage floor both sides). **No intra-cycle roll simulated** in this first pass (documented simplification — the certified Gate-4 spec must add it, see §7).

Real-data cross-check: average realized strike distance 4.05% OTM, average premium collected 0.41% of notional/month — this matches the Black-Scholes model in §3 (0.41%, delta 0.20) almost exactly. Win rate (option leg keeps most of the premium) ≈ 80%.

| Variant | End NAV (1 lot start, ₹18.2L-equiv, 50% premium-sweep compounding) | CAGR | Cum. option P&L (10.25y) | ITM-at-exit rate | Cycle-level maxDD |
|---|---|---|---|---|---|
| **Buy & Hold (no calls)** | ₹18,20,314 | **11.83%** | — | — | −31.9% |
| **Always-write** (no overlay) | ₹18,10,663 | **11.77%** | **−₹1,13,393** | 20.2% (24/119) | −32.3% |
| **Overlay v1** (SMA-stack + mid-RSI skip, rejected) | ₹17,39,785 | **11.34%** | −₹1,39,218 | 23.8% (19/80) — *higher*, i.e. this filter selected for MORE capped months, not fewer | −33.6% |
| **Overlay v2** (skip both RSI tails, recommended §5) | ₹18,10,127 | **11.77%** | −₹83,141 | 21.2% (18/85) | −33.3% |

**Honest reading, stated plainly:**
1. **The covered call is a small net drag on total return in this 10-year window, not a source of extra return.** Cumulative option P&L is negative in every variant (−₹83k to −₹139k on a book that grew from ₹18.2L to ~₹18.1-1.8L). The premium collected does not fully pay for the upside given up. This directly confirms the brief's own warning: capped upside vs. India's positive equity drift is a real cost, and here it slightly exceeds the premium income.
2. **Neither overlay variant demonstrably improves on simply always-writing.** v1 is worse (both on CAGR and, backwards from its intent, on the ITM/capped-rate — it skipped the wrong months). v2 ties always-write on return with ~30% fewer trades (85 vs 119 executions) and slightly less negative option P&L, which is a modest transaction-cost/operational-simplicity win, **not** a return improvement. I am reporting this ties-not-beats result honestly rather than dressing it up as "optimized," per the brief's own instruction that this is where overfitting risk concentrates.
3. **Drawdown is NOT visibly cushioned by the call at monthly granularity** — maxDD is similar to or marginally worse than buy-and-hold across all variants. A small monthly premium does not meaningfully offset a sharp multi-month drawdown; the call simply expires worthless in a crash and contributes nothing to cushion it. Anyone pitching "covered calls reduce drawdown" should see this table first.
4. **Compounding mechanic, concretely:** under the 50%-premium-sweep rule, units grew from 75 → 87.7 (Always-write) over 10.25 years purely from reinvested option income (on top of any price appreciation) — the compounding "buy more, repeat" mechanic works exactly as specified, it's just compounding a small-to-negative income stream, not a large one.
5. **KNOWLEDGE_BASE lesson 24 context:** the 15-25% CAGR / Sharpe 0.9-1.2 ceiling in that lesson is for a *dedicated* NIFTY VRP-selling sleeve benchmarked against cash. This programme's benchmark is NOT cash — it's an already-~12%-CAGR long index holding. The two are not comparable, and this design should **never** be marketed as adding "up to 25% CAGR" on top of the holding — the honest expected range, per this backtest, is **roughly buy-and-hold CAGR ± 0.5pt**, i.e. essentially return-neutral with a small tilt determined by strike distance and regime, NOT a return-enhancer.

---

## 7. Pre-registered backtest spec (for Gate-4 certification, before any capital)

- **Universe/data:** NIFTY 50 index (index_daily/nifty50.parquet) + NIFTY OPTIDX CE from official bhavcopy (fo_bhavcopy_hist, 2016-2026, ~2.75M rows verified complete). ETF NAV cross-check via NIFTYBEES for tracking-error sanity.
- **Params (frozen, tiny count):** tenor=monthly; k=1.0σ strike offset; RSI 30/70 (canonical, not fit); sweep fraction f=50%; roll trigger = spot≥strike with >5 DTE remaining, one roll/cycle max.
- **Additions needed vs. the first pass above:** (a) simulate the intra-cycle roll-up rule (not done in first pass); (b) run interpretation-B (ratio write) as its own tracked variant through the full window to show the tail risk empirically, not just at two shock points; (c) extend to 2011-2016 using the same bhavcopy source (available, unused here) for a longer sample; (d) lookahead audit pass (`lib/lookahead_audit.py` + one-day-lag test) per D-028 before this touches a register row.
- **Kill criteria (pre-registered, per RESEARCH_SOP discipline):** ABANDON the programme if, after the additions above on the full available history —
  1. Cumulative option P&L drag exceeds **−1.5%/yr** against buy-and-hold (i.e., it's a materially worse way to hold NIFTY, not just a wash), OR
  2. The overlay (v2 or any refined version) cannot beat always-write's CAGR by at least its own added complexity/turnover cost on an out-of-sample split (else: run always-write, skip the "optimization"), OR
  3. maxDD with the programme running is **worse** than buy-and-hold by more than 2 points in any 3-year rolling window (the call should never make the ride worse, only the endpoint smoother) OR
  4. Reading-B economics (§3) ever appear in the actual order flow (audit trail must show short-call lots ≤ held lots at all times, no exceptions — a single breach is an automatic halt, not a warning).

---

## 8. What would make me abandon this design entirely [OPINION]

- If the Principal, after seeing §1-§3, still wants the over-written (reading B / ratio-write) version for the extra premium — I will not structure it under a "covered call" or "income overlay" label; it is a leveraged short-vol bet with unbounded upside tail risk and needs to go through the same IC/CIO tail-risk review as any other naked short-gamma structure, sized far smaller, with an explicit stop.
- If the underlying must be held on futures margin at anything near 5% (§2) — the leverage math alone (routine moves erasing the margin) makes this un-recommendable as currently briefed, independent of the options design. I'd need the Principal or CIO to explicitly accept 15-20x leverage on a NIFTY holding before touching this.
- If Gate-4 testing (§7) shows the drag exceeds the −1.5%/yr kill threshold, or the overlay can't be shown to add value out-of-sample — ship the plain always-write monthly design (or don't ship at all; buy-and-hold is a legitimate "verdict" here, not a failure to find something clever).
- If liquidity checks at trade time show the 0.20-delta monthly strike isn't reliably fillable at reasonable slippage (unlikely for NIFTY ATM-adjacent strikes per the firm's own bhavcopy note that "weekly-era monthlies trade ~16 strikes near ATM — fine for ATM studies," but must be re-verified live, not assumed from historical prints).

---

## Compact summary for the record

- **Resolved ambiguity:** "1/2 lot" should mean *partial coverage never exceeding held notional* (reading A). Reading B/C (fixed lot count regardless of holding, or deliberate ratio write) is what actually produces "unlimited loss after 2sd" — and is rejected.
- **Batman overlay:** does not belong here — it's a neutral structure fighting a directional long holding. Rejected.
- **Vehicle:** NIFTYBEES ETF (unleveraged) recommended over 5%-margin futures — the leverage implied by "5% margin" turns routine volatility into ruin risk, independent of the options structure.
- **Structure:** monthly, delta-0.20 (≈1σ) call, coverage ≤ holding always, roll-up trigger at breach, RSI 30/70 skip-both-tails overlay (v2), 50% premium sweep into more units each cycle.
- **Honest expected return:** roughly buy-and-hold CAGR ± 0.5pt — a small tilt, not a return-enhancer. 10.25-year real-data first pass: Buy&Hold 11.83% vs Always-write 11.77% vs best overlay 11.77% (tied) vs a rejected overlay variant 11.34% (worse).
- **Top 3 risks:** (1) the leverage-implied-by-margin-assumption risk is bigger than the options-structure risk if futures are used; (2) an accidental or deliberate over-write (reading B) reintroduces unbounded upside loss on the exact structure meant to be "safe"; (3) the trend/OB-OS overlay, as first specified, does not survive first-pass real-data testing (one variant actively hurt) — do not deploy an "optimized" overlay that hasn't cleared its own out-of-sample bar.
