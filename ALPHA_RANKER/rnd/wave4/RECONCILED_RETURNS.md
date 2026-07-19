# ALPHA_RANKER — Reconciled Deployable Returns (TCA reconciliation)
**Tara Singh (E-015, Execution & TCA) · 2026-07-17 · answers COMPLETENESS_CRITIC.md #1**
Tags: [DATA] on-disk fact/computed by the script below · [INFERENCE] my construction/judgment · [OPINION] my call.
Script: `rnd/wave4/reconcile_returns.py` (scratchpad copy run; logic described below, re-runnable).
Raw output: `rnd/wave4/reconcile_results.json`.

---

## BOTTOM LINE

The 6.6x spread (EY 1.95% vs 12.9%, composite 28.4%) is **not real disagreement — it is four different
things being called "the same number."** Once construction is held fixed (one panel, one universe filter,
one cost table, one horizon-aware annualization), EY-alone reconciles to **~10-15%/yr net-of-cost gross-side
edge**, NOT 2% and NOT 13% by coincidence of matching an old number — both quoted originals were each
individually broken in a different way (see map below). The critic's floor of "true edge ~2%/yr" does **not**
hold up under a consistent rebuild; FINAL_MODEL's own "~12% market-neutral" headline is much closer to what
a careful reconstruction actually produces for the **composite**, though every one of these numbers — old
and new — still carries the harness's own **KILL (PBO > 0.5)** verdict, which this memo does not and cannot
override (that is a DSR/PBO/overfitting question, not a costs/construction question — Overfit Analyst /
Red Team's lane, unresolved).

**Canonical deployable (my construction, 1Y horizon, full 21yr sample, net of APPROVED COST_STANDARDS at 1x):**
| | Gross | Net @1x cost | Net @2x cost (promotion-rule stress) |
|---|---:|---:|---:|
| **7-leg composite** | **17.4-17.7%/yr** | **15.3-15.6%/yr** | **13.2-13.5%/yr** |
| **EY alone** | **12.6-13.3%/yr** | **11.6-12.4%/yr** | **10.7-11.4%/yr** |
| Momentum alone (plain 12-1 resid) | 11.8-12.4%/yr | 9.6-10.1%/yr | 7.3-7.9%/yr |
| Trend/MA65-slope candidate (H002-family rep.) | 8.9%/yr | 5.2%/yr | **1.4%/yr** |

---

## 1. WHY THE QUOTED FIGURES DIFFER — definition map

Four numbers were on the table. Each maps to a DIFFERENT construction; none of the four is what I'd call
"the deployable number" as originally computed:

| Quoted figure | Source card | Panel | Universe | Cost/liquidity | Horizon-annualization | Verdict on the harness's own gate |
|---|---|---|---|---|---|---|
| EY **1.95%/yr** | `H046_ey_only_1Y` | `panel.parquet` — **short, recent window only** (751 syms, 2021-07→2026-07, **only 42 dates**) | no ADV/liquidity screen | flat blended cost, no microcap drop | correctly ×1 (already fixed) | **KILL, PBO=1.000** (perfect overfit signature — n_obs=42 is too thin for the CSCV split to find any OOS support at all) |
| EY **12.9%/yr** | `CAPSTONE_value_EY_1Y` | `panel_long.parquet` — full 21yr, **survivorship-UNCONTROLLED** (universe balloons to 783 avg names by 2020-25 vs true ~500-528) | no ADV/liquidity screen, no winsorization | flat blended cost | correctly ×1 (already fixed) | KILL, PBO=0.961 |
| Composite **28.4%/yr** | `CANONICAL_7LEG_1Y` | same survivorship-uncontrolled `panel_long.parquet` | same — no liquidity screen, no winsorization | flat blended cost | correctly ×1 (already fixed) | KILL, PBO=0.909 |
| FINAL_MODEL headline **"~12% market-neutral"** | `rnd/reports/FINAL_BACKTEST.md` (5a) | a **full trade-simulated equity curve** (position sizing, rebalance drift, compounding) — NOT a mean decile-spread statistic at all | unclear from FINAL_MODEL text whether liquidity-screened | applies the breadth/VIX exposure scalar (a SIZING overlay, absent from every card above) | genuine CAGR (equity-curve compounding, not decile-spread × 1) | not a harness card — different methodology entirely, not directly comparable to any row above |

**The ×12 annualization bug is NOT the residual driver post-fix** (HARNESS_FIX_NOTE already corrected it, and
all four numbers above already reflect the fix — I verified `net_LS_v2` in every case equals the old buggy
`ann_return_LS` divided by 12, exactly). What the fix did NOT touch and what actually drives the 6.6x EY gap:
1. **Different data window**: H046 sees only 2021-2026 (42 monthly obs, ~3.5 effective years of non-overlapping
   1Y windows) vs CAPSTONE's full 2005-2025. This is a genuine apples-to-oranges era mismatch, not a
   construction bug — but it was never disclosed as such when the two numbers were compared.
2. **Different universe hygiene**: `panel_long.parquet`'s "survivorship-uncontrolled" universe (documented in
   FINAL_MODEL §5-RISKOFFICE) still lets ~783 names into some cross-sections. [DATA] `fwd_ret_1Y_raw` on the
   PIT-corrected panel (`panel_pit.parquet`) ranges from **-98% to +2,501%** even after PIT-membership
   filtering; **before dropping micro-cap names it goes as high as +9,929%** on the raw (non-PIT) panel — a
   handful of thinly-traded, circuit-prone micro-cap prints (exactly the class flagged in my Lessons Learned:
   "mid/small-cap strangle tails are fatter... bhavcopy closes hide intraday gaps"). A MEAN-based decile
   long-short spread (which is what every card above computes) is not robust to these; a rank-based IC is
   (which is why IC_IR barely moved when PIT-filtering was applied, per FINAL_MODEL §5-RISKOFFICE, but the
   raw £-return decile spread did NOT get similarly checked before being quoted as "the money number").
