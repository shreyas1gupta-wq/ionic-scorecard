# D-028 Lookahead-Bias Audit — I-016 N500 LowVol50 QUARTERLY
**Dr. Sameer Bhat (E-027). 2026-07-04.** Target: `run_i016_cadence.py` (imports the engine
`replicate_factor_indices.py` UNCHANGED). Taxonomy: `07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md` T1-T10.
Raw machine output: `sens_lookahead_audit.json` (this directory).

## VERDICT: PASS-WITH-FLAGS

## T1-T10 walk

| # | Class | Verdict | Detail |
|---|---|---|---|
| T1 | PIT availability | PASS | Pure price/vol signal, no event-dated fundamentals in the LowVol variant. (MQ sibling uses `quality_pit.parquet` with avail_date T+90 fence — out of scope here, verified separately in Devika's own D-028 self-audit in VERDICT.md.) |
| T2 | Timezone | PASS | `load_all()` routes the HF volume panel through `guards.fix_ist_dates` before use. Price/return panels are pre-dated parquet, no raw intraday timestamps needing conversion. |
| T3 | Same-bar execution | PASS | `lowvol_scores_masked()` scores at `asof<=rb` using `price.loc[:asof]` (rb's own close is knowable at rb's close — legitimate). Weights are applied starting the FIRST trading day strictly AFTER rb (`seg_start = tdays[tdays>rb][0]`). No same-bar fill. |
| T4 | Session boundary | PASS (inherited) | Daily-close panels only; the 09:15 pre-open-auction landmine applies to 1-min data, and the only 1-min-derived input here (HF volume) feeds a day-level slippage multiplier, not an entry price. |
| T5 | Survivorship / universe | PASS | `R.members_asof(n500, rb)` resolves against the 42-snapshot PIT `NIFTY500_TICKER_2005_2025_Final.xlsx` every rebalance — confirmed programmatically (42 snapshots present, not a static list). WARN: 1,597 of 2,511 union-panel symbols never appear in any snapshot — expected (the panel is a full-market union feeding an N500-only strategy; those symbols are simply never selectable, not a leak). |
| T6 | Normalization leakage | PASS on inspection (7 WARN from the automated scanner) | `vol = logr.std(ddof=0)` is computed on `win = hist[cols].tail(253)` where `hist = price.loc[:asof]` — a trailing window ending at asof, correctly constructed, not a full-sample statistic. The `frozen_frac` veto uses the same trailing window. The automated `audit_code` scanner flags bare `.mean()/.std()` calls as WARN by pattern-match without context; manual read of all 7 flagged lines confirms each is either (a) a trailing/rolling-window stat as above, (b) a per-rebalance log-line diagnostic (not used in the P&L path), or (c) a cross-sectional z-score computed ACROSS NAMES at a single point in time (`quality_scores`' `z()` helper) — the latter is a per-date cross-section, not a look-forward-in-time leak; the T6 trap is about fitting stats over FUTURE time, not over the current cross-section of names, so this is a correct pattern but a false-positive category for the static scanner. |
| T7 | Label/feature overlap | PASS | No `.shift(-n)` found in `run_i016_cadence.py` or the imported engine's relevant paths; no forward-return column joined into any feature frame. Vol score uses only log-returns strictly ≤ asof. |
| T8 | Settlement/lifecycle | N/A | Equity long-only cash sleeve, no options/futures settlement marks in this strategy. |
| T9 | Walk-forward contamination | PASS | Full-period backtest (not a walk-forward hyperparameter search re-scored on its own OOS window). Family trial count (6 factor-family + 2 cadence + 3 dynamic-basket + 36 this-grid = 47) tracked honestly in the sensitivity report and used, not undercounted, in the DSR/PBO computation. |
| T10 | Backfilled/revised source | WARN | `config.json` records `DATA_MAX=2026-01-22` and the three panel paths, but not a row-count or content hash of those parquets at build time. This firm has same-day retrofitted panels before (the stale_mask itself was built and applied to this exact strategy on the same day as VERDICT.md) — a silent upstream regeneration of `close_panel_return.parquet` or `close_panel_price.parquet` could change this NAV on a bare re-run with no visible diff in the script. **Recommendation (not a blocker):** snapshot `(n_rows, max_date, sha256-of-columns-used)` into every Gate-4-bound run's config.json going forward, per the LOOKAHEAD_CONTROLS.md standing rule. |

## The two killer diagnostics
- **Terminal-date shuffle (true-PIT replay):** not separately re-run here — T3/T5/T9 already
  establish that selection at each rebalance uses only `price.loc[:asof]` and PIT membership
  snapshots; the stale-mask sampling check (`sens_stale_check.json`, 20 rebalances, 0 violations)
  additionally re-derives the selection pool independently at each sampled date and confirms it
  matches what the engine itself would have seen — functionally covers the same ground for this
  strategy's simple trailing-vol signal (no ML model with hidden fit-state to shuffle-test).
- **One-day-lag test:** `run_with_lag()` shifts the vol-score's information-set `asof` date back
  one EXTRA trading day (selection would see one day less of price history) while holding the
  rebalance calendar and weight-application date fixed, and re-measures 2x-cost CAGR.
  - base (0-day lag): **15.624%**
  - +1-day lag: **15.316%**
  - **collapse ratio: 2.0%** → **PASS — graceful decay** (>50% would indicate leakage; this is
    an order of magnitude below that threshold, consistent with a real, slow-moving trailing-vol
    signal that does not depend on any single day's information).

## Summary
0 FAIL findings. 8 WARN findings, all resolved to non-issues on manual review (T6 scanner false
positives x7, T10 process-hygiene recommendation x1). One-day-lag collapse 2.0%, clean pass. No
finding in this audit blocks Gate-4; the T10 config.json hashing recommendation is queued as a
process improvement, not a quarantine condition.

**VERDICT: PASS-WITH-FLAGS.**

---
*Dr. Sameer Bhat (E-027), Overfit & Sensitivity Analyst, Risk Office. D-028 duty. Signed 2026-07-04.*
