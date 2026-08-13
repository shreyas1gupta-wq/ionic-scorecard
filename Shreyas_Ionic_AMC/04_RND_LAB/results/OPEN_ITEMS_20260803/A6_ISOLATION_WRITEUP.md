# A6 ISOLATED: the signal is REAL and survives correction — it was never TRADEABLE
**2026-08-04 · DESK-100 · attribution completed by the coordinator from the agent's banked ablations**

## The question
`A6_vwap_proxy_continue` was reported at **+4.153 index pts, t_NW 2.576, placebo p=0.000, n=9,655**, and
I described it to the Principal as the second-best cell in the book. `NEWDIM_LEVELS_20260731` then found
that the consumer of `chain_features_15min.parquet` selects a NON-FRONT expiry via a naive
`drop_duplicates("bucket")`, and reported that the VWAP continuation side "did not replicate at the same
strength" once corrected — but attributed the gap to several simultaneous differences without isolating
the cause. This resolves it.

## The ablation ladder

| cell | n_build | mean pts | t_NW | hit | max-day share | placebo p |
|---|---|---|---|---|---|---|
| **A6 ORIGINAL (buggy selector)** | 9,655 | **4.153** | 2.576 | 53.84% | 0.087 | 0.000 |
| **A6 CORRECTED SELECTION ONLY** | 9,923 | **3.887** | 2.450 | 54.27% | 0.101 | 0.000 |
| + daily trade cap | 1,621 | 3.412 | 2.074 | 52.31% | 0.098 | 0.000 |

Reproduction was **exact** on all four statistics of the original before any ablation ran, so the
pipeline is faithful and the comparison is valid.

## The attribution: the defect cost 0.266 points, i.e. 6.4%
**4.153 → 3.887.** With front-week selection corrected and *everything else held identical*, the signal
loses **6.4%** of its edge. Hit rate actually *improves* (53.84% → 54.27%) and n rises (9,655 → 9,923).
The signal is essentially intact.

**So NEWDIM's non-replication was METHODOLOGY, not the defect.** The remaining gap belongs to the daily
trade cap, sigma choice and ATR exits, and the one cap ablation that ran shows the cap alone accounts for
more (3.887 → 3.412) than the expiry defect did.

### Why a defect affecting 51.3% of buckets moved the number only 6.4%
The re-measured mismatch rate is **51.3% of 32,397 common buckets — twice the 25.6% NEWDIM reported**,
and I had passed the 25.6% figure to the Principal. Yet A6 barely moves, because **A6 is primarily a
price/VWAP signal that merely happens to be computed alongside chain columns.** Mis-selecting the expiry
changes the chain context without changing the price signal underneath.
**This means the defect's impact is CELL-DEPENDENT, and A6 was the least-affected cell we could have
picked.** The genuinely expiry-specific cells are the ones still at risk:
`A3`/`A4` (OTM strike concentration) and `A7`–`A10` (OI-quadrant momentum) all depend directly on which
expiry's OI and strike ladder is read. **None of them has been re-run.** Their `stage1_report.json`
numbers remain unverified and should not be quoted.

## The cost overlay — and this is what actually settles it
A6's sample spans 2021-05-24 to 2026-06-03. **Measured mean spot over that window: 20,788** (460,477
bars), so the cost must be computed there rather than at today's 24,000 — STT scales linearly with spot
and using today's level overstates the historical hit. That error is one I made myself today and two
agents caught it independently.

| basis | STT | + non-STT 1.97 | + slip 0.5 | round trip | **A6 net** |
|---|---|---|---|---|---|
| OLD 0.02% | 4.16 | | | **6.63** | **−2.74** |
| NEW 0.05% | 10.39 | | | **12.86** | **−8.98** |

**A6 needed 6.63 points gross to break even and delivered 3.887 — a 2.74-point shortfall on the OLD cost
basis, before the STT hike existed.** At the new basis the shortfall is 8.98 points.

## Verdict
**The signal is real. It was never tradeable.**
- Real: placebo p=0.000, n=9,923, max-day share 0.101 (well distributed, not one lucky day), t_NW 2.450,
  and it survives correction of a defect affecting half the buckets.
- Not tradeable: a ~3.9-point gross edge against a 6.63-point cost floor then, 12.86 now.

This is the same wall every other family hit — gross edges of 2–5 index points against a cost floor of
6–7 points, now 13–15. **A6 is not an exception to that pattern; it is another instance of it.** My
describing it as the second-best cell in the book was accurate about the *signal* and silent about the
*cost*, which is the part that mattered.

## Disclosed deviations
- Placebo draws reduced from the pre-registered 200 to **50** for wall-clock. Disclosed by the agent at
  runtime, not discovered afterward.
- The full ablation ladder (sigma variants, ATR-exit variants) did **not** complete — the agent stalled
  four times on this box and hit an `ArrayMemoryError` trying to allocate 1.18 MiB, with free RAM at
  2–3GB while several agents ran. Two of five ablations landed. The two that matter — corrected-selection
  and the daily cap — are the two that decide the attribution, so the conclusion stands, but the sigma
  and ATR-exit contributions remain unquantified.

## Files
`task1_a6_isolate.py` · `task1_ablation_stage.py` · `task1_a6_isolation.json` · `task1_run.log` ·
`stage_sigma1.log` · `_sig_corr_cache.parquet`
Defect flag at source: `INDICATOR_MINE_20260730/KNOWN_DEFECT_chain_features_dedup.md`
Corrected selector: `NEWDIM_LEVELS_20260731/chain_front.py` → `chain_front_15min.parquet`
