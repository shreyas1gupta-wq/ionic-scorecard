# GATED OPTION BUYING — 0.6 delta / ITM-100 / ITM-50 at RR 1:1.5
**2026-07-30 · DESK-100 · 36,061 simulated legs · 87 scored cells · verdict: NO**

## The ask
Principal: *"FIND HIGH CAGR STRATEGIES USING OPTION BUYING ONLY 0.6 DELTA OR ITM 100/50 POINT
STRIKE AND BEST HARVEST RISK REWARD ATLEAST 1:1.5"*

## Verdict
**0 of 87 cells has a positive pessimistic mean at n≥100.** Not one. In-sample (2021-2025) and
held-out (2026) both. All 87 cells passed pathsafe's reliability check, so none of this is a
fill-convention artifact.

## Strike selection verified on spec
| rule | n | measured delta mean | median | min | max |
|---|---|---|---|---|---|
| delta0.60 | 12,045 | **0.602** | 0.602 | 0.500 | 0.698 |
| itm100 | 11,904 | 0.664 | 0.649 | 0.516 | 0.988 |
| itm50 | 12,112 | 0.590 | 0.579 | 0.491 | 0.971 |

Delta was inverted from each strike's own traded price via Black-Scholes, not assumed. ITM-50 lands
at 0.59 delta — i.e. the Principal's "0.6 delta" and "ITM 50 points" are the same instrument in
practice. ITM-100 sits slightly higher at 0.66.

## The mechanism — this is the useful part
**Hit rate clusters at 40–43% in-sample. Breakeven at RR 1:1.5 is exactly 40.0%.**

| best in-sample cells (n≥200) | n | hit% | mean (pess) |
|---|---|---|---|
| IV=MID itm100 stop15 | 790 | **42.78%** | −0.321 |
| C1 delta0.60 stop15 | 748 | 42.51% | −0.379 |
| C2 delta0.60 stop15 | 748 | 42.51% | −0.379 |

The 1:1.5 harvest is priced FAIRLY. Gross of cost, buying at 0.6 delta with a hard stop is a
coin-flip that lands within ~2 points of hit rate of its own breakeven. The **entire** loss is the
1.77-premium-point round trip (₹25/lot/side = 0.385 pts ×2, plus 0.5 slippage ×2).

Required hit rate to clear cost at stop 15 / target 22.5: **44.7%.** Best observed: 42.78%.
The gap is 1.9 points of hit rate and no tested condition closes it.

## The IV/RV gate (B2) does NOT transfer to the option vehicle
B2_vix_rv_divergence_low was the only indicator cell to clear the Bonferroni bar on the UNDERLYING
(+4.584 index pts, t=4.029, placebo p=0.000). At the option level it adds nothing:

| IV state (delta0.60, stop15) | n | hit% | mean |
|---|---|---|---|
| CHEAP | 828 | 41.1% | −0.99 |
| MID | 794 | 41.8% | **−0.45** ← best |
| RICH (control) | 857 | 40.4% | −0.98 |

CHEAP ≈ RICH, and MID beats both. **The B2 gate was noise at the option level.** The +4.58 index
points are real but get consumed by the option's theta and spread before reaching the buyer. This
is the honest disposition of the one indicator that cleared its bar.

## Held-out 2026 is materially worse
Hit rate falls to **30–37%**, mean −2.60 to −5.52, every cell negative. Consistent with the
Oct-2024 structural break (see below) and with the 2025+ alpha decay the Principal flagged.

## What was run
- Triggers, all pre-registered from INDICATOR_MINE_20260730 and all placebo-cleared there:
  A6 vwap-continue (16,759 legs), C1/C2 sweep-reclaim 30/45min (9,651 each)
- Strikes: measured-delta 0.60, ITM-100, ITM-50
- Stops: 10/15/20/25 premium points; target always 1.5× stop (RR exactly 1:1.5)
- Exits via `lib/pathsafe.simulate_exit` — target is a resting limit, stop resolves ADVERSELY,
  both intra-bar bounds returned. Quoted numbers are the pessimistic bound throughout.
- Scheduled event days excluded; premium <₹5 excluded; 2026 held out.

## Files
`gated_buying.py` (build) · `report.py` (scoring) · `trades.parquet` (36,061 legs) ·
`cells.csv` (87 cells) · `run_log.txt` · `report_log.txt`

## Note on a guard firing correctly
The first run crashed in the report layer: I passed duck-typed stand-ins to `pathsafe.summarize()`
and it raised rather than scoring them. That is the module working as designed — it refuses to
summarise anything that did not come from `simulate_exit()`. The scoring was split into `report.py`
with real `ExitResult` objects. No result was affected; the 36,061 legs were already on disk.
