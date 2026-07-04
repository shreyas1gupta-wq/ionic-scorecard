# S-04 LOOKAHEAD AUDIT — D-028 (Gate-4 mandatory)

**VERDICT: PASS-WITH-FLAGS** — 0 FAIL findings; 4 WARN flags (W1-W4 below). Backtest results are quotable; flags route to the paper desk and the monthly decay cadence. No quarantine.

**Date:** 2026-07-04 | **Auditor:** Dr. Sameer Bhat (E-027), owner of LOOKAHEAD_CONTROLS (D-028)
**Audited pipelines:** `results/S-04/20260704_cost_cert/cost_cert.py` and `results/S-04/20260704_sensitivity/sensitivity_S04.py`, plus their shared upstream (`intraday_options_strategy/buying/shortlist_shortvol.py`, `dispersion_strategy.py`) — the upstream is where fills and settlements are actually computed, so it is in scope.
**Battery:** `lib/lookahead_audit.py` `audit_code()` on all four files + manual T1-T10 walk per `07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md`.

## 1. Programmatic scan (audit_code)
**0 FAIL, 27 WARN across the four files.** Every WARN is the T6 heuristic firing on `.mean()/.std()` — all 27 are *reporting aggregations of realized P&L* (edge means, hit rates, summary stats), not feature normalization. There are no features in this strategy (unconditional calendar entry), no `.shift(-)`, no `bfill`, no full-sample scalers, no shuffled splits. All 27 dispositioned INFO. [DATA]

## 2. Manual T1-T10 walk

| T | Class | Verdict | Evidence / disposition |
|---|---|---|---|
| T1 | PIT availability | **PASS** | Inputs are market prints only (option prices, spot closes). No published/event-dated data anywhere in the pipeline; entries are unconditional at ~14 DTE, so no signal exists to leak into. |
| T2 | Timezone | **PASS** | Spot panel: `ds.stock_close()` does `tz_convert('Asia/Kolkata')` before `.normalize()` — landmine #1 handled at source. Angel 2026 append uses IST-native timestamps, `tz_localize(None).normalize()`, appended strictly after the HF panel end (no overlap). |
| T3 | Same-bar execution | **WARN (W1)** | Entry is unconditional (no signal computed from the entry bar) — filling at the entry-day print is standard, not self-referential. The managed exit, however, *decides and fills on the same EOD print*: trigger `cost_bb <= 0.5x credit` is evaluated at a day's price and filled at that same price. Live analogue is a resting limit buy-back at the 50% level. Two offsetting distortions: (a) trigger is CONSERVATIVE (EOD-only check misses intraday touches, undercounting early exits); (b) fill price is OPTIMISTIC (fills at a close that is at-or-below the level, where a live limit fills AT the level). Bounded and paper-measurable — paper desk item #1. |
| T4 | Session boundary | **PASS** | No intraday logic. Single-stock options have no 09:00 pre-open prints; minute-era price picks are >=09:15 by construction of the feed. |
| T5 | Survivorship | **PASS (note)** | Universe = contracts that physically existed per expiry file (HF + bhavcopy backfill) — point-in-time by contract existence; names later removed from F&O remain in history. No pruning to today's list. |
| T6 | Normalization leakage | **PASS** | No z-scores, ranks, vol-scaling, or fitted scalers anywhere. |
| T7 | Label leakage | **PASS** | No feature/label construction; P&L is settlement arithmetic. |
| T8 | Settlement lifecycle — **the S-04 precedent** | **PASS (verified, both pipelines)** | The 2026-07 corruption (84 future-expiry settlements fabricating +1.75% edge) is the reason this audit exists. Verified the purge holds: (i) builder L7 guard skips any expiry beyond per-symbol real `data_end` (`shortlist_shortvol.py` L75); registered parquet max exp 2026-06-30, zero rows settle beyond real data; (ii) `spot.asof()` is backward-only; (iii) L7b physical bounds (>6%/spot "profit" = corrupted mark) drops logged in every sensitivity cell (18-37 rows, ~0.5%); (iv) 2026 monthly winner rates normalized vs the corruption era's 19-100% impossible months; (v) sensitivity rebuild reproduced all 5,031 registered trades **bit-exact** (max P&L diff 0.000000%). |
| T9 | Walk-forward / OOS discipline | **PASS (note)** | No parameters are fitted in-pipeline (convention-chosen config — corroborated by the certified cell sitting at its neighborhood MEDIAN, not the peak). No OOS window was opened. The sensitivity grid adds **33 trials to the family ledger** (logged); standing warning: adopting the grid's best cell (dte16_otm4_pt40) post-hoc would be selection on already-seen data = T9 violation. |
| T10 | Backfilled/revised source | **WARN (W2) — measured live** | Between the registered build and the sensitivity rebuild (same code, same window), Angel daily appends moved per-symbol `data_end`, and the L7 guard admitted **53 additional Jan-Jun-2026 expiries** (mean +0.7445%) it had correctly excluded before. Direction benign (real settlements added, none removed; common keys bit-exact; registered mean unchanged at +0.2241%). This is exactly the drift the config.json row-count/max-date discipline exists to catch — and it did. Standing exposure: Angel purges expired contracts (capture task mitigates). Monitor: any future rerun must re-diff key sets. |

