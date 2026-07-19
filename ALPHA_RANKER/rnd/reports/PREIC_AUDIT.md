# PRE-IC ADVERSARIAL BATTERY — ALPHA_RANKER final composite
Owner: Dr. Sameer Bhat (Overfit & Sensitivity Analyst, E-027). Run 2026-07-17. Targets `rnd/FINAL_MODEL.md`
(the 7-leg 1Y composite), harness `rnd/lib/harness.py`, panel `rnd/panel/panel_long.parquet` (2005-04→2025-12,
969 symbols, 249 monthly dates). Scripts: `rnd/lib/sameer_preic_audit.py` (+`_audit2.py` supplementary pass).
Raw numbers: `rnd/reports/PREIC_AUDIT_results.json`, card `rnd/cards/AUDIT_TRUE7_1Y.json`.

## 0. HEADLINE FINDING — the number in FINAL_MODEL.md is not the composite it describes [DATA]
`FINAL_MODEL.md` S2 headline ("IC_IR ~0.91, monotonicity 0.98, lag clean") is quoted from
`cards/CAPSTONE_COMPO_1Y_final.json`. Traced that card's construction in `rnd/lib/run_capstone.py`
`COMPOSITES["COMPO_1Y_final"]` = **`["mom_resid_peer", "trend_ma65_slope", "value_EY", "value_smallcap_M2"]`**
— a 4-leg mix, NOT the 7-leg stack the document narrates (EY+PLAIN mom+MA65+QMJ+issuance+asset-growth+CFO/PAT).
Two concrete bugs in that 4-leg mix, both **already disclosed as wrong by FINAL_MODEL.md's own text**, just
never propagated to the actual card:
- Uses `mom_resid_peer` (sub-sector peer-relative momentum, IC_IR 0.552 on 21yr), the variant the document
  itself says is inferior/reversed vs PLAIN (IC_IR 0.688, `cards/LONG_H003_mom121_resid_1Y.json`) — "the earlier
  peer-relative>plain... was a 5yr-BULL-PANEL ARTIFACT, reversed on full history. Use plain" (FINAL_MODEL.md L14).
- Includes `value_smallcap_M2`, a leg the orthogonality writeup names as absorbed by EY (corr 0.94-1.00) and
  says should be dropped, while **excluding** QMJ, net-issuance, asset-growth and CFO/PAT — the four legs whose
  incremental value was actually leave-one-out tested (`reports/incremental_value.csv`, BASE4=EY+mom_resid_peer
  +MA65+QMJ, itself ALSO built on peer-relative not PLAIN).
The true 7-leg, PLAIN-momentum composite had **never been assembled as one card**. Built + evaluated it fresh
(`AUDIT_TRUE7_1Y`, 1 new honest trial, disclosed): **IC_IR 1.356 (vs 0.908 shipped), monotonicity 0.9999 (vs
0.976), regime IC bear 0.165/bull 0.207/sideways 0.167 (vs shipped bear 0.037/bull 0.118 — much less bull-skew)**.
The correction is directionally GOOD NEWS (true composite is stronger, not weaker) but every number currently
in FINAL_MODEL.md's headline paragraph must be replaced before an IC memo cites them — right now the memo would
be citing an artifact of a different, inferior, undocumented construction.

## 1. Parameter surface / perturbation (on the corrected TRUE7 composite)
| Perturbation | IC_IR range | Verdict |
|---|---|---|
| Leg-weight tilts (5: 2x-EY, 2x-mom, 2x-quality-block, 2x-BS-block, drop-weakest) | 1.52–1.93 (baseline 1.36 equal-wt) | PLATEAU — no cell >20% below neighborhood, all higher than equal-weight |
| Decile vs quintile portfolios | IC unaffected; ann_LS 3.81 (decile) vs 2.93 (quintile), as expected from a wider band | PASS |
| Rebalance offset ±1/±2 months (finer week-level shift NOT testable — panel is monthly-granularity only, disclosed gap) | 1.22–2.30, no sign flip | PASS, asymmetric magnitude noted not explained — flag for record |
| Universe drop-random-20% (5 seeds) | 1.58–1.77 | PASS, tight band |
| Drop-each-sector-once (22 sectors) | 1.28–1.80; Financial Services removal *raises* IC_IR to 1.55 | PASS — no sector is load-bearing |
**No knife-edge dependency found anywhere in construction/portfolio-formation space.** This is the one clean
pass in this audit.

