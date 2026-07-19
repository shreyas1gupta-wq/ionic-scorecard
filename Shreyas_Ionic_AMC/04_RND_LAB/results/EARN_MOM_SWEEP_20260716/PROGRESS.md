# PROGRESS — EARN_MOM_SWEEP_20260716
Goal: 30 long-only earnings-momentum combos, ranked vs calendar-matched placebo. Screen, not cert.

## DONE
- Data recon (schemas, coverage: dense 2020-23, thin 2024-26, price ends 2026-01-22; universe 1,845 overlap).
- SPEC.md written (rules, data, signals, 30-combo frozen registry, output contract).

## NEXT (exact)
1. DONE (2026-07-16, Arjun Rao / Sonnet): engine.py + combos.py + run.py built, smoke-tested
   (A2, B1) — clean, PIT-safe, one_day_lag_test PASS (3.7% collapse, not a leak). See
   "BUILD HANDOFF" below for exact numbers, quirks, and one deliberate deviation from SPEC.
2. NEXT: 3 parallel agents (Sonnet) — Family A / B / C each run their remaining combos via
   `python run.py <IDs>` (A2/B1 already in results.csv, just re-run or skip), write ledgers +
   append results.csv + a family conclusions block. Data quirks below are load-bearing context.
3. DESK-100 synthesize FINDINGS.md leaderboard (beats_placebo95 only = "real"), escalate survivors.

## BUILD HANDOFF (Arjun Rao, 2026-07-16) — read before running your family
- Files: `engine.py` (shared, loads once per process ~75s), `combos.py` (30 frozen combos),
  `run.py <ID...>` CLI. All in this dir. Run via:
  `PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 "C:\Users\Shreyas.1Gupta\AppData\Local\Python\pythoncore-3.14-64\python.exe" run.py A3 A4 A5 ...`
  (pass all your family's remaining IDs in ONE call so the ~75s data load is amortized once.)
- **DEDUP LANDMINE FOUND & FIXED**: unified_quarterly_pit.parquet has 1,278 exact
  (symbol,quarter_end) duplicate rows (kaggle vs screener, same quarter slightly different
  values) that silently corrupt shift(4)/shift(1) YoY math if not deduped first (same failure
  mode as the 17-month-gap lesson). Fixed in `engine.dedupe_fundamentals` (kaggle wins). Not a
  SPEC deviation — SPEC didn't know about this dup; documented in engine.py doc #3.
- **Coverage funnel** (from `engine.get_master()`): 31,891 raw fund rows -> 30,613 after dedup
  -> 10,323 pass the N500 PIT gate -> 9,259 have a resolvable D0+1 entry (rest: symbol missing
  from price panel entirely, or D0 too close to panel end for even one more trading day).
  ~90/1,004 universe tickers never match the price panel at all (renames/delistings not
  aliased, e.g. ABAN, CADILAHC) — a real, disclosed ~9% universe leak, not a bug.
- **eps_yoy is mostly-NaN**: 82% of the 9,259-event master table has NaN eps_yoy_pctile (source
  eps column itself is ~80% NaN per the earlier recon). A8 (eps_yoy top-decile) will therefore
  have a much smaller n_trades than the other A-family combos — check it's still in the
  "hundreds" per SPEC's sanity bar; if it comes in at <100 trades, flag it as underpowered in
  your family conclusions rather than silently trusting the number.
- **A2 smoke result**: n_trades=573, mean_net_pct=5.48%, median=3.37%, win%=56.9%, t_stat=6.42,
  mean_ex_top1=5.30%, mean_ex_top2=5.12%, cens_pct=6.8%, cagr=42.4%, sharpe=1.48, maxdd=-27.5%,
  placebo_mean=6.98%, placebo_p95=8.25%, excess_vs_placebo=-1.50%, **beats_placebo95=False**,
  mean_net_pct_2x=5.08%. No degenerate flags.
- **B1 smoke result**: n_trades=800, mean_net_pct=6.57%, median=4.38%, win%=59.6%, t_stat=8.96,
  mean_ex_top1=6.35%, mean_ex_top2=6.20%, cens_pct=6.1%, cagr=40.4%, sharpe=1.52, maxdd=-24.8%,
  placebo_mean=8.15%, placebo_p95=9.24%, excess_vs_placebo=-1.58%, **beats_placebo95=False**,
  mean_net_pct_2x=6.17%. No degenerate flags.
- **Headline read so far**: both smoke combos LOSE to their own calendar-matched placebo —
  i.e. staying in that stock around that time for the same holding period, entered on a random
  day instead of the earnings day, would have done BETTER on average. This is exactly the
  "trailing-stop/hold structure harvests market drift" pattern from prior PEAD work. Don't
  assume this generalizes to all 30 — sue/turnaround/opm_delta combos may behave differently —
  but go in expecting most of Family A/B to fail beats_placebo95, and treat any combo that
  clears it as the interesting one, not the norm.
- **one_day_lag_test (A2)**: base mean_net_pct=0.05482, lagged(+1d)=0.05280, collapse=3.7% ->
  PASS (graceful decay, no same-bar leak). Run `engine.run_one_day_lag_test(COMBOS['A2'])`
  yourself if you want to re-verify on your own family's combos — cheap (skips placebo/NAV).
- **SPEC deviations, both forced by real data issues, both disclosed above**: (1) fundamentals
  dedup before signal math (not in SPEC, but necessary — SPEC didn't anticipate the dup rows);
  (2) quantile window = pure EXPANDING (not "trailing 4Q with expanding fallback") — went
  straight to expanding because trailing-4Q pools for sparse signals (sue>=2.0, turnaround-
  adjacent) were unstable early in the sample; SPEC.md lines 49-52 explicitly sanctions
  expanding as the fallback, so this is within the letter of the spec, just skipping the
  trailing-4Q attempt. Nothing else deviates: costs 0.67%/1.07%, PIT entry D0+1, N500 gate,
  ledger schema, output contract — all per SPEC.md as written.
- Placebo methodology (K=200, same-symbol/same-calendar-year random entry, real trade's
  realized holding length) is fully documented in engine.py doc #8 — read it before
  interpreting placebo_mean/placebo_p95 on your family's combos.

## OUTPUT PATHS
- results.csv, ledgers/<ID>.csv, FINDINGS.md (all under this dir).

## GUARDRAILS
- PIT: entry D0+1, membership as-of available_date. Placebo K≥200. Report ex-top1/2 + cens%.
- Costs 0.67%/1.07%. No post-hoc tuning. Sonnet tier (D-036). Max 3 parallel (D-023).
