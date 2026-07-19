# ALPHA_RANKER — Survivor Shortlist (v2-scored, cross-regime confirmed)
Owner: Dr. Sameer Bhat (Overfit & Sensitivity Analyst). Generated 2026-07-17 from
`pragmatic_score_v2.py` over `rnd/cards/*.json` (318 cards read, 312 OK).
Criteria (pre-registered, per task brief): lag+placebo GATE clean (lag_test_delta<=0.25,
|placebo_ic|<=0.02) AND signed_ic_ir>0.3 AND, where a LONG_ (21yr panel) counterpart
exists, that counterpart ALSO clears both bars. DSR/PBO are shown as ADVISORY only —
per CONSOLIDATION.md item 1, PBO is structurally near-saturated (~0.95-1.0) on this
monthly/overlapping-return sample and is a known firm decision to not hard-gate on it;
same caveat now applies to DSR after the per-family fix (large sweep families still
deflate hard, see harness section below — that is a CORRECT skepticism of a
"best-of-N-variants" pick, not a scoring bug).

## What changed in the scorer (rnd/pragmatic_score_v2.py, non-destructive — v1 untouched)
1. **DSR: per-family trial count, not global.** Global counter was 318 trials
   (`trials_counter.json.total_trials`) → crushed every card's DSR toward 0 regardless
   of that factor's own test history. Recomputed via new `harness.dsr_from_stats()`
   (refactored out of `compute_dsr`, same math, additive) using
   `trials_counter.json.by_family[<card's family>]`. Effect: single/few-trial hypotheses
   (H015 fcf_yield n=1, H043 beta_adj_mom n=1, H009 stage2 n=3) now show real DSR
   (0.05-1.0) instead of a blanket ~0. Large parameter-sweep families (H002 MA n=48,
   W2_ma n=56) still deflate near 0 — correctly so, that IS 48-56 correlated trials on
   one idea.
2. **Signed IC_IR.** `verdict()` in `lib/harness.py` kills on raw `ic_ir < 0.20`, which
   auto-kills any factor with a NEGATIVE economically-expected sign (low-vol, idio-vol,
   size, accruals, forensic-penalty — "high raw value -> LOW forward return" is the
   hypothesis). Confirmed on file: **H010 low-vol** (raw ic_ir=-0.324, was hard-KILLed)
   and **H028 size** (raw ic_ir=-1.447, was hard-KILLed) are in fact among the STRONGEST
   signals on the whole board once sign is respected. Expected sign sourced from
   `backlog.json`'s `sign` field (keyed by the H0xx family already stamped on the card),
   keyword fallback for wave-2 families (lowvol/idio_vol/size/accrual/etc. substring
   match). Long-short return legs are also flipped for negative-sign factors so
   `net_LS_v2` is a genuine tradeable number, not a sign-mismatched one.
3. **Horizon-aware annualization.** `evaluate()` multiplies `mean(ls_ret_raw)` by a
   hardcoded 12 regardless of horizon — correct for 1M (label is a 1-month return),
   **12x inflated for 1Y** (label is already a 1-year return), **60x inflated for 5Y**
   (label is a 5-year cumulative return, needs /5 not *12). Verified end-to-end on
   H014 earnings-yield 1Y: v1 card claimed 34.4% annual net LS return; the true number,
   recovering mean(ls_ret_raw)=v1/12=2.86% and re-annualizing by horizon, is **~2.0%
   net/yr** — a defensible value-premium magnitude, not the implausible 34%. Cost drag
   (turnover x cost_bps) is untouched: rebalance cadence is monthly for every horizon
   per RESEARCH_PROTOCOL S1, so *12 there was already correct.

Hard gates UNCHANGED (CONSOLIDATION item 6 — they work): lag_test_delta>0.25 or
|placebo_ic|>0.02 = FAIL_GATE, no exceptions.

## SURVIVORS — 1Y (cross-regime CONFIRMED on the 21yr panel via LONG_ cards)
| Family | What | 5yr-panel signed_IC_IR | 21yr-panel signed_IC_IR | net_LS_v2 (1Y, 5yr panel) | Verdict |
|---|---|---|---|---|---|
| H003 | Residual momentum 12-1 (FF-neutral) | 0.72 | 0.69 | +17.3%/yr | **ROBUST** (fragile-at: high-vol regime, see red-team) |
| H014 | Earnings yield (value) | 1.52 | 0.76 | +2.0%/yr | **ROBUST** (defensive: bear IC > bull IC, confirmed) |
| H001 | MA(65) trend — stack/slope/dist variants | 0.72-0.95 | 0.71-0.84 | +7-9%/yr | **ROBUST at 1Y**, stack-variant degrades at 5Y (see below) |
| H004 | Momentum-Sharpe / rank-band variants | 0.65-0.79 | 0.65-0.67 | +11-19%/yr | **ROBUST at 1Y**, weakens to CANDIDATE-only at 5Y |
| H009 | Weinstein stage-2 | 0.33 (5yr panel, PROMOTE*) | **-0.12 (21yr panel, sign FLIPS)** | +22% (5yr panel only) | **KILLED BY CROSS-CHECK** — bull-only 2021-26 artifact |

H009 is the textbook catch this cross-referencing exists for: PROMOTE* on the 5yr
(2021-26 bull-heavy) panel, but its raw IC_IR literally changes SIGN on the 21yr panel
(+0.191 short-panel-1Y -> -0.115 long-panel-5Y). Per this desk's own red-flag list
("edge sign-flips across halves = automatic Gate-4 FAIL"), H009 is OVERFIT, not
FRAGILE — it should stay in KILLED_IDEAS, not the pipeline.

