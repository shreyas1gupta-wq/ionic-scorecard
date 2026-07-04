# D-M4 FINAL — Replication on PIT UNION PRICE panel (Arjun Rao, 2026-07-04)
(Filed by main desk from Arjun's returned report — his direct file-write was harness-blocked.)

## ONE LINE
**LOWVOL30 v2: full-period TE 4.58% / corr 0.956, TE <=6% across ALL of 2008-2026, 2.71% in 2023-26 — the D-M4 goal is MET.**
MOMENTM30: full TE 8.48% / corr 0.933 (HF-alone was 15.55%); ~6.4% floor from 2016+ — residual is unreproducible NSE mechanics (true IWF float weights + exact constituent list; factsheets = home-net).

## Three-column era table (momentum A_incl EW): HF-alone -> Master-EW(basis-mixed) -> UNION-PRICE
2005-15: 0.599/20.14% -> 0.725/18.65% -> **0.904/10.76%** | 2016-19: -> **0.921/6.11%** | FULL: 0.719/15.60% -> 0.781/14.52% -> **0.915/9.03%**

## Early-era decomposition (the round-1 wound, closed)
1. Coverage residual SMALL (scorable 71.8->75.9%). 2. **Episodic HF OUTAGES were the real killer** (2007+2012 zero-basket years; 2011-12 total hole) — union fills them: corr 0.935/0.784. 3. Float-weight absence ~0.4-0.6pp. 4. Constituent-selection mismatch = dominant residual (~2-4pp), unmeasurable on-disk (no official constituent list; proxy-blocked).

## Task-3 retroactive caveat
Master-EW run mixed a dividend-adjusted RETURN series into a PRICE-index comparison (ground-truth: Master matches bhavcopy only 41%) — its numbers are superseded by this basis-consistent run.

## Audit
Engine UNCHANGED from round-1 (diff = data loader only). Mar/Sep membership correction honoured. Degenerate detectors ALL CLEAN (real max-move dates: 2009-05-18, 2020-03-23; no NaN leaks; quarantines untouched). D-028 self-audit PASS (0 FAIL). Frozen-panel md5 cc5f70d1f94129d52bd55fc8b77d0094.
Full detail: headline_summary.csv, era/peryear 3-col CSVs, engine_diff_vs_round1.txt, run.log in this dir.
