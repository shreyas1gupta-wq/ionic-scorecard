# Family A conclusions — pure earnings momentum / PEAD (Arjun Rao, 2026-07-16)

Run: `python run.py A1 A2 A3 A4 A5 A6 A7 A8 A9 A10` (re-run twice — see INFRA NOTE below).
All 10 ledgers confirmed in `ledgers/A1.csv` .. `ledgers/A10.csv`. All 10 rows confirmed in
`results.csv`.

## INFRA NOTE — results.csv race condition (flag for DESK-100 / ops-engineer)
`run.py` does read-CSV -> append own rows -> overwrite-whole-file, with no lock. Families A/B/C
ran concurrently; each overwrite clobbered the others' rows (classic lost-update). My first run
completed clean (10/10 rows, confirmed via stdout), but Family B's later overwrite wiped A1,
A3-A10 down to just A2 (which pre-dated my run). Ledger CSVs on disk were never touched (safe —
they're per-combo files, no shared-file race). I re-ran my batch after confirming both other
families' ledgers existed (i.e., they were done writing), which restored 10/10 A rows + the
pre-existing 10 B rows (20 total). **As of this writeup, results.csv has NO C-family rows** —
C's ledgers exist on disk (`ledgers/C1.csv`..`C10.csv`, all written) but were lost in the same
race and nobody has re-run C's IDs since. `run.py` needs a file lock or a per-family output file
merged at the end before FINDINGS.md synthesis, or this will keep happening.

## Combo table

| id | signal | cut | hold | n | win% | mean_net% | median% | t | ex_top1% | ex_top2% | cens% | placebo_mean% | placebo_p95% | beats_p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | np_yoy | pctile 0.90 | fixed:20 | 573 | 51.3 | 1.29 | 0.16 | 2.69 | 1.16 | 1.04 | 1.2 | 1.74 | 2.48 | **False** |
| A2 | np_yoy | pctile 0.90 | fixed:63 | 573 | 56.9 | 5.48 | 3.37 | 6.42 | 5.30 | 5.12 | 6.8 | 6.98 | 8.25 | **False** |
| A3 | np_yoy | abs>=100% | dma:50 | 762 | 36.9 | 3.04 | -1.26 | 4.77 | 2.86 | 2.68 | 0.1 | 4.39 | 5.29 | **False** |
| A4 | np_yoy | pctile 0.80 | fixed:40 | 1189 | 57.5 | 4.62 | 2.06 | 9.26 | 4.49 | 4.38 | 1.1 | 4.18 | 4.95 | **False** |
| A5 | sue | pctile 0.90 | fixed:20 | 596 | 52.7 | 1.70 | 0.34 | 3.99 | 1.59 | 1.52 | 2.2 | 1.23 | 1.80 | **False** |
| A6 | sue | pctile 0.90 | fixed:63 | 596 | 56.7 | 4.17 | 1.74 | 5.78 | 4.01 | 3.87 | 8.4 | 5.23 | 6.35 | **False** |
| A7 | sue | pctile 0.80 | dma:50 | 1144 | 39.1 | 2.58 | -0.99 | 5.57 | 2.37 | 2.25 | 1.1 | 3.54 | 4.10 | **False** |
| A8 | eps_yoy | pctile 0.90 | fixed:63 | 159 | 45.3 | 0.40 | -1.68 | 0.26 | -0.29 | **-0.91** | **29.6** | 3.56 | 5.80 | **False** |
| A9 | np_yoy | pctile 0.90 | fixed:63+stop:8 | 573 | 44.3 | 3.71 | -4.40 | 4.55 | 3.52 | 3.34 | 3.1 | 5.66 | 6.73 | **False** |
| A10 | sue | abs>=2.0 | fixed:40 | 982 | 57.2 | 4.08 | 1.89 | 8.59 | 3.94 | 3.83 | 1.6 | 5.11 | 3.94 | **True** |

(cost basis 0.67% RT / 1x; 2x-cost mean_net% not shown, see results.csv `mean_net_pct_2x` — all
combos lose roughly 0.4pp of mean at 2x stress, doesn't change any beats_p95 verdict.)

## Per-combo notes

- **A1/A2 (np_yoy top-decile, fixed 20/63)**: both lose to placebo, and lose by MORE at the
  longer hold (A2 margin -1.48pp vs A1 -1.19pp) — consistent with the handoff's warning that
  the hold structure itself harvests drift better than random entry does. No degenerate flags.
- **A3 (np_yoy>=100%, dma:50)**: win% 36.9%, **median negative** (-1.26%) despite positive
  mean — classic right-skew: most trades lose small, a few large winners carry the mean.
  mean_ex_top2 (2.68%) stays close to mean (3.04%), so it's not 1-2-name concentration, it's
  the trailing-stop payoff shape itself (small losses, occasional big rides) — same asymmetric
  pattern flagged in the 2026-07 Sharpe-artifact lesson, though here it doesn't inflate Sharpe
  since we're booking net-of-cost per exit-month, not spreading. Still loses to placebo by
  -1.35pp. cens% near zero (0.1%) — dma exit resolves almost everything by data-end.
- **A4 (np_yoy top-quintile, fixed:40)**: CLOSEST miss. mean 4.62% vs placebo_p95 4.95%
  (-0.33pp), and positive excess vs placebo MEAN (+0.44pp). Largest n in the family (1189),
  highest t-stat (9.26), low cens% (1.1%), ex_top2 barely below mean (4.38 vs 4.62) — clean,
  well-powered, just not quite over the real bar. Worth a note for FINDINGS but not a survivor.
- **A5 (sue top-decile, fixed:20)**: SECOND-closest miss, and the tightest margin in the whole
  family: mean 1.70% vs placebo_p95 1.80% (-0.10pp), positive excess vs mean (+0.47pp). Small
  edge, short hold, n=596, ex_top2 close to mean — clean signal, no red flags, just short of
  the bar. Same signal family (sue) as the actual survivor A10.
- **A6 (sue top-decile, fixed:63)**: cens% 8.4% — highest of the non-dma, non-A8 combos (63-day
  hold running closer to the panel's 2026-01-22 cutoff). Still a clean result shape (ex_top2 close
  to mean) but loses to placebo by -1.06pp.
- **A7 (sue top-quintile, dma:50)**: same shape as A3 — win% 39.1%, negative median (-0.99%),
  asymmetric trailing-stop payoff. Loses to placebo by -0.96pp.
- **A8 (eps_yoy top-decile, fixed:63) — FLAGGED, do not trust**: n=159 clears the nominal
  "hundreds" sanity floor per SPEC but the handoff's 82%-NaN warning shows up as real damage:
  engine's own degenerate detector fired **"one symbol >30% of |P&L|"** and **"negative without
  top-5 trades."** mean_ex_top2 flips NEGATIVE (-0.91%) against a barely-positive raw mean
  (+0.40%), t-stat is ~0 (0.26), median is negative (-1.68%), and cens% is 29.6% — nearly a
  third of trades are still open/unrealized marks, not real P&L. This is not merely
  underpowered, it is a 1-2-name artifact riding on a mostly-missing signal. Treat as FAKE,
  exclude from any leaderboard.
- **A9 (np_yoy top-decile, fixed:63+stop:8)**: hard 8% stop drags win% to 44.3% and median to
  -4.40% (stop triggers often), mean still positive (3.71%) but loses to placebo by -1.96pp —
  worst placebo-relative miss in the un-flagged part of the family. Stop-loss structure looks
  like it converts the same np_yoy signal into a worse risk/reward than the plain fixed:63 (A2),
  which already lost to placebo too.
- **A10 (sue>=2.0 absolute, fixed:40) — the one survivor, with caveats**: mean 4.08% clears
  placebo_p95 3.94% by **+0.14pp** — thin. t-stat is high (8.59) and n is large (982, second
  largest in the family) but that t-stat is testing mean-net != 0, not testing the excess over
  placebo — there's no direct significance test on the 0.14pp gap itself, and with K=200
  placebo resamples the p95 threshold itself has resampling noise on that order. cens% is low
  (1.6%) and mean_ex_top2 (3.83%) stays close to the raw mean (4.08%) — not tail-carried, not
  censoring-inflated. This is the cleanest pass in the family: absolute (not percentile-ranked)
  SUE threshold, fixed 40-day hold, no price filter. Read it as "worth a closer look with a
  wider placebo K and a fresh OOS slice," not as certified — one thin margin against one
  resampled percentile is not a DSR/PBO-grade result.

## Verdict

9 of 10 Family-A combos LOSE to their own calendar-matched placebo, confirming the handoff's
prior — the trailing-hold structure alone harvests more drift than the earnings signal adds.
**A10 (sue>=2.0, fixed:40) is the only nominal survivor** (beats_placebo95=True), by a thin
+0.14pp margin, clean on concentration/censoring — flag it for a second look (wider placebo K,
next OOS slice) but do not certify off this screen alone. **A8 (eps_yoy) is a FAKE/degenerate
result** — 1-2-name concentration, negative ex-top2 mean, 29.6% censored — exclude from any
FINDINGS.md leaderboard entirely, don't just call it "underpowered." A4 and A5 are honest
near-misses worth a footnote. Weakest assumption across the family: the dma:50 exit combos
(A3, A7) show negative medians masked by positive means — same asymmetric-payoff shape as
past Sharpe-artifact lessons, here not inflating a headline Sharpe but still a reminder that
"positive mean" and "positive edge" are not the same claim under this hold structure.