3. **No liquidity/short-ability screen anywhere in the harness's decile machinery.** `_decile_stats` in
   `harness.py` (lines 418-446) puts every name that clears `min_names_per_date=20` into a decile bucket —
   including micro-caps that cannot realistically be shorted or filled at the sizes any of this would trade.
4. **No winsorization of the underlying `fwd_ret_1Y_raw` target anywhere** — a small number of stale/adjustment-
   artifact prints can dominate a decile MEAN even though they don't move the Spearman IC much.
Point 2+3 together (dropping the bottom-quintile mktcap tier from the eligible cross-section — my liquidity
policing gate) collapse the return range from **[-98%, +2,501%]** to **[-93%, +559%]** with winsorization on
top — i.e., the extreme prints are concentrated almost entirely in the micro-cap tier the firm's own charter
says can't be shorted anyway.

---

## 2. THE ONE CANONICAL CONSTRUCTION (what I actually computed)

Applied identically to composite + every leg + the one candidate, so the comparison is apples-to-apples:
1. **Panel**: `panel_pit.parquet` — PIT-membership-filtered (`NIFTY500_TICKER_2005_2025_Final.xlsx`
   nearest-prior snapshot), survivorship-free, 933 symbols after the corporate-action guard
   (`disc_event_in_window_1Y>0` rows dropped, 735 rows), 2005-04→2025-12, 249 monthly dates.
2. **Investable universe**: drop the bottom-quintile market-cap tier (micro-cap, same quantile method as
   `harness._mktcap_tier`) from BOTH the long and short leg entirely — 98,680 → 79,683 eligible rows. This is
   the liquidity-policing gate from my charter (≤10% ADV / ≤5% micro is a sizing rule; here I go further and
   simply exclude micro from the tradeable decile universe, since a systematic monthly decile short cannot
   reliably borrow/short a rotating basket of micro-caps at scale).
3. **Winsorization**: per-date clip of the tradeable target (`fwd_ret_1Y_raw`) at the 1st/99th percentile —
   kills residual stale-print artifacts without touching the rank statistic.
4. **Decile construction**: identical to `harness._decile_stats` — per-date decile on the factor rank, top-minus-
   bottom mean of the (winsorized) raw forward return. Min 20 names/date.
5. **Annualization**: `harness.annualize_ls_return()`, horizon-aware — for 1Y the label is already annual, so
   no `×12` (this was the bug; now correctly a no-op multiplier of 1.0 for 1Y).
