# Scoping memo — FF term-structure signal, near-month-ONLY vehicle
_Aakash Jain (Structurer) + Arjun Rao (signal), 2026-07-07 · stage 1-INTAKE · NOT a K-012 resurrection · evidence: `results/S-03/20260705_resurrection/{CIO_RULING,RED_TEAM_FF_RESURRECTION,FILL_AUDIT_FF,CAUSAL_RETEST}.md`, KB lessons 14-18 (A.14-A.18 per CIO ruling)_

**This is vehicle design, not a backtest.** No P&L claimed below. Deliverable = recommended structure + pre-registration-ready spec for Arjun's Gate-3/4 build.

---

## 0. What's actually validated, restated precisely [DATA]

- The FF term-structure signal is **placebo-real**: FF≥0.25 book sits at the **100.0th percentile** vs both a turnover-matched AND a CE_be-(premium-)matched null (Nikhil, `RED_TEAM_FF_RESURRECTION.md`). Inverted FF flips sign to -4.76. This is real information, not an artifact of sizing or premium level.
- What killed K-012 was **not** the signal — it was that **59.3% of forward signals (122/199) fire into a back-(2nd-forward-)month CE leg with zero traded volume** (`FILL_AUDIT_FF.md` §3), and even mega-caps (APOLLOHOSP, SUNPHARMA, BRITANNIA, COLPAL) show **100% forward drop rate** on that specific leg. The front (near-month) leg is essentially never the problem: front-entry 90.3% NORMAL-liquidity / 5.2% untraded; front-exit 65.2% NORMAL + 32.5% THIN/THIN-ABRUPT (still fillable, just re-tiered) / 2.2% untraded. **Combined near-month fillability ≈95-98% on both legs.**
- Causal, D+1, gated, tiered-1x forward is **-0.03/Rs100** (Arjun, `CAUSAL_RETEST.md`, the pre-registered verdict) — i.e. once the vehicle is fixed to something fillable, this specific number no longer applies; it was measured on the calendar, not on any near-month-only structure. **We inherit the signal's validity, not any of K-012's P&L numbers.**
- Family trial ledger: ~34+ trials carried forward (CIO ruling §b) — DSR/PBO deferred until this vehicle shows a **positive raw forward edge**, per CIO's explicit instruction, not before.

## 1. The concrete design problem

Drop the back leg entirely → the structure needs to stand on the near-month expiry alone. Three candidates considered, per charter (liquidity honesty first, then payoff/margin shape).

---

## 2. Candidate A — Naked short near-month ATM call

**Legs/strikes/expiry:** SELL 1x near-month (M1) ATM CE, nearest strike to spot, same expiry the FF signal is computed on. No offsetting leg.

**Payoff [physical bound stated]:** Max profit = premium received (bound, per P-0x). **Max loss = undefined/unbounded** (stock can gap through any level; single-stock upside has no exchange-imposed cap). Breakeven = strike + premium. Greeks at entry: short delta ~-0.5 (ATM), short gamma, short vega, long theta — and **critically, zero offsetting vega/gamma anywhere** now that the back leg is gone. This is a strictly worse risk shape than the killed calendar was, not a better one: the calendar was at least *vega-neutral by design* (short front/long back); this is outright short-vol/short-gamma with no hedge at all.

**Margin/SPAN:** [INFERENCE, flag to Tara] Undefined-risk single-leg short option — same SPAN+exposure category COST_STANDARDS assigns short strangles (~12% notional), with **no netting benefit** a 2-leg strangle gets from offsetting CE/PE deltas. RISK_LIMITS' clean "1% of book equity, max-loss" sizing rule **does not apply** to an undefined-risk structure — it must instead be sized off a worst-case-MTM model (RISK_LIMITS §5: "undefined: worst-case MTM model, NOT premium"), which caps practical size hard and needs Ritika's sign-off, not mine.

**Liquidity check:** The ONE leg here is near-month ATM — per Tara's own audit this is the *good* leg (front-entry 90.3% NORMAL). **Liquidity was never this candidate's problem.** Its problem is risk shape.

**Cost stack:** COST_STANDARDS single-stock near-ATM slippage tier (0.5-1.5% premium, one leg only) — cheapest cost stack of the three by leg count, which is exactly why it's tempting and exactly why it's dangerous: cheap execution on an unbounded-loss structure is not a saving.

