# CODE CHECKS — mandatory before trusting ANY backtest output
(BUILD_ADDENDUM §9 verbatim + status update. Guards importable from `04_RND_LAB/lib/guards.py`.)

## Landmine guards — every backtest entry point
```python
from datetime import time
# L1 HF timezone bug: daily 18:30 UTC == next-day 00:00 IST
assert df["timestamp"].dt.tz is not None, "tz-naive timestamps"
df["date"] = df["timestamp"].dt.tz_convert("Asia/Kolkata").dt.date
# L2 pre-open auction bug: real open = first bar >= 09:15
intraday = intraday[intraday["timestamp"].dt.time >= time(9, 15)]
# L3 PIT: never act on data before it was public
assert (signals["available_date"] <= signals["action_date"]).all(), "LOOKAHEAD"
# L4 merge safety: joins must not create/destroy rows silently
n0 = len(a); m = a.merge(b, on=k, how="left"); assert len(m) == n0, "merge blew up rows"
# L5 same-bar sin: signal computed on bar t must trade at t+1 (or t close -> t+1 open)
# L6 option-data schema awareness (UPDATED 2026-07-03: gap FILLED with DAILY bhavcopy bars):
#    - single-stock options Apr-24..Aug-25 & Jun-26 & the 122 new names = DAILY bars (settle/oi cols, naive 15:30 stamps)
#    - intraday logic must NOT run on daily-schema files; EOD logic fine on both
#    - filter volume>0 to exclude 0.00-price untraded strikes in daily files
```

## Post-run degenerate detectors (any hit = assume bug until proven otherwise)
- Daily-strategy Sharpe > 4, or CAGR > 60% with MaxDD < 10%
- Win rate > 75% with avg-win/avg-loss < 0.5 → tail-seller profile: check 2020/2022/2024 crash slices
- >30% of total P&L from one symbol/expiry, or top-5 trades removed → strategy goes negative
- Equity curve R² vs straight line > 0.98 (too smooth = accounting bug)
- Implied participation > 10% of 20d ADV anywhere (capacity fiction)
- Trade-level P&L sum ≠ equity-curve delta (leak in accounting)
- **(firm additions)** returns normalized by a to-zero denominator (net-debit!) · per-trade returns spread across holding days · partial-year coverage read as full years · near-expiry return-on-premium rows (DTE<7) dominating an average

## Placebo battery (Red Team runs; must FAIL placebos, pass real)
- Lag signal +1 day → performance must DEGRADE (improves ⇒ lookahead)
- Shuffle signal cross-sectionally within each date → Sharpe ≈ 0 expected
- Random-entry benchmark at same trade frequency → real must beat decisively
- 2× costs rerun (COST_STANDARDS promotion rule) · bootstrap 1,000 resamples → 5th-pctile CAGR > 0

## Lookahead (D-028, 2026-07-04)
Standing code rules from LOOKAHEAD_CONTROLS.md apply to EVERY backtest/feature file: as-of comment per feature column; `.shift(-n)` only with `# LABEL:` tag; no full-sample mean/std/rank in features; merge_asof(direction='backward') for published data; run `lookahead_audit.audit_code()` on your own file before handing to review.
