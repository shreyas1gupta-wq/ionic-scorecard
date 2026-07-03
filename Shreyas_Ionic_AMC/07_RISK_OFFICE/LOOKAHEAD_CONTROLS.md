# LOOKAHEAD-BIAS CONTROLS — Risk Office (D-028, Principal order 2026-07-04)
> **STATUS: BINDING.** Owner: Dr. Sameer Bhat (E-027). Live/paper parity monitor: Ritika Sharma (E-020).
> Red-team attack surface: Nikhil Bose. Enforcement: **Gate-4 CANNOT pass without a LOOKAHEAD AUDIT PASS**
> (alongside the sensitivity report). Programmatic checks: `04_RND_LAB/lib/lookahead_audit.py` (+ `lib/guards.py`).

**Definition.** Lookahead bias = any computation that uses information not knowable at the moment the
simulated decision is taken. It is the single most reliable way to fabricate an edge; unlike overfitting,
ONE leaked column can create an arbitrarily large fake return. This firm has already been bitten (see T-log).

## The taxonomy — T1..T10 (every audit walks ALL ten)

| # | Class | The trap | Firm precedent / check |
|---|---|---|---|
| T1 | **Data-availability (PIT)** | Using data on its *event date* instead of its *publication date* — earnings on quarter-end, restated fundamentals, index membership announced later | Landmine #3: `unified_quarterly_pit.parquet` `available_date` col MANDATORY. `audit_pit_column()` |
| T2 | **Timestamp/timezone** | 18:30 UTC bar = NEXT-day 00:00 IST → daily features shifted one day into the future | Landmine #1 (guards L1). `audit_tz()` |
| T3 | **Same-bar execution** | Signal computed on bar t's close, entry filled at bar t's close/open — you traded on a price that finished forming after you "decided" | guards L5; SIG-11/BT-11 rule: next-day open. `audit_same_bar()` |
| T4 | **Intraday session boundary** | 09:00 pre-open auction print used as "open"; post-close prints in the day's bar | Landmine #2 (guards L2, ≥09:15). `audit_session()` |
| T5 | **Survivorship / universe** | Screening today's index members historically; delisted losers absent from the panel | `NIFTY500_TICKER_2005_2025_Final.xlsx` 42 PIT snapshots MANDATORY for universe membership. `audit_universe_pit()` |
| T6 | **Normalization leakage** | Z-scores / percentile ranks / vol scaling fit on the FULL sample (mean/σ include the future); ML scalers fit before the split | Fit stats on trailing windows only, or per-walk-forward-train-window. `audit_full_sample_stats()` (heuristic) |
| T7 | **Label / target leakage** | Feature window overlaps the label window; "12-1 momentum" computed through t instead of t-21; forward returns joined on the wrong date | `audit_feature_label_overlap()`. Merge keys reviewed line-by-line (guards L4) |
| T8 | **Settlement / lifecycle** | Marking open option positions with FUTURE expiry settlement prices; corporate actions applied before ex-date; strike grids from a later master | S-04's 84 fabricated wins (guards L7/L7b — future-settlement + physical bounds). OPS-1 strike-grid cousin |
| T9 | **Walk-forward contamination** | Params tuned on data that includes the "OOS" period; final-12m OOS opened more than once per family; threshold picked after seeing forward results | RESEARCH_SOP: OOS opened exactly ONCE. Family trials ledger. Sameer verifies the run log |
| T10 | **Backfilled / revised source** | Vendor silently restates history (HF re-uploads, Angel master purges expired contracts, "corrected" bhavcopies) — today's file ≠ what was knowable then | DATA_CATALOG snapshot dates; results dirs record row-counts+max-dates (config.json) so reruns detect drift |

## The audit gate (mandatory at Gate-4; re-run at any data-source change)
1. Run `lookahead_audit.py` programmatic battery on the strategy's panel + trade log → machine report.
2. Walk T1–T10 manually against the CODE (greps for `.shift(-`, full-sample `mean()/std()/rank()`, merges on date columns, `available_date` presence). The machine catches patterns; the human catches intent.
3. **The two killer diagnostics** (run for any suspicious result):
   - **Terminal-date shuffle:** recompute the signal with all data AFTER each decision date deleted (true PIT replay) — if results change, there is leakage. Gold standard, expensive; sample ≥20 decision dates.
   - **One-day-lag test:** lag every feature one extra day. A real edge degrades gracefully; a leak COLLAPSES. Collapse ratio >50% = investigate before believing anything.
4. Verdict: **PASS / PASS-WITH-FLAGS / FAIL** filed as `results/<strategy>/<run>/LOOKAHEAD_AUDIT.md`, signed Sameer. FAIL = the backtest result is quarantined (not quotable in any register/memo/letter).
5. Ritika (live/paper): weekly parity check — the PAPER signal stream must be reproducible from data that existed at signal time (capture-time snapshots, not later re-pulls). Divergence = T10 event, escalate.

## Standing code rules (CODE_CHECKS.md incorporates by reference)
- Every feature column carries an explicit **as-of convention** in a comment (`# knowable at t close` / `# available_date-lagged`).
- `.shift(-n)` on any feature = forbidden without a `# LABEL:` tag marking it as a target.
- No `df.mean()/std()/rank(pct=True)` over the full axis inside feature code — trailing windows or train-window-fit only.
- Every merge on dates: `merge_asof(..., direction='backward')` or an explicit availability lag — never exact-date joins for published data.
- Backtests never read files newer than the run's declared data snapshot (config.json rows/max-dates).

## T-log (firm's own lookahead incidents — why this document exists)
- 2026-07: **S-04 future-expiry settlements** marked as closed wins (+1.75% fake edge) — T8. Caught by pre-IC shuffle; guards L7/L7b born.
- 2026-06: HF timezone bug shifted daily bars a day forward — T2. Landmine #1.
- 2026-06: pre-open auction print as "open" corrupted ~94% of 2026 gap calcs — T4. Landmine #2.
- 2026-06: earnings joined on quarter-end dates (not available_date) in early screens — T1. PIT dataset built in response.
- Standing: Angel purges expired contracts from its master — T10. Daily capture task exists BECAUSE of this.

## Changelog
- 2026-07-04: first issue per D-028 (Principal: "ensure no lookahead bias add that too in risk management").