**Verdict: REJECTED on risk-shape, not liquidity.** Correlated with the entire S-01..S-04 short-vol book's existing tail (the CIO's own tail-risk language for the killed calendar — "short vol-of-term-structure... draw down TOGETHER in a vol spike" — applies with *more* force here since there's no hedge leg at all). This fails the charter's job before it fails any backtest: a defined-risk desk does not naked-short single-stock calls to harvest a term-structure signal when a capped alternative exists.

---

## 3. Candidate B — Near-month vertical (bear call spread): SELL ATM CE / BUY OTM CE, same expiry

**Legs/strikes/expiry:** SELL near-month ATM CE (as above) + BUY near-month OTM CE, **same expiry**, at a strike chosen by a liquidity-first rule (§5 below), not a fixed delta/% target. No second expiry anywhere in the structure — the entire back-month dependency the calendar needed is gone.

**Payoff [physical bound stated]:** Max profit = net credit received (bound). **Max loss = (strike width − net credit) — DEFINED and bounded.** This is the whole point of the leg: it converts an unbounded-risk structure into one that fits RISK_LIMITS' clean 1%-of-book-equity max-loss rule without needing a worst-case-MTM model. Breakeven = short strike + net credit. Greeks: still net short delta/gamma/vega near the money, but damped — the long call caps upside tail risk and returns *some* vega offset (smaller than the calendar's cross-tenor offset, since both legs now share the same expiry/IV surface point roughly).

**Margin/SPAN:** [INFERENCE, flag to Tara for an actual SPAN-calculator number] COST_STANDARDS already grants **calendars** "spread margin" treatment (materially below the ~12% naked/strangle notional proxy) precisely because a long leg caps the short leg's loss. A same-underlying, same-expiry vertical is the textbook case for spread-margin treatment under NSE/SEBI's peer-margin framework — if anything a *cleaner* case than a calendar's cross-expiry spread, since both legs price off the same IV surface point. **This should be a materially better margin-utilization vehicle than either the killed calendar or Candidate A** — but "should be" is not a number; Tara owns costs, this needs her SPAN read before it's sized.

**Liquidity check — this is where the real work is:**
- Short leg (near-month ATM): audited-liquid, per Tara's fill audit (as Candidate A).
- Long leg (near-month OTM, same expiry): **NOT the audited leg.** This is a genuinely different liquidity question from what killed K-012 — strike-distance-within-one-expiry, not cross-expiry tenor. I ran a quick spot-check (NOT a fill audit) on 6 large-cap names from the K-012 universe (APOLLOHOSP, SUNPHARMA, BRITANNIA, COLPAL, AUBANK, BOSCHLTD), most recent 3 expiries each, one mid-cycle day per expiry, CE volume by strike-distance-from-ATM:

  | Distance (strikes from ATM) | n obs | zero-volume rate | median volume |
  |---|---|---|---|
  | ATM | 18 | 0% | 118,175 |
  | 1 | 32 | 3.1% | 6,314 |
  | 2 | 33 | 3.0% | 31,050 |
  | 3 | 31 | 0% | 11,750 |
  | 4-5 | 62 | 3.2% | 17,938 |
  | 6-8 | 87 | 6.9% | 8,175 |
  | 9+ | 265 | **30.2%** | 150 |

  [DATA, spot-check only — n=6 mega-cap names, cross-sectional not FF-signal-day-conditioned, 1 day per expiry]. Reads as **encouraging**: liquidity degrades gradually out to ~8 strikes, then falls off a cliff beyond 9+. This is structurally different from the back-leg problem (which was ~60% dead *regardless* of distance, because it was a different expiry with no organic interest until near ITS OWN expiry) — same-expiry OTM strikes trade because of contemporaneous spread/hedging demand.

