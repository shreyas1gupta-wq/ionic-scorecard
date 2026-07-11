# LEAK/LOOPHOLE AUDIT — self-red-team of 2026-07-11 work (Principal challenge: "there will definitely be some loopholes and leaks")

## MATERIAL — fixed or rule-changed today
1. **Pre-registration not provable (process hole).** C2/A1/C1 cards were frozen in MASTER_PLAN *before* their scripts ran, but card + results landed in the SAME git commit — so the freeze-before-run ordering is my word, not cryptographic fact. **FIX ADOPTED (standing rule, effective now): the frozen card is COMMITTED ALONE before the experiment script is executed.** The freeze commit hash goes into the results file. Nothing about today's verdicts changes (all three were kills/parks — the incentive to cheat runs the other way), but the next PASS must be provable.
2. **A4 prerequisite gap: no NIFTY spot 2011–2015 daily.** Kaggle minute data starts 2015-01; hedging-study india parquet starts 2016. The bhavcopy backfill gives options + FUTURES — near-month futures close is a usable spot proxy, but that must be declared in the A4 card, or NIFTY daily 2011-15 pulled from the NSE indices archive first. Flagged into the A4 card spec (to be frozen).
3. **A4 must use SETTLE_PR, never CLOSE**, and must drop 0.05-floor/0.00 untraded strikes (bhavcopy CLOSE is stale last-trade; existing dual-schema landmine extends to the 2011-21 vintage).

## CHECKED EMPIRICALLY — clean
4. Stale/dead entry prints (would fake C2/A1 entries): **0 of 1,224 + 1,228 + 1,793 obs** below plausibility floors; premium percentiles smooth across DTE. Clean.
5. Settlement STT on ITM finishes (ignored in A1 nets): mean 0.31 pts, max 1.88 — sub-noise vs the 4-pt cost model and the −300..−776 worst-5s. Negligible, conclusions unchanged.
6. C1 timezone alignment: regressor = most recent US session ending strictly before the NIFTY date; same-calendar-day US sessions (which end AFTER NIFTY's open) correctly excluded. No lookahead. (Stage-2 in-sample coefficients were flagged in the output itself.)

## ACCEPTED CAVEATS — documented, not fixed (would not flip any verdict)
7. C2/A1 "15:25 settle" = last print ≤15:25, not NSE's closing-VWAP settlement — direction-neutral noise.
8. A1 cross-bucket correlation: k and k−1 entries to the same expiry overlap in time — within-bucket t-stats (the decision statistic) are unaffected; cross-bucket comparisons are correlated (all t≈1 anyway).
9. US stocks `adj_close` is retro-adjusted — fine for returns, WRONG for price-level rules ("stock under $5", round-number effects). Use raw `close` for those.
10. Binance quotes are USDT not USD (depeg episodes distort); HistData gold = BID quotes of a CFD in EST timezone, no spreads — both noted in catalog.
11. Participant-OI publication time is EOD-after-close: any strategy must use it T+1 (B1 card already specifies this) — using same-day would be lookahead.
12. Survivorship in US stocks bulk — already documented as landmine (2/7,693 tickers end pre-2025).

## STANDING LOOPHOLES THE FORWARD TEST COVERS (cannot be closed in-sample)
- ~155+ trials on the same 2021-26 sample (selection pressure) → DSR needs the consolidated ledger (Phase-0 #9, still BLOCKING for the next Gate-4).
- SL fills modeled at next 1-min close (ticks worse in reality) → S1-F kill criterion #3 (implementation shortfall >3pts/day over 13 expiries → HALT) is the live guard.
