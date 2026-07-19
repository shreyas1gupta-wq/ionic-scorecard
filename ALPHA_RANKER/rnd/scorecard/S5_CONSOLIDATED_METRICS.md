# S5 — Consolidated Cross-Scorecard Metrics (RELATIVE 1Y + 5Y)

**Owner:** Dr. Sameer Bhat (Overfit & Sensitivity). **Date:** 2026-07-18.
**Scope:** significance-reclassification sweep applied to the two NEW builds (S2 RELATIVE 1Y,
S3 RELATIVE 5Y) per `wave4/RESEARCH_QUEUE.md` Wave-C mandate. This is NOT a re-litigation of
wave4/5/6 — that sweep is already done, filed in `USABLE_ALPHA_INVENTORY.md` (F1). S1 (RELATIVE
1M) had not produced `S1_RELATIVE_1M_REPORT.md` at time of writing — **pending, fold in at S7
final assembly.** S4 (ABSOLUTE) likewise pending.

Sources read: `S2_RELATIVE_1Y_REPORT.md`, `S3_RELATIVE_5Y_REPORT.md`, `cards/S2_RELATIVE_1Y.json`,
`cards_S3_rel5Y/S3_REL5Y_SUMMARY.json`, `USABLE_ALPHA_INVENTORY.md` (cross-ref only — frozen
7-leg and forward-watch items there are a separate track, untouched by this sweep).

## Cross-scorecard table

| | **S2 — RELATIVE 1Y** | **S3 — RELATIVE 5Y** |
|---|---|---|
| Rank-IC (mean) | 0.084 | 0.079 (blend) |
| IC_IR | 0.63 | 1.59 (blend) |
| Decile Sharpe (LS, horizon-aware, net) | 0.137 ann. net-of-cost | +12.6%/yr net-of-cost |
| Decile monotonicity (Spearman) | 0.988 (strong) | 0.71 blend (sr_5Y 0.45 weak / abs_merit_5Y 0.93 strong) |
| Lag-test delta (hard gate <0.25) | 0.116 — **PASS** | 0.042 — **PASS** |
| Placebo IC (hard gate ±0.02) | −0.0014 — **PASS** | +0.0014 — **PASS** |
| DSR (advisory) | ~0 (global n_trials=702, deflated) | 0.89 blend (honest local n_trials=3) |
| PBO (advisory) | 0.926 — fails 0.5 | 0.926 — fails 0.5 |
| Independent-sample count | ~90 monthly obs ≈ **7–8 independent annual windows**, all post-2017 | 92 monthly obs ≈ **1.5 non-overlapping 5Y windows** over 2005–2020 |
| Verdict (this sweep) | **FRAGILE** | **FRAGILE** |
| Weakest assumption | `quality_cfo_pat` coverage CLIFF (median 1–4 names/date 2010–16 → 226+ from 2017-06-30) makes the gate a post-2017-only model in practice | Treating 92 overlapping 5Y-forward labels as independent trials; true n≈1.5 |
| FM-lens judgment | **Usable as sized forward-test input**, not a certified book. Logic sound, no leg redundant (drop-one moves IC_IR on every leg), hard gates clean — but "never tested through 2008/2011" is a real PM objection, not a stats artifact | **Usable, directionally**, with the 60/40 sr_5Y/abs_merit_5Y split defensible on era-stability grounds even though abs_merit_5Y monotonicity is the more reassuring number. A PM would want one more OOS window before full conviction |

Both hard gates (lag, placebo) are the program's sole kill criteria at this stage — both scorecards clear them cleanly. Per firm standing rule (low-t power-aware re-screen), DSR/PBO failure at this sample thinness is expected and disclosed, not disqualifying on its own.

## Firm standing-rule application (explicit, not rubber-stamped)

- Neither result is rejected for DSR/PBO alone. Neither is waved through as REAL either — both carry a genuine, named reason the sample is thin (S2: a discoverable data gap; S3: a structural property of the 5Y horizon that no bigger sample fixes within 20 years of data).
- Both would fail a mechanical PBO>0.5 kill rule; the harness's own mechanical verdict field on S2 reads `KILL (PBO 0.926>0.5)`. This report's FRAGILE call overrides that field per blueprint §2.4's advisory-only DSR/PBO rule — logged here so the override is traceable, not silent.

## Escalation items (flagged for Principal/CIO/Data-Officer, not silently resolved)

1. **S2 pre-2017 `quality_cfo_pat` coverage cliff — DATA-ASK, not a scorecard-invalidating flaw.**
   Verified root cause: `quality_QMJ` (not gated on cfo_pat) covers all 249 panel dates; `quality_cfo_pat`
   alone covers only 187 dates and is a strict subset. This is a genuine source-coverage fact, not a
   join bug. **Recommendation: route to Data Officer (Kavya Reddy)** — confirm whether a wider CFO/PAT
   panel exists pre-2017 that fell out of `capstone_legs.parquet`'s cache, or whether the underlying
   fundamentals source itself starts there. Until answered, treat S2 as an honest **post-2017 model**
   (~7–8 independent annual readings) — it does not invalidate the 1Y scorecard's logic, but it does
   cap how much can be claimed about its behavior in a 2008/2011-style bear market: **unknown, not
   tested, not assumed either way.**

2. **S3 growth-longevity drop-one anomaly — blueprint tension, Principal's/CIO's call, not this
   builder's or this report's to resolve.** The blueprint (§2.3) mandates a 2.0× overweight on
   growth-longevity at the 5Y horizon; as implemented (0.5·`composite_v2_confirmed` +
   0.5·`sub_op_persistent`, 82% coverage), dropping this leg *increases* IC in both limbs (sr_5Y
   0.083→0.120; abs_merit_5Y 0.052→0.084). Two live hypotheses, neither adjudicated here: (a) the
   construction is a noisy proxy for the intended "growth durability" concept and needs a cheap-test
   revisit, or (b) the leg earns its keep on a dimension drop-one/average-IC doesn't capture (tail-risk
   avoidance across the 5Y hold, not average-month IC). **S3's builder correctly did not unilaterally
   remove a blueprint-locked leg — this report affirms that restraint and forwards the tension
   unresolved.** No action taken on the leg; flagging only.

3. **S1/S4 not yet folded in** — this consolidation covers S2+S3 only; re-run/extend at S7 assembly
   once S1_RELATIVE_1M_REPORT.md and the S4 absolute-scorecard report land.

## Verdict summary for S7

Both S2 (RELATIVE 1Y) and S3 (RELATIVE 5Y): **FRAGILE** — no leakage evidence (hard gates clean),
sound underlying economic logic (FM-lens affirms both), genuinely thin independent-sample DSR/PBO
(expected/disclosed per firm rule, not a kill). Recommended disposition: **forward-test candidates**,
not certified books, with the two escalation items above carried forward rather than resolved by
substitution or override.
