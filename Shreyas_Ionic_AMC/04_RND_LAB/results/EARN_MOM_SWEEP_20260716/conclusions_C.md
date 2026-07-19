# Family C conclusions — surprise-magnitude / turnaround / other
Owner: Arjun Rao (quant-head), 2026-07-16. Screen tier only (per SPEC — single PIT window, no
walk-forward/DSR/PBO claimable here). [DATA] below = read off results.csv after verified write;
[INFERENCE] = my read; [OPINION] = judgment calls.

## [DATA] Run confirmation
- All 10 C1–C10 executed clean, no exceptions. `ledgers/C1.csv` … `ledgers/C10.csv` all present
  (10 files, verified via `ls ledgers/ | grep -c "^C"` = 10).
- results.csv verified at 30 rows (A1–A10, B1–B10, C1–C10) after a **results.csv write race**
  (see Ops note below) was resolved. Snapshot of the verified C rows saved alongside this file:
  `C_snapshot_verified.csv` (10 rows, same dir).
- one_day_lag_test run on C1 (turnaround) and C6 (OR combo) as spot-checks: collapse_ratio 0.8%
  and 3.6% respectively → both PASS (graceful decay, not same-bar leakage).
- No `n_trades < 100` (my underpowered flag threshold): smallest is C1/C2 turnaround at n=254 —
  well above the SPEC's 30-trades/parameter floor and comfortably answers the "was n=15 too small
  before" question with a real number this time.
- Engine's automated degenerate-flag check fired **zero** flags across all 10 (no Sharpe>4, no
  win%>75%+W/L<0.5 concentration pattern caught).

## Full table (C1–C10)

| combo_id | signal | hold | n_trades | win% | mean_net% | median_net% | t_stat | mean_ex_top1% | mean_ex_top2% | cens% | sharpe | placebo_mean% | placebo_p95% | excess_vs_placebo% | beats_placebo95 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| C1 | turnaround | fixed:63 | 254 | 57.5% | 6.10 | 2.81 | 4.77 | 5.65 | 5.34 | 4.7% | 0.95 | 6.66 | 8.47 | -0.56 | **False** |
| C2 | turnaround | dma:50 | 254 | 38.2% | 4.20 | -1.08 | 3.11 | 3.41 | 2.81 | 0.4% | 0.67 | 4.72 | 6.13 | -0.52 | **False** |
| C3 | sales_yoy top-decile | fixed:63 | 430 | 52.3% | 4.69 | 1.17 | 4.12 | 4.27 | 4.03 | 5.8% | 1.30 | 5.98 | 7.91 | -1.29 | **False** |
| C4 | opm_delta top-decile | fixed:63 | 629 | 59.5% | 6.58 | 3.89 | 8.12 | 6.38 | 6.22 | 4.3% | 1.27 | 7.64 | 8.96 | -1.06 | **False** |
| C5 | qoq top-decile | fixed:40 | 731 | 57.3% | 4.43 | 1.75 | 7.30 | 4.28 | 4.15 | 1.2% | 0.84 | 4.03 | 4.95 | **+0.40** | **False** |
| C6 | np_yoy≥100% OR turnaround | fixed:63 | 1016 | 57.3% | 6.00 | 3.15 | 8.87 | 5.83 | 5.71 | 5.5% | 1.34 | 7.34 | 8.35 | -1.33 | **False** |
| C7 | np_yoy top-decile | fixed:126 (long-drift) | 573 | 55.7% | 10.27 | 3.04 | 7.51 | 9.95 | 9.70 | 11.9% | 1.35 | 13.95 | 15.56 | -3.67 | **False** |
| C8 | np_yoy & sales_yoy tercile (quality-growth) | fixed:63 | 821 | 54.3% | 4.67 | 2.20 | 6.03 | 4.45 | 4.30 | 6.9% | 1.51 | 6.78 | 7.99 | -2.11 | **False** |
| C9 | accel | fixed:63 | 2928 | 57.3% | 4.52 | 2.29 | 13.45 | 4.46 | 4.41 | 7.2% | 1.62 | 4.73 | 5.20 | -0.20 | **False** |
| C10 | np_yoy top-decile · surprise-weighted sizing | fixed:63 | 573 | 56.9% | 5.48 (EW) / **13.20 (SW)** | 3.37 | 6.42 | 5.30 | 5.12 | 6.8% | 1.48 | 6.98 | 8.25 | -1.50 (EW) | **False** |

(mean_net%, median_net%, mean_ex_top1/2%, placebo%, excess% all ×100 from raw fractions in
results.csv for readability. sharpe/cagr/maxdd/2x-cost columns omitted here for space — full
values in `C_snapshot_verified.csv`.)

## [INFERENCE] Verdict: 0/10 clear beats_placebo95. No survivor to escalate from Family C.