6. **Costs**: `COST_STANDARDS.md` (STATUS: APPROVED, D-021) blended round-trip bps by realized tier mix in the
   eligible universe (large 43bps / mid 63bps / small 93bps RT — micro excluded, its 123bps never charged
   because the tier is excluded from trading, not because it's cheap) × realized top-decile turnover ×
   12 rebalances/yr. **1x is the approved-standard cost; 2x is the firm's own promotion-rule stress
   (COST_STANDARDS "must remain net-positive at 2× ALL of the above").**
7. **Turnover-driven cost realism carries real weight here**: the trend/MA65-slope candidate has the highest
   turnover (45.2%/month) of anything tested and is the ONLY row where 2x-cost stress nearly annihilates the
   edge (5.2% → 1.4%) — a direct empirical confirmation of Red Team's blind-spot #4 ("turnover/capacity/real
   fills on the rescued technicals... completely untested... most likely place a rescue evaporates live").

**What this construction does NOT do** (explicitly out of my lane, flagged so nobody mistakes silence for a
clean bill of health): sector/size-neutralize the long-short return itself (only IC_IR was checked for that,
per `concentration_check.md` — the tradeable decile-LS return could still carry a residual size tilt within
the surviving small/mid/large tiers, same class of distortion FINAL_MODEL itself flagged for the long-only
quintile CAGR); recompute DSR/PBO on this new construction (Overfit Analyst's instrument, not mine — every
card discussed here, old and new, independently fails the harness's own PBO>0.5 KILL gate); or test
orthogonality of the trend candidate against the composite's own MA65 leg (Red Team blind-spot #2 — this
candidate is not a "new" bet, it's already one of the frozen 7).

---

## 3. CANONICAL TABLE

All figures 1Y horizon, annualized, net of APPROVED COST_STANDARDS. "no-winsor" columns shown to disclose the
winsorization's own effect size (it is small — the liquidity/micro-cap drop does almost all the work).

| Factor | n periods | Gross | Cost @1x | **Net @1x** | Cost @2x | Net @2x | Turnover/mo |
|---|---:|---:|---:|---:|---:|---:|---:|
| 7-leg composite (winsorized) | 141 | 17.44% | 2.12% | **15.32%** | 4.24% | 13.20% | 25.5% |
| 7-leg composite (no winsor) | 141 | 17.70% | 2.12% | 15.58% | 4.24% | 13.46% | 25.5% |
| EY alone (winsorized) | 154 | 13.33% | 0.97% | **12.36%** | 1.93% | 11.40% | 11.6% |
| EY alone (no winsor) | 154 | 12.60% | 0.97% | 11.63% | 1.93% | 10.67% | 11.6% |
| Momentum alone, plain 12-1 resid (winsorized) | 221 | 11.81% | 2.25% | **9.57%** | 4.49% | 7.32% | 27.1% |
| Momentum alone (no winsor) | 221 | 12.39% | 2.25% | 10.14% | 4.49% | 7.89% | 27.1% |
| Trend/MA65-slope candidate (H002-family rep.) | 232 | 8.90% | 3.76% | **5.15%** | 7.51% | **1.39%** | 45.2% |

**Era split (decay check, same construction, split at 2020-01-01):**
| Factor | 2005-2020 net@1x | 2020-2025 net@1x | Direction |
|---|---:|---:|---|
| Composite | 16.90% | 13.12% | decaying (consistent w/ FINAL_MODEL's IC 0.190→0.111) but not collapsing |
| EY alone | 10.67% | **15.09%** | **not decaying** — actually stronger in the recent window (2022 value rotation, per FINAL_MODEL §5a bear-year note) |
| Momentum alone | 10.57% | 6.81% | decaying, consistent with momentum-crash literature |

The EY era-split result directly contradicts the idea that H046's 1.95% is "the honest recent-era number" —
on the SAME recent 2020-2025 window, my reconciled construction gives 15.09% net, not 2%. H046's number is not
a valid recent-era EY reading; it is a different, thinner, differently-sourced construction (`panel.parquet`,
751 symbols, only 42 dates, its own `bi.h046_ey` builder from a GARP-interaction worker script, not
`run_long_confirm`'s PIT fundamentals path) that happens to KILL at PBO=1.000 — i.e. it is the LEAST
statistically supported of the four original numbers, not the most conservative/trustworthy one.

---

## 4. VERDICT — SURVIVE/FAIL at 2x cost (COST_STANDARDS promotion rule)

| Factor | Net @2x | Verdict |
|---|---:|---|
| 7-leg composite | 13.20% | **SURVIVES 2x** (magnitude-only; PBO/DSR gate still fails independently — see caveat below) |
| EY alone | 11.40% | **SURVIVES 2x** |
| Momentum alone | 7.32% | **SURVIVES 2x** |
| Trend/MA65-slope candidate | 1.39% | **BARELY SURVIVES 2x — de facto FAIL for capacity/real-fill purposes** (this is exactly the highest-turnover, most fill-sensitive leg in the whole stack; a realistic slippage multiplier on thin days per COST_STANDARDS "Dynamic slippage" section, not modeled here, would plausibly push it negative) |

**Caveat that cannot be waived by a costs memo:** every card discussed here — old and newly reconciled alike
— independently carries the harness's own `verdict: KILL (PBO > 0.5)`. This memo answers "if the signal is
real, what would survive costs" — it does NOT answer "is the signal real." That is unchanged by anything
here: DSR ≈ 0, PBO 0.90-0.96 on ~13 independent years / 456+ trials, per FINAL_MODEL §5-RISKOFFICE and
COMPLETENESS_CRITIC #6. Costs surviving 2x is necessary, not sufficient.

---

## 5. CONFIRM/REFUTE THE TWO STANDING CLAIMS

- **Red Team's "true edge ~2%/yr EY-class" — REFUTED as stated.** The 1.95% figure it anchored on
  (`H046_ey_only_1Y`) is the least statistically supported of the four original numbers (PBO=1.000, n=42
  dates, a different panel/builder entirely), not a conservative floor. A consistent, liquidity-honest,
  PIT-correct, winsorized, cost-adjusted rebuild puts EY-alone at **~11-15%/yr net**, including in the exact
  recent-era window H046 claims to represent. The *qualitative* point Red Team was making — "don't trust the
  6.6x-inconsistent magnitude, EY is probably the modest end of the range" — was directionally right in
  spirit (EY-alone < composite in every construction I ran) but the specific "~2%" anchor does not survive
  a consistent rebuild.
- **FINAL_MODEL's "~12% market-neutral" — CONFIRMED as the right order of magnitude for the composite**,
  though for a different reason than FINAL_MODEL states: that number comes from a full equity-curve
  backtest with a sizing overlay, not from the decile-LS statistic quoted elsewhere in the same document. My
  independently-reconstructed decile-LS composite (15.3-15.6% net @1x, 13.2-13.5% @2x) lands close enough to
  corroborate the ~12% CAGR headline as a believable ballpark, not an inflated one.

---

## 6. PRE-REGISTRATION RECOMMENDATION — Dec-2026 forward-test grade

**Pre-register: the 7-leg composite's decile-LS return, net of APPROVED COST_STANDARDS at 1x, on the
PIT-investable universe (micro-cap dropped from both legs), monthly-rebalanced, 1Y-horizon-labeled forward
return, winsorized 1%/99% per date — i.e., exactly the construction in §2/§3 of this memo, applied
prospectively rather than in-sample.**

Why this one, not the others:
- It is the ONLY metric in the whole corpus that is simultaneously (a) horizon-aware annualized correctly,
  (b) liquidity-honest (no micro-cap short assumption), (c) PIT/survivorship-correct, (d) cost-adjusted from
  an APPROVED standard, and (e) outlier-robust. Every other quoted number in the corpus fails at least one of
  these five.
- **Grade against ~13-15%/yr net@1x as the in-sample expectation, not 2% and not 28%.** Both fantasy anchors
  should be retired from firm discourse. If the Dec-2026 forward result lands materially below ~5-7%/yr
  net, that is a genuine decay finding worth a post-mortem; if it lands near 13-15%, the in-sample number
  was honest; if it lands near or above 28%, something is still leaking.
- **Log the 2x-cost figure (13.2%) alongside the 1x figure at pre-registration time** — COST_STANDARDS'
  own promotion rule requires surviving 2x, and doing so retroactively after seeing the forward result would
  be exactly the kind of goalpost-moving RESEARCH_SOP forbids.
- This pre-registration is silent on PBO/DSR — that gate is separate, owned by Overfit Analyst/Red Team, and
  remains failed regardless of which return figure is used. A forward-test PASS on magnitude does not
  override a PBO KILL; both must clear before any capital conversation.

---

## Files
- Script (reproducible): `rnd/wave4/reconcile_returns.py` (also left in scratchpad for this session)
- Raw output: `rnd/wave4/reconcile_results.json`
- Inputs read: `rnd/panel/panel_pit.parquet`, `rnd/panel/canonical_7leg_pit_scores.parquet`,
  `rnd/panel/capstone_legs.parquet`, `rnd/lib/harness.py` (`_decile_stats`, `_turnover`, `_mktcap_tier`,
  `annualize_ls_return`, `_read_cost_standards_bps`), `rnd/run_long_confirm.py`
  (`build_mom_resid_12_1`, `load_all`), `Shreyas_Ionic_AMC/06_TRADING_DESK/COST_STANDARDS.md` (APPROVED).
- Cards cross-referenced: `rnd/cards/H046_ey_only_1Y.json`, `rnd/cards/CAPSTONE_value_EY_1Y.json`,
  `rnd/cards/CANONICAL_7LEG_1Y.json`, `rnd/cards/CANONICAL_7LEG_PIT_1Y.json`.
