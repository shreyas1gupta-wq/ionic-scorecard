# LOOKAHEAD AUDIT -- verdict: PASS-WITH-FLAGS
FAIL: 0 | WARN: 15 (taxonomy: 07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md, D-028)
- [WARN] code_scan: bt11_union.py:122: snap.loc[valid, "rs_pct"] = snap.loc[valid, "mom_blend"].rank(pct=True) * 100.0 -> T6: full-sample percentile rank — the percentile at time t includes future cross-sections unless applied per-date group
- [WARN] code_scan: bt11_union.py:161: ref.loc[valid, "rs_pct"] = ref.loc[valid, "mom_blend"].rank(pct=True) * 100.0 -> T6: full-sample percentile rank — the percentile at time t includes future cross-sections unless applied per-date group
- [WARN] code_scan: bt11_union.py:345: sharpe = (monthly_ret.mean() / (monthly_ret.std(ddof=1) + 1e-12) * np.sqrt(12) -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization
- [WARN] code_scan: bt11_union.py:360: "avg_trade_ret_pct": round(float(g["ret"].mean()) * 100, 3), -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization
- [WARN] code_scan: bt11_union.py:361: "win_rate_pct": round(float((g["pl"] > 0).mean()) * 100, 2), -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization
- [WARN] code_scan: bt11_union.py:362: "pct_entries_no_vol": round(float((~g["entry_has_vol"]).mean()) * 100, 2) -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization
- [WARN] code_scan: bt11_union.py:383: "avg_cash_slots": round(float(pe["cash_slots"].mean()), 2), -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization
- [WARN] code_scan: bt11_union.py:416: "avg_trade_ret_pct": round(float(g["ret"].mean()) * 100, 3), -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization
- [WARN] code_scan: bt11_union.py:417: "win_rate_pct": round(float((g["pl"] > 0).mean()) * 100, 2), -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization
- [WARN] code_scan: bt11_union.py:477: f"has_vol={100*panel['has_volume'].mean():.1f}%") -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization
- [WARN] code_scan: bt11_union.py:547: pct = float((cagrs < real_cagr).mean() * 100.0) -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization
- [WARN] code_scan: bt11_union.py:593: "has_volume_pct": round(100 * float(panel["has_volume"].mean()), 2), -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization
- [WARN] code_scan: data11_union.py:147: f"({100*panel['has_volume'].mean():.1f}%); union-only(no vol)={int((~panel['has_volume']). -> T6: bare .mean()/.std() — verify it is per-date/rolling/train-window, not full-sample normalization
- [WARN] T2_tz: timestamps are tz-naive — confirm they are IST dates, not raw UTC (landmine #1)
- [WARN] T5_universe: 1597 panel symbols never in any PIT snapshot (sample: ['20MICRONS', '21STCENMGM', '3IINFOLTD', '3PLAND', '5PAISA'])

## HUMAN DISPOSITION (Devika, E-016) — every WARN reviewed, none are leaks

- **[WARN] code_scan .rank(pct=True)** (bt11_union.py compute_month_signals / _assert; data11 none):
  DISPOSITION = NOT A LEAK. rank(pct=True) is applied to `snap` = ONE month's PIT snapshot only
  (compute_month_signals filters to `feats_by_date[asof]` restricted to that month's universe),
  NOT the full sample. This is the RS cross-sectional percentile, by design PIT-set-relative.
  Verified in _assert_engine_matches_features (fast path == from-scratch date<=asof rebuild).
- **[WARN] code_scan bare .mean()/.std()** (metrics Sharpe; mb.min()/max() normalization):
  DISPOSITION = NOT A LEAK. (a) Sharpe .mean()/.std() are over the REALIZED monthly-return path
  (past P&L only). (b) mom_blend min/max normalization is WITHIN a single month snapshot for the
  composite ranking score — a monotone rescale of that month's cross-section, no future info.
- **[WARN] T2_tz tz-naive dates**: DISPOSITION = NOT A LEAK. Panel `date` is the ALREADY-IST-FIXED
  trading date (union build applied guards.fix_ist_dates on the HF core; MASTER/DELISTED are
  daily calendar dates). No 18:30-UTC signature (audit_tz only FAILs on >50% 18:30 stamps).
- **[WARN] T5_universe stray symbols**: DISPOSITION = EXPECTED & CORRECT. The union panel
  deliberately carries DELISTED/non-index names (survivorship fix). Selection is gated by
  pit_universe(asof) at every rebalance, so strays can never be BOUGHT — they only widen the
  price panel. This is the anti-survivorship mechanism, not a bug.
- **T3 same-bar**: fills use _next_close (searchsorted side='right') = strictly the first trading
  day AFTER the rebalance signal date -> next-day execution, L5-clean. DEVIATION from bt11: fill
  at next-day CLOSE (union has no open) rather than next-day open. This is a ~1-day-later, more
  CONSERVATIVE fill, stated loudly; it cannot introduce lookahead (still strictly t+1).
- **T7 label/momentum**: mom_12_1 = close.shift(MOM_SKIP)/close.shift(MOM_SKIP+MOM_12M)-1 uses
  only PAST closes (positive shifts). No negative shift anywhere (scanner would FAIL on shift(-)).

(Programmatic verdict above; with dispositions the WARNs are cleared -> effective verdict: PASS-WITH-DISPOSITIONS. No FAIL findings.)