## SURVIVORS — 5Y (21yr panel native; no separate short-panel cross-check exists)
| Family | What | signed_IC_IR | net_LS_v2 | Verdict |
|---|---|---|---|---|
| H014 | Earnings yield | 2.09 | +5.9%/yr | **ROBUST** — best 5Y risk-adjusted number on the board |
| H003 | Residual momentum 12-1 | 0.60 | +1.5%/yr | CANDIDATE — IC survives, edge thins post-cost at 5Y |
| H004 | Momentum-Sharpe / rank-band | 0.38-0.39 | +1.5-2.6%/yr | CANDIDATE — borderline, weakest of the 4 core legs at 5Y |
| H001-stack | MA stack(65) | 0.48 | **-8.7%** | WEAK — monotonicity flips negative (-0.33) at 5Y |
| H001-slope | MA slope(65) | 0.41 | ~0% (-0.4%) | WEAK — IC/mono hold, but turnover eats the whole edge at 5Y |
| W2_dcf_* | Reverse-DCF valuation gap (new wave-2) | 0.45-0.48 | +9.7-15.1% | PROMOTE* — no 21yr-vs-5yr cross-check possible yet (5Y is 21yr-panel-native); needs a genuine OOS confirmation pass before trusting the magnitude |

Confirms CONSOLIDATION's own note precisely: MA **slope** survives 5Y statistically
better than **stack**, but neither monetizes well net-of-cost at 5Y — this remains a
1Y model, 5Y is genuinely thin.

## SURVIVORS — 1M
No 21yr-panel (`LONG_`) cards exist for the 1M horizon at all (panel_long.parquet is
built for 1Y/5Y forward labels only per CONSOLIDATION's data-asset note) — so
**cross-regime confirmation is structurally impossible for 1M right now**, not a
finding of fragility. Gate-clean, signed_ic_ir>0.3 candidates on the 5yr panel only
(unconfirmed cross-regime):
| Family | signed_IC_IR | net_LS_v2 | Note |
|---|---|---|---|
| H014/H030/H046 (earnings yield, 3 near-duplicate cards) | 0.39 | +6.3%/yr | same value signal as the 1Y/5Y survivor, good sign |
| H029/H048 (momentum, raw) | 0.30 | +22.7%/yr | consistent with H003/H004 |
| COMPO (turnover-band rank-average composite) | 0.35-0.38 | +3.6-17.2%/yr | the firm's own "durable model" combination — directionally consistent with 1Y result |
| W2sector (peer-relative EY / residual momentum) | 0.32-0.41 | +3.6-23.7%/yr | sub-sector refinement, consistent with CONSOLIDATION's peer-relative lift note |

Action item for wave-3: build a 21yr 1M cube so this horizon can get the same
cross-regime confirmation the 1Y/5Y legs already have. Until then, 1M candidates are
UNCONFIRMED, not robust.

## Red-team pass on the top 5 (adversarial check = regime sub-split, already computed
and stored per-card — a causally-identifiable, lookahead-free split per CONSOLIDATION's
own regime-map methodology; genuinely independent of the IC/DSR/PBO machinery above)
1. **H003 residual momentum** — regime_breakdown IC by vol-regime: low-vol +0.13/+0.17,
   **high-vol -0.01 to -0.08 (NEGATIVE on all three of the short-panel, LONG-1Y, and
   LONG-5Y cards)**. Holds. **FRAGILE-AT(high-vol regime)** — classic momentum-crash
   signature, not new but now quantified on our own data. Does NOT invalidate the
   factor; it does mean naive full-position momentum needs a vol-regime overlay before
   sizing (matches CONSOLIDATION's wave-3 queue item).
2. **H014 earnings yield** — regime_breakdown by trend: bear 0.156-0.171 > bull
   0.042-0.097 on all three cards (short-panel, LONG-1Y, LONG-5Y). **Holds, no fragility
   found** — genuinely the countercyclical/defensive leg CONSOLIDATION claims it is.
3. **H001 MA(65)-stack** — 5Y sub-panel: decile monotonicity **flips sign** (0.90 at 1Y
   -> -0.33 at 5Y) even though raw IC stays weakly positive. **FRAGILE-AT(5Y horizon)**
   — the top-minus-bottom decile spread is not a stable ranking at 5Y; do not extend
   this leg past 1Y.
4. **H004 momentum-Sharpe** — same high-vol crash pattern as H003 (vol-regime IC
   -0.10 at 5Y) plus a 1Y->5Y IC_IR decay (0.79->0.39, PROMOTE*->CANDIDATE).
   **FRAGILE-AT(high-vol regime, long horizon)**.
5. **H009 stage-2** — already covered above: sign-flip across panels is disqualifying
   on its own; regime_breakdown adds that even within-panel its bear-regime IC is
   negative on both the 1Y (-0.008) and 5Y (+0.025, near-zero) long-panel cards — there
   is no regime where this factor is convincingly positive outside 2021-26. **OVERFIT,
   confirmed killed.**

## Bottom line
Only **H003 (momentum), H014 (value/EY), H001 (MA-trend, 1Y only)** clear every bar:
gate-clean, signed_ic_ir>0.3, AND hold sign+magnitude on the independent 21yr panel.
H004 is a weaker fourth (1Y only). H009 is a confirmed false-promote the cross-panel
check correctly kills. H010 (low-vol) and H028 (size) are newly-recovered, previously
mis-killed candidates from the signed-IC_IR fix — no 21yr LONG_ card exists yet for
either, so they are 5yr-panel-only CANDIDATES pending a long-panel run, not yet
survivors. Do not adopt anything here without the pending red-team full pass +
IC memo per CONSOLIDATION's ADOPTION GATE — this is a scoring/sensitivity pass, not
a certification.