- **PRIOR-ART COLLISION I have to flag against my own recommendation:** K-009 (`KILLED_IDEAS.md`) killed "pre-bought both-wing hedges on FF calendars" for exactly this failure mode — "far-OTM single-stock wings unpriceable (stale prints → −883% artifact)" (also cited in COST_STANDARDS' slippage table: "far-OTM single-stock wings: treat as UNTRADEABLE"). Candidate B is **not** the same shape as K-009's wing (K-009 was a deep-OTM tail hedge on top of an already-2-expiry calendar; this is a moderate-distance, same-expiry hedge with no second tenor at all) — but the failure pattern rhymes closely enough that I will not wave it through on a 6-name spot-check. **This is the single biggest open item before Gate-4** (see §5, kill #1).

**Cost stack:** short leg at COST_STANDARDS single-stock near-ATM tier (0.5-1.5% premium); long hedge leg at the SAME tier **only if** it clears the ex-ante liquidity floor — if it doesn't, the signal is DROPPED for that name-day, never pushed out to a farther illiquid strike and priced at the "illiquid" 1-2% tier (that tier exists for genuinely tradeable-but-thin strikes, not for the UNTRADEABLE far-OTM bucket).

**Verdict: RECOMMENDED**, conditional on the hedge-leg liquidity floor holding up under a real fill audit (not my spot-check) — see pre-registration §5.

---

## 4. Candidate C — Strangle / put-side equivalent — checked, not recommended now

Task asked explicitly whether FF has a put-side reading. **Checked the code, not just the docs:** `dispersion_strategy.atm_iv_asof()` (used by `forward_factor_v2.py` for both `iv1` and `iv2`) hard-codes `_series(df, k, "CE")` — **the FF signal, as computed and as the ONLY thing Nikhil's 100th-percentile placebo battery validated, is derived purely from ATM CALL IV term structure.** The parquet does carry PE leg prices (`PE_fe/be/fx/bx` columns exist, because `forward_factor_v2.py`'s `pnl()` function supports a `sides=["CE","PE"]` double-calendar variant that was coded but never the one that reached the register/backtest), but there is **no put-side FF signal, validated or otherwise.**

By put-call parity it's *plausible* the same term-structure richness shows up in PE ATM IV — but plausible is not evidence, and treating it as equivalent would be reusing a validated 100th-percentile claim to justify an unvalidated structure, which is precisely the "denominator disease" pattern (KB lesson 8) the firm has been burned by three times already, just in a different disguise (signal-identity disease, not denominator disease). It would also add unaccounted trials to the ~34+ family ledger the CIO explicitly ordered carried honestly into the eventual DSR/PBO gate.

**Verdict: PARKED.** Not this memo's scope. If wanted, it is a **separate signal-validation project** (new placebo battery on PE ATM IV term-structure — Nikhil's job, not mine) before it is ever a vehicle question. Do not build a PE leg off the CE-validated FF number.

---

## 5. Recommendation + why the others lose

**Recommend Candidate B — near-month bear call vertical, liquidity-gated hedge strike — to Arjun for a pre-registered Gate-3/4 build.**

- **A loses on risk shape, not liquidity:** its single leg is the audited-good leg, but undefined loss + zero hedge + direct correlation with the book's existing short-vol tail is a governance non-starter under RISK_LIMITS and the CIO's own tail doctrine, independent of any backtest number.
- **C loses on evidence, not structure:** the FF signal was never measured on the put side; using it there launders validated evidence onto an unvalidated leg.
- **B is the only candidate that (i) needs no second expiry — the exact thing that killed K-012, (ii) fits RISK_LIMITS' defined-risk 1%-of-equity rule cleanly, (iii) should get spread-margin treatment analogous to what COST_STANDARDS already grants calendars, and (iv) has a liquidity profile (moderate same-expiry OTM distance) that is structurally different from the cross-expiry back-leg problem** — but it is NOT yet proven fillable at the rigor the back leg was tested at, and it rhymes with a prior firm kill (K-009) closely enough to demand the same audit discipline before anyone sizes it.

## 6. Pre-registration spec for Arjun (freeze before any code is written)