**Turnaround (C1/C2) — the priority read — does NOT survive the multi-year test.**
Prior single-quarter work had turnaround at t=1.13, n=15 (too small to trust either way). This
run gives it a real multi-year sample: n=254, t_stat=4.77 (C1, fixed:63) — on its own, that raw
t-stat *looks* like a strong, statistically "significant" result, and a naive read would call this
confirmed. It is not. The calendar-matched placebo (same stock, same-length random holding
period) delivers 6.66% mean / 8.47% p95, both *above* C1's 6.10% mean — i.e., simply holding
the turnaround stock for 63 trading days starting on a random day beats holding it starting on
the earnings-announcement day. Turnaround's raw return is real (it is a genuinely up-trending
name in the 4 quarters after flipping to profit) but the *specific act of entering on the earnings
signal* adds nothing over the stock's ambient drift for that period — same pattern as prior
PEAD/trailing-stop work (the strategy is renting market beta from a hold-structure, not eating an
earnings-surprise edge). C2 (dma:50 trailing exit instead of fixed:63) is worse on every axis:
win% collapses to 38.2%, median goes negative (-1.08%), same placebo-miss. C6 (OR-widened
turnaround∪np_yoy≥100% bucket, n=1016) doesn't rescue it either — excess -1.33%, the worst
combo-vs-own-placebo margin after C7.

**Everything else in Family C fails the same way, by varying margins.** C7 (np_yoy top-decile,
126-day long-drift hold) has the largest raw mean (10.27%) but also the largest placebo miss
(-3.67pp) — the longest hold window is exactly where "just holding a name that had a good quarter"
harvests the most generic drift, which is the mechanism this desk has been burned by before.
C8 (quality-growth combo) and C6 both give up >1pp to placebo. The **closest-to-real signals**
are C5 (qoq, excess +0.40pp — the only combo with a positive mean-vs-placebo-mean gap in the
whole family, though it still misses the p95 bar: 4.43% vs 4.95%) and C9 (accel, excess -0.20pp,
n=2928 — largest sample in the whole 30-combo sweep, smallest miss). Neither clears the actual
bar (beats_placebo95), so per SPEC neither is a "real" result, but if Family A/B also come back
all-False, C5/C9 are the two worth a second look with a tighter placebo (they're not degenerate,
not censoring-driven — cens_pct 1.2%/7.2%, mean_ex_top2 nearly equals mean_net_pct for both,
so no fat-tail single-name carry).

**C10 surprise-weighted sizing is a flag, not a survivor.** SW mean (13.20%) is 2.4x the EW mean
(5.48%) on the *identical trade set* as C10/A2 (same signal/cut/hold — np_yoy top-decile,
fixed:63). That kind of jump from a np_yoy-magnitude weighting is the same shape as the firm's
debit-denominator lesson: weighting by an unbounded percentage-growth number lets a handful of
extreme-np_yoy names (small positive base, large swing) dominate the weighted mean. SPEC didn't
ask for a placebo comparison on the SW variant, so I am not calling this beats/fails — I am
flagging it: **do not quote the 13.2% figure anywhere without first checking weight
concentration** (top-3 weight share) before any escalation. Did not have EW/SW weight-share time
budget in this run; recommend Sameer Bhat's desk look at it if C10 is ever revisited.

## [OPINION] Bottom line for the 30-combo synthesis
Family C contributes **zero survivors**. The turnaround bucket — this family's reason for
being tested at all — is now conclusively answered: it does not clear its own calendar-matched
placebo at any hold structure tried (fixed:63 or dma:50), despite a properly-powered multi-year
sample and a t-stat that would have looked convincing without the placebo control. This is a
clean negative result, not a fragile one — the guard rails did their job. If FINDINGS.md ends up
needing a lower bar than beats_placebo95 (e.g., "smallest excess deficit") to surface any
candidate at all, C5 (qoq) and C9 (accel) are the least-bad in this family, on record above.

## Ops note — results.csv write race (flag for DESK-100 synthesis)
`run.py` does read-full-CSV → modify → write-full-CSV with no locking. Running Family C
concurrently with Family A/B agents caused **two silent lost-update clobbers**: my first C1–C10
write landed (log confirmed "12 rows"), then a concurrent Family-B write (which had read the file
before my write landed) overwrote it back down to 11 rows with all 10 C rows gone; I reran, it
landed at 21, then a concurrent Family-A finish did the same thing, dropping back to 20 with C
gone again. Ledgers on disk were never affected (each agent writes its own `ledgers/<ID>.csv`,
no shared file), so no data was actually lost, but results.csv briefly showed 11 and then 20 rows
mid-run, i.e. it is not safe to read results.csv as a status check *during* a multi-agent run —
only trust it once all family agents report done. I re-ran C1–C10 a third time after confirming
(via combo_id list) that A and B had both already finished, and it is now stable at 30 rows
(verified twice). Recommend `ops-engineer-manoj-pillai` add a file lock or move to per-family
CSVs + a merge step before this pattern is reused.