## 3. Killer diagnostics
- **One-day-lag test: strict form NOT RUN — and not cheap.** S-04 has no feature stream to lag: entry is calendar-scheduled (DTE-based), so "lag all features one day" has no referent, and a literal entry+1-day rerun requires a full raw-file sweep (~30-60 min compute) — stated explicitly per instruction rather than faked. The cheap analogue already exists in the sensitivity grid: shifting the entry day via DTE 14->12 (enter ~2 days later) degrades the edge +0.229 -> +0.176 (-23%), DTE 14->16 -> +0.286. **Graceful degradation, no collapse (threshold: >50% = leak signature). PASS on the collapse criterion.**
- **Terminal-date shuffle:** not re-run this session (expensive); partially covered by the prior `20260704_shuffle` run and by T8(v) bit-exact reproduction under a *changed* data snapshot — a leak that depended on future data would not reproduce bit-exact on the common keys when the future changed.
- **Bidirectional stale-print check (W3) — this audit's own finding, outside the standard battery:** `ds.price_asof` takes the *nearest print within +/-15 days in either direction* — a price from AFTER the decision day can price a fill. Measured exposure: buyback triggers 99.0% same-day prints (>2d: 0.22%; same-day-only variant moves the edge -0.0002pp — immaterial); entry legs: 2.3% of a 300-trade sample priced off non-entry-day prints (max 12 days; either direction). Bounded at ~2% of trades and CI-invisible, but the pattern is a standing hazard for any descendant strategy that *conditions* on these prices. Recommend guards.py gain a forward-print detector before this loader is reused in signal-conditioned work. |

## 4. COST_STANDARDS circuit/thin-volume rule (Principal order 2026-07-04, applied to options)
The trades data carries **no volume column** — fill legality under the new rule cannot be checked from the trade log alone. Quantified instead by raw-file sample (n=300 center-config entries, `entry_fill_volume_sample.csv`):
- **2.3%** of entries have a leg with NO print on entry day -> under the rule (zero/absent volume = NO FILL) these are **fabricated fills**;
- **5.0%** have a leg with zero traded volume on entry day despite a print row;
- combined **~5-7% of entry fills are suspect (W4)**. Effect on the edge is bounded (removing ~7% of trades moves a +0.229 mean by at most a few bp unless the suspect trades are systematically the winners — not yet tested);
- **exit-leg (buyback) volume remains UNMEASURED — named data gap**: the trade log stores no exit date, so the paper desk must log strike-level volume at every live buyback and reconcile.

## 5. Flags summary and routing
| Flag | Class | Route |
|---|---|---|
| W1 | EOD trigger/fill approximation on managed exit (T3) | Paper desk measurement #1: realized buyback fill vs 50% trigger level |
| W2 | T10 drift: +53 trades from Angel append; benign, documented | Kavya/ops — key-set diff on every rerun; capture task standing |
| W3 | Bidirectional +/-15d nearest-print pricing (~2% of fills) | guards.py enhancement before any signal-conditioned reuse |
| W4 | ~5-7% entry fills on zero/no-volume strikes; exit-volume gap | Paper desk: strike-volume logging + thin-strike fill success rate |

**Verdict: PASS-WITH-FLAGS.** No T1-T10 class produces a FAIL; the historical T8 corruption is verifiably purged in both audited pipelines; the largest honest uncertainty is execution realism (W1/W4), which is a cost question, not a lookahead question — priced separately by the 2x-cost certification and measurable in paper.

*Signed: Dr. Sameer Bhat (E-027) — Lookahead Controls owner (D-028), Risk Office — 2026-07-04*
