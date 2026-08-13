# FLEXICAP — QFRA-1 + QFRA-2, as-of 2026-07-31 (OUT-OF-CYCLE monitoring run)
Run 2026-08-11 (DESK-100). Recommendation-of-record cadence remains Apr/Oct-end (next: Oct-end 2026).
Builder: `05_DATA_OFFICE/scripts/qfra1_asof_jul2026_flexi.py` (stages A–E, checkpointed in this folder).

## QFRA-1 (short-term capture overlay) — anchor 2026-07-31, 37 Reg-G funds, NIFTY 500 (PRI)
First-ever out-of-cycle anchor advance past the workbook's 2025-01-31 data cut (runbook in qfra1-rerun skill).

**BUY (2):**
| rank | fund | FN (6M downside cap) | HC (total cap) |
|---|---|---|---|
| 1 | Quant Flexi Cap Fund(G) | 0.843 | 1.296 |
| 3 | Navi Flexi Cap Fund-Reg(G) | 0.967 | 1.185 |

Rank 2 (Invesco India Flexi Cap, HC 1.201) excluded by the FN>1.0 downside filter (FN 1.015) — rank-stealing by design. ICICI Pru Flexicap rank 4 (just missed).

**SELL (10):** Canara Rob (−0.80%), Franklin India Flexi Cap (−3.60%), Mahindra Manulife (−3.39%), Nippon India (−0.38%), NJ (−3.06%), **Parag Parikh (−3.12%)**, Samco (−9.56%), SBI (−1.61%), Shriram (−2.32%), Tata (−3.67%). (CJ trailing-12M excess vs NIFTY 500 PRI; PK=4.)
**HOLD: 25.** All 37 funds eligible (full 6M window enforced; none under the 7-month No-View floor).

Vs the stale 2025-01-31 anchor: TRUSTMF and Parag Parikh were the BUYs then — TRUSTMF is now HOLD, **Parag Parikh flipped BUY→SELL**. Navi flipped SELL→BUY. 18 months of drift; this is why the anchor advance mattered.

## QFRA-2 (frozen engine) — panel truncated at 2026-07-31, point-in-time
Panel refreshed to 2026-08-10 by the repo's own `resolve_codes.py` (corr-verified ≥0.98, 0 funds dropped, backup in `data/_backup_pre_jul31_20260811/`; full panels in `data/_full_20260810/`), then truncated ≤2026-07-31 for the run (same PIT pattern as `recommend_asof.py`). Config/scoring untouched.

**FLEXI final-2 CHANGED vs the 2026-06-29 run (flag per skill):**
| rank | fund | QFRA | CALIBRE | SENTINEL | conviction |
|---|---|---|---|---|---|
| 1 | HDFC Flexi Cap Fund(G) | 100 | A | clear | High |
| 2 | **Aditya Birla SL Flexi Cap Fund(G)** (NEW — in) | 83 | A | clear | High |
| 3 | Kotak Flexicap Fund(G) (was rank 1 — out) | 67 | B | flagged(1) | Medium |
| 4 | Quant Flexi Cap Fund(G) | 50 | B | flagged(1) | Medium |
| 5 | Franklin India Flexi Cap Fund(G) | 33 | C | flagged(1) | Low/Index-lean |

ICICI Pru Flexicap dropped out of the published top-5 (was rank 3 in May). All other categories' final-2 unchanged. Raw re-rank only — the τ-hysteresis churn adjudication belongs to the Oct-end run of record.

## Merged (ORIGINATE-AND-VETO, D-2026-08-04 ruling)
- Franklin India Flexi Cap: QFRA-1 Sell + QFRA-2 grade C (no veto) → **SELL**.
- Other 9 QFRA-1 Sells: no QFRA-2 Direct-universe coverage → **SELL, SINGLE-FRAMEWORK → FM sign-off required**.
- Quant Flexi Cap: QFRA-1 BUY (rank 1) + QFRA-2 rank 4/B flagged(1) — aligned enough short-term, mid-pack long-term; no contradiction fired.
- No QFRA-1 Sell landed on an A/B grade → zero contradictions.

## Caveats
1. QFRA-1 benchmark is **PRI** (TRI fix queued, NEXT_WEEK_QUEUE) → CJ flattered ~1.2–1.5%/yr → **SELL list understated**; Nippon (−0.38%) and several small-positive HOLDs would worsen under TRI.
2. QFRA-1 leg is a side-store replication (workbook read-only, untouched): funds value-matched at 30/31-Jan-2025 AMFI NAVs (27 exact, 10 Growth-vs-IDCW tie-breaks on NAV-identical twins), daily NAVs from mfapi.in, benchmark = FACTOR_NAVS + NSE ind_close_all 27–31 Jul (D-009 overlap check 2026-07-24: exact to the paisa). Grid effects vs a true workbook extension are possible at the margin.
3. QFRA-2 focused/value categories still run on the 2026-05-27 panel — `resolve_codes.py` predates those categories (KeyError 'focused'); flagged for the ops queue.
4. `factors_live` ends 2026-06-18 (enrichment ON but ~6 weeks stale at the Jul-31 as-of).
