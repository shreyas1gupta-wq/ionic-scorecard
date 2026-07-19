# LOOKAHEAD AUDIT T1-T10 -- ALPHA_RANKER 7-leg composite (D-028)
Owner: Dr. Sameer Bhat (E-027). Target: `rnd/cards/AUDIT_TRUE7_1Y.json` (the composite FINAL_MODEL.md S2 should be re-cited to, per PREIC_AUDIT.md) + its 7 legs. Battery: `04_RND_LAB/lib/lookahead_audit.py` (`07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md` T1-T10 taxonomy).

**VERDICT: FAIL** (1 FAIL, 16 WARN)

## Per-class results

| Class | Verdict | Finding |
|---|---|---|
| T1_pit | INFO | 0/1092384 rows have available_date before the fiscal-year-end proxy (source publication-before-event check) |
| T1_pit | INFO | available_date column present in fundamentals source; all 4 fundamentals-based legs (EY, QMJ, issuance, asset-growth, cfo_pat) confirmed via source read to merge_asof(direction='backward') on this column, not on fiscal_year/quarter-end -- landmine #3 respected |
| T2_tz | INFO | panel dates are month-end labels derived from daily-close parquet index (tz-naive IST trading-calendar dates), no raw UTC intraday timestamps in this pathway -- landmine #1 applies to the HF options data, not this equity panel |
| T3_same_bar | INFO | harness.evaluate() is a cross-sectional rank/IC scorer (decision date == rebalance date, position held to next rebalance), not a signal/entry trade log with separate timestamps -- the T3 same-bar-execution check does not apply to this evaluation layer; it WOULD apply if/when this composite is wired into an actual order-placement pipeline, flagged for that gate |
| T4_session | INFO | no intraday bars are read anywhere in the fundamentals/monthly-rebalance pathway that builds this composite |
| T5_universe | FAIL | ALPHA_RANKER's panel universe is built from `nifty_total_market_750.csv` (751 CURRENT constituents, single static snapshot per build_panel_long.py's own documented caveat), NOT the 42-PIT-snapshot `NIFTY500_TICKER_2005_2025_Final.xlsx` mandated by landmine #6/T5 for universe membership. Names delisted/removed from the CURRENT 750-name universe before today are absent from EVERY historical panel date, including 2005-2015 dates decades before this snapshot was taken -- classic survivorship bias in the panel's cross-section, distinct from (and in addition to) the already-disclosed current-snapshot sector/mktcap caveat. |
| T5_universe | INFO | the mandated PIT file exists on disk (1 sheets) and is NOT wired into this panel build -- an available fix, not a data gap |
| T6_T7_code_scan | WARN | run_long_confirm.py:94: pct = g.rank(pct=True) -> T6: full-sample percentile rank — the percentile at time t includes future cross-sections unless applied per-date group |
| T6_T7_code_scan | WARN | run_long_confirm.py:111: ma_fast = close.rolling(fast_n, min_periods=fast_n).mean() -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization |
| T6_T7_code_scan | WARN | run_long_confirm.py:112: ma_mid = close.rolling(mid_n, min_periods=mid_n).mean() -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization |
| T6_T7_code_scan | WARN | run_long_confirm.py:113: ma_slow = close.rolling(slow_n, min_periods=slow_n).mean() -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization |
| T6_T7_code_scan | WARN | run_long_confirm.py:120: ma = close.rolling(n, min_periods=n).mean() -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization |
| T6_T7_code_scan | WARN | run_long_confirm.py:163: cov_ok = window.notna().mean() >= 0.80 -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization |
| T6_T7_code_scan | WARN | run_long_confirm.py:173: ma150 = close.rolling(150, min_periods=150).mean() -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization |
| T6_T7_code_scan | WARN | run_long_confirm.py:233: "bear_ic_2008_11_20": float(bear["ic"].mean()) if len(bear) else None, -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization |
| T6_T7_code_scan | WARN | run_long_confirm.py:234: "other_ic": float(other["ic"].mean()) if len(other) else None, -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization |
| T6_T7_code_scan | WARN | run_long_confirm.py:236: "bear_ic_by_year": {int(y): float(g["ic"].mean()) for y, g in bear.groupby("year")}, -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization |
| T6_T7_code_scan | WARN | builders_w2_profq.py:93: fresh_frac = df.groupby(["symbol", "fiscal_year"])["is_fresh"].mean() -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization |
| T6_T7_code_scan | WARN | builders_w2_profq.py:143: g["ni_growth_std5y_neg"] = -ni_growth.rolling(5, min_periods=3).std()  # IDG-G-12 stabilit -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization |
| T6_T7_code_scan | WARN | builders_w2_profq.py:198: return float((merged["is_fresh_frac"] >= 0.5).mean()) -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization |
| T6_T7_code_scan | WARN | builders_w2_profq.py:205: return s.groupby(level="date").rank(pct=True) -> T6: full-sample percentile rank — the percentile at time t includes future cross-sections unless applied per-date group |
| T6_T7_code_scan | WARN | builders_w2_profq.py:211: return (x - x.mean()) / sd if sd and sd > 0 else pd.Series(np.nan, index=x.index) -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization |
| T6_T7_code_scan | WARN | builders_w2_issuance.py:75: return (v - v.mean()) / sd -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization |
| T9_oos | INFO | family ledger: AUDIT_TRUE7=1 trial(s), CAPSTONE_COMPO=1 trial(s), total_trials(all families)=455. The TRUE7 composite itself was built+scored via harness.evaluate() exactly ONCE (sameer_preic_audit.py, disclosed as +1 new honest trial) -- no repeat OOS opens on this specific construction. However the composite's 7 legs were each selected from a much larger multi-week search (H001-H050+, W2 series, 90 families, 454 trials total) -- the HONEST trial count for 'did we go looking for a 7-leg composite that works' is NOT 1, it is closer to the full program-level count. This is exactly the DSR/PBO n_trials ambiguity Gate 3 must resolve, not a T9 pass/fail on its own. |
| T10_backfill | INFO | panel_long loaded: 148297 rows, 249 monthly dates, 969 symbols, date range 2005-04-29..2025-12-05. No config.json row-count/max-date snapshot stamp found alongside panel_long.parquet -- CLAUDE.md/LOOKAHEAD_CONTROLS.md standing rule ('backtests never read files newer than the run's declared data snapshot') is not mechanically enforced here; a future re-run against a silently-revised fundamentals source (screener_dump backfills, Angel purges) would not be automatically detected. Disclosed gap, not a demonstrated leak. |

## One-day-lag test (killer diagnostic)

| Name | IC_mean | IC_mean(+1 lag) | collapse_ratio | verdict |
|---|---|---|---|---|
| COMPOSITE(AUDIT_TRUE7_1Y) | 0.19008992358092444 | 0.17892375571600563 | 0.05874150325577455 | PASS |
| value_EY | 0.07922785908062568 | 0.08003901584191951 | 0.010238276923125726 | PASS |
| mom_resid_plain | 0.11127098480382781 | 0.09833412930515706 | 0.11626441090171528 | PASS |
| trend_ma65_slope | 0.09572341627910882 | 0.0853377646068129 | 0.10849645860960085 | PASS |
| quality_QMJ | 0.14827387510095497 | 0.14655090464089132 | 0.011620189051446374 | PASS |
| bs_issuance | 0.060610682526194136 | 0.059959433486571324 | 0.010744789738036048 | PASS |
| bs_asset_growth | None | None | None | None |
| quality_cfo_pat | 0.042046315841370516 | 0.04204178924715121 | 0.00010765733284174257 | PASS |

## Verdict rationale
- T1 (PIT): PASS -- all 4 fundamentals legs confirmed source-code-verified to use `merge_asof(direction='backward')` on `available_date`, never on fiscal_year/quarter-end.
- T2/T3/T4: N/A for this evaluation layer (monthly cross-sectional rank/IC scorer, no intraday bars, no trade-level entry timestamps) -- flagged as an open item for the day this composite is wired into an execution pipeline, not a finding against the research layer itself.
- **T5 (survivorship): FAIL.** The panel's universe join uses `nifty_total_market_750.csv` (CURRENT constituents only, single static snapshot), not the mandated 42-snapshot `NIFTY500_TICKER_2005_2025_Final.xlsx`. This means every historical panel date (back to 2005) is scored only against names that happen to still be in the universe TODAY -- delisted/merged/renamed losers are structurally absent. This is additive to (not the same as) the already-disclosed current-snapshot sector/mktcap caveat in `build_panel_long.py` -- it affects WHICH STOCKS appear at all, not just their metadata.
- T6/T7 (code scan): see raw hits table above -- static regex hits on the 3 builder files are dominated by per-date `.groupby('date')...rank(pct=True)` patterns (correct, causal) that the regex cannot distinguish from a full-sample rank; manual read of `run_long_confirm.py`/`builders_w2_profq.py`/`builders_w2_issuance.py` confirms all rank/mean/std calls are inside `.groupby("date")` or rolling-window wrappers -- no genuine full-sample normalization leak found in these 3 files.
- T9: composite opened once (disclosed +1 trial); the deeper question -- how many trials produced the 7-LEG SELECTION itself -- is not a T9 pass/fail, it is exactly the DSR/PBO n_trials question resolved in `DSR_PURGEDCV.md` (Gate 3).
- T10: no config.json snapshot stamp alongside panel_long.parquet -- mechanical re-run drift detection is not wired up. Disclosed gap, not a demonstrated leak.
- One-day-lag test: composite collapse_ratio 0.059 (PASS, <0.25). All 6 legs with cards clean (<0.12, PASS). `bs_asset_growth` was never independently run through `harness.evaluate()` as a standalone leg (only as a leave-one-out incremental-value row) -- no per-leg lag_test exists for it; the composite-level lag test still covers it in aggregate, but a standalone re-check is recommended before final sign-off.

## Sign-off
**FAIL.** The composite does NOT show classic leakage (T1/T7/lag-test all clean) but Gate-4 cannot be signed PASS outright because of the T5 survivorship finding, which is a genuine structural bias (not a false positive) with a known, available fix (wire in the 42-snapshot PIT file). Per D-028 protocol, a FAIL on any class quarantines quoting this result until remediated or the bias is bounded and explicitly disclosed in the IC memo -- recommend the latter (quantify the survivorship exposure) rather than re-running the whole panel build, given the modest edge magnitudes already on record.

## ADDENDUM 2026-07-17 (Arjun Rao, quant desk) -- bs_asset_growth standalone 1Y lag test
Gap closed: `bs_asset_growth` was flagged in the original T1-T10 pass as never independently lag-tested at 1Y (only present in the composite-level lag test and a leave-one-out incremental row with no lag_test field). Ran it standalone through the identical harness/panel/basis used for the other 6 TRUE7 legs -> `rnd/cards/STANDALONE_bs_asset_growth_1Y.json` (+1 disclosed trial, family STANDALONE_LAGCHECK).

| Name | IC_mean | IC_mean(+1 lag) | lag_test_delta | verdict |
|---|---|---|---|---|
| bs_asset_growth (STANDALONE, 1Y) | 0.0352901970988775 | 0.03482420401223511 | 0.013204604251337768 | PASS |

**Result: PASS** (lag_test_delta=0.0132 < 0.25 threshold). All 7 TRUE7 legs now have an independent 1Y lag_test on record; no leg is unverified. This closes the residual T1-T10 gap; it does NOT change the binding Gate-3 verdict (DSR~0 / PBO>0.5 multiple-testing kill stands per FINAL_MODEL.md S5-RISKOFFICE) -- this addendum is a leak-check closure only, not a re-certification.