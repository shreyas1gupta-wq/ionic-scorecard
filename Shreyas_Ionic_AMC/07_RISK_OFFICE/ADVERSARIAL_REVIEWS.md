# ADVERSARIAL REVIEWS — Red Team log (Nikhil Bose; reports to CIO only)
One focused attack per idea (D-008). Verdict REAL / FRAGILE / FAKE. Strategy cannot pass gate 5 without a row here.

## The gate checklist (ALL must pass — from BUILD_ADDENDUM §5)
PIT universe (42 snapshots) · `available_date` fundamentals · IST tz fix · first bar ≥09:15 · option-data schema/coverage acknowledged (gap now FILLED — daily granularity caveat) · costs per COST_STANDARDS + 2× stress · ADV caps · walk-forward with ONE untouched final OOS · DSR + PBO reported (honest trials) · ≥30 trades/param, ≤5 params · regime slices 2018/2020/2022/2024/2026 · capacity estimate · economic WHY written BEFORE testing · kill criteria pre-registered · outcome logged (REGISTER or KILLED_IDEAS).

## Placebo battery (strategy must FAIL placebos, pass real)
lag+1 degrades · cross-sectional shuffle → Sharpe≈0 · random-entry benchmark beaten decisively · 2× costs survive · bootstrap 1,000: 5th-pctile CAGR > 0.

## Review log
| Date | Target | Attack chosen | Evidence | Verdict | AP |
|---|---|---|---|---|---|
| 2026-07 (pre-firm, retro-logged) | FF calendar v1 (+80%/trade) | Denominator artifact: return-on-net-debit → 0 | Rebuilt with back-premium denom → +15%/trade real | was FAKE → v2 REAL | +15 |
| 2026-07 (retro) | 5-sleeve portfolio Sharpe 7-10 | Return-spreading fabricated daily variance | Exit-month booking → Sharpe ~2.6 | was FAKE → rebuilt | +15 |
| 2026-07 (retro) | Mid-cap "16 landmines" filter | Lookahead: selected on realized outcomes | Walk-forward persistence modest; ex-ante IV filter catches 8/12 | FAKE as filter; lesson logged | +15 |
| 2026-07 (retro) | Earnings +43.6% "last month" | Near-expiry return-on-premium explosion (+357% rows) | DTE<7 events = artifact rows; gate added to S-02 | FRAGILE → gated | +10 |
| 2026-07-03 | **S-01 IV/RV straddle — IC Round 2 (first live IC review)** | Regime-beta vs signal-alpha: within-month iv_rv shuffle → 37.6%→26.8% (71% of headline = base short-vol beta); incremental alpha +11.4pts (boot 5th-pctile +10.3, sig) BUT 2022 incremental −10.1 (signal WORSE than random in the sole stress year); 96.2% of n in 2024-04→2026-05 low-vol block | Headline overstated ~3.4×; prevents sizing the sleeve to borrowed VRP beta that inverts in the exact tail the firm exists to survive | **FRAGILE** — flip: positive incremental through a real vol-crush sample + re-register edge as ~+11pt incremental | +15 |
| 2026-07-04 | **S-02 earnings sleeve — pre-IC shuffle (Gate-5 SOP, first use)** | Denominator artifact + base-inversion: c4_short_thru normalizes by decaying per-leg premium (max row +6,759%, DTE=1); gated honest +9.7%; crush vs exit-before +4.8% (CI touches 0); vs calendar-matched unconditional −10.1% (CI all-neg); 2023 carries the sign | Killed an IC cycle before it convened; registered number was fiction | **FAILS-PRE-IC** — resurrection conditions registered | +15 (Arjun) |
| 2026-07-04 | **S-04 strangle — pre-IC shuffle #2** | DATA CORRUPTION: 84 future-expiry rows closed as wins (stale spot.asof fabricates settlement); impossible-winner rate 4%→41% from 2026-02; physically impossible +40.7%-of-spot profits | Registered +1.75%/88% is fiction; honest ≤2025 edge +0.27%/spot, decaying, crash-blind; managed-exit proven a tail lever not return-adder | **FAILS-PRE-IC — dataset bounced to Data Office** | +15 (Arjun) |