## 2. Subsample / era stability — real concentration issue [DATA]
| Era | n_dates | median names/date | IC_mean | IC_IR | Trust |
|---|---|---|---|---|---|
| 2005-10 | 32 | **3** (max 5) | NaN — 0/32 months clear the 20-name minimum | — | EMPTY, not thin |
| 2010-15 | 60 | **17** (range 5→514, huge ramp mid-window) | 0.368 | 1.82 | LOW — dominated by its high-coverage tail, not a real 5yr result |
| 2015-20 | 60 | 578 (full panel) | 0.190 | 3.76 | Trustworthy |
| 2020-25 | 59 | 722 (full panel) | 0.111 | 1.24 | Trustworthy |
The "21-yr, cross-regime-validated" framing in FINAL_MODEL.md/CONSOLIDATION.md is **not true of this specific
7-leg composite** — 4 of 7 legs are fundamentals-based and PIT fundamentals coverage is essentially zero before
2010 (matches the known landmine: CURRENT_STATE.md 2026-07-13, "PIT coverage ~zero pre-2020"). The only two
eras with genuinely comparable full-panel coverage (2015-20 vs 2020-25) show **IC_mean nearly halving** —
real decay/crowding, not proven safe. Era-concentration disclosure required in the IC memo.

## 3. DSR / PBO — currently uninformative, not a valid gate at this data scale [INFERENCE]
Checked whether PBO/DSR discriminate real signal from noise by running every CAPSTONE leg card, incl. the
anchor EY (bear-defensive, "no fragility" per red-team) and the already-known-dead seasonality (IC_IR -0.014):
**every single leg — good or dead — returns PBO 0.85–1.00 and DSR ≈ 0.** `AUDIT_TRUE7_1Y` (the corrected,
perturbation-robust composite) also gets `KILL (PBO 0.931 > 0.5)`. Re-deflated DSR at assumed honest-trial
counts N=1/5/10/20/50/100/300/454 (`dsr_from_stats`, sr_hat=0.856, skew=1.24, kurt=8.17, n_obs=145): DSR=1.0
only at N=1, **already ≈0.0002 at N=5, flat 0.0 by N=10**. This is NOT primarily a global-trial-count artifact
(CONSOLIDATION.md's stated diagnosis) — it collapses even under an implausibly generous N=5-10 assumption,
given this series' skew/kurtosis and the harness's disclosed harsh `sigma_SR=1` approximation.
**CONSOLIDATION.md already downgraded PBO to "advisory only, never a hard kill" and flagged DSR's global-N as
a known bug — but that downgrade was a quant-desk self-declaration, not a Sameer/CIO-signed Gate-4 ruling.**
Per my charter (DSR/PBO production owner, purgedcv replacement pending — adoption queue item 1, still not
run), I am NOT signing DSR/PBO as either PASS or FAIL today. The metric currently has zero discriminating
power at this n_obs/skew/kurtosis combination — it must be replaced with the already-pip-installed `purgedcv`
package before Gate-4 can honestly claim DSR>0.95/PBO<25% either way.

## 4. Lookahead — spot-checks clean, formal T1-T10 battery NOT yet run [DATA]/[gap]
Per-leg `lag_test_delta`: all <0.1 (clean, <0.25 threshold) except seasonality (already correctly KILLed via
IC_IR/lag independently). Composite lag_test_delta 0.059–0.077, clean. EY uses `merge_asof(direction=
'backward')` on `available_date` (PIT-safe). Momentum window is `loc-251:loc-20` (skip-month, no lookahead
into the return window). Breadth exposure overlay (`%>200DMA`) uses trailing `rolling(200)` + `reindex(...,
method='ffill')` — causal. **However**: `04_RND_LAB/lib/lookahead_audit.py` / the T1-T10 checklist
(`07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md`) has never been run against ALPHA_RANKER specifically — no
`LOOKAHEAD_AUDIT.md` exists for this composite. Today's finding is "no leakage found in spot-checks," not a
completed, signed D-028 audit. Must run before Gate-4 sign-off.

## 5. Verdict
**FRAGILE-AT(headline-artifact, DSR/PBO-uninformative, era-coverage) — NOT YET GATE-4 CERTIFIABLE.**
Construction/portfolio-formation is genuinely ROBUST (section 1 — real good news, not manufactured). But:
(a) the number currently in FINAL_MODEL.md is drawn from the wrong 4-leg artifact, not the 7-leg model —
easy fix, re-cite `AUDIT_TRUE7_1Y` (IC_IR 1.356, mono 0.9999); (b) DSR/PBO as wired cannot certify OR kill
anything at this data scale — re-run via purgedcv before either claim; (c) "21-yr cross-regime-validated" is
overstated for this composite — real trustworthy history is 2015-2025 (10yr) and IC_mean nearly halved across
its two comparable eras, which must be disclosed, not smoothed over, in the IC memo.
**Single most fragile assumption for the IC memo to correct: the "21-yr" framing.** Everything else (weights,
bands, offset, universe, sector) held up under stress; the era-coverage claim did not.