**Structure:** SELL near-month ATM CE / BUY near-month OTM CE, same expiry, same strike-selection universe as K-012 (large-cap gate: sym's first FF candidate pre-2024-01-01).

**Entry:** Causal earliest-FF-cross ≥ threshold (carry forward the causal fix from `ff_v3_causal.py` — **NOT** v2's argmax/peak-FF; lesson 16 (v1→v2 injected T9-class lookahead) applies verbatim here). Fill-timing convention (same-day-close vs D+1) **must be pre-registered before the run**, per lesson 17 — default to D+1 (conservative) with same-day-close only as a labeled EXPLORATORY rung that cannot enter the verdict.

**Hedge-strike selection rule (liquidity-first, not delta-first):** nearest OTM strike whose trailing-5-session median volume/OI clears the same floor Tara's fill audit used for the back leg ("standing OI or volume required," COST_STANDARDS), searched outward from ATM up to a max distance cap (start at 8 strikes / informed by §3's spot-check — Arjun/Tara to set the exact cap from the real data, not my 6-name sample). **If no strike clears the floor within the cap, DROP the signal for that name-day — never fall back to a farther, illiquid strike.**

**Exit:** both legs together, 2 sessions before front expiry — carried forward unchanged from K-012's convention, specifically to avoid ITM assignment and the 0.125%-of-intrinsic STT-on-exercise trap (COST_STANDARDS §Per-order charges) that a naive hold-to-expiry would walk into on the short leg.

**Sizing:** defined-risk max-loss = (strike width − net credit) × lots; ≤1% of book equity per position (RISK_LIMITS §clean defined-risk rule — no worst-case-MTM model needed, unlike Candidate A).

**Pre-registered kills (carry forward CIO's 5 verbatim + 3 new, structure-specific):**
1. [CIO-1, adapted] **Hedge-leg fwd drop-rate <20%** over 2 forward years, measured by Tara's exact fill-audit methodology (not my spot-check) on the FULL eligible universe on actual FF-signal days — this is the direct successor to the back-leg's 61% kill number, now asked of the new liquidity dimension.
2. [CIO-2] **Gate-vs-drop test mandatory** on the hedge leg (lesson 15: gating can admit weaker trades) — kill if ex-ante gating is net-negative to a naive drop rule.
3. [CIO-3] Causal entry, D+1 fills (or pre-registered same-day), tiered slippage — **forward per-Rs100 >0 at 1x AND survives 2x.**
4. [CIO-4] **Positive in-sample (BUILD) too** — no regime-carried-edge alibi.
5. [CIO-5] DSR/PBO on the full ~34+-trial FF family ledger **once** (2) shows a positive raw forward edge — not before (CIO ruling §b: correcting a ≤0 edge burns tokens for nothing).
6. [NEW-6] **Naked-vs-vertical comparison reported, not assumed:** run Candidate A's naked-call P&L (same entries/exits, worst-case-MTM sized at RISK_LIMITS' 1% cap) alongside B's — if A's raw edge is materially better net of what the hedge premium gives up, say so plainly; don't let "defined risk is safer" quietly stand in for "defined risk is the better trade." Risk-shape preference and edge-per-rupee are separate questions.
7. [NEW-7] **Signal-computability check, operational, before backtest:** FF still requires `iv2` (back-month ATM IV) to compute the term-structure factor even though the TRADE no longer touches that leg. `FILL_AUDIT_FF.md` §"Raw price/volume source" shows the bhavcopy-daily schema (Apr-2024→Aug-2025) carries theoretical settle prices even at zero volume — but per CLAUDE.md's own dual-schema landmine, the current live/HF-1-min schema (post-Aug-2025) may NOT carry that feature for untraded strikes. Route to Kavya/Arjun: confirm the FF factor is still computable on a representative recent sample of days/symbols under the CURRENT data feed before assuming "the signal keeps firing" — "near-month-only" removes the fill requirement on the back leg, it does not remove the signal's DATA dependency on it.
8. [NEW-8] Exercise/assignment guard: confirm the 2-session-before-expiry exit convention actually clears T+1/T+2 settlement risk on Indian single-stock (physically-settled) options; report any residual near-expiry ITM exposure and its 0.125%-of-intrinsic STT cost explicitly in the cost stack rather than letting it hide inside a "close positions" assumption.

**Not a Strategy Register row yet** — this stays in `04_RND_LAB/IDEA_PIPELINE.md` at 1-INTAKE until Arjun's Gate-3/4 build produces a real number; next available register slot is S-07 if/when it gets there.

---
**Tags:** [DATA] signal validation (Nikhil), fill-audit numbers (Tara), causal retest (Arjun) — all cited from source files. [INFERENCE] margin/SPAN reads (flagged explicitly for Tara's sign-off), the 6-name OTM liquidity spot-check (explicitly labeled non-audit-grade). [OPINION] the risk-shape rejection of Candidate A and the "don't launder onto PE" call on Candidate C — both defensible on firm doctrine cited inline, but they are structuring judgment calls, not measured numbers.
