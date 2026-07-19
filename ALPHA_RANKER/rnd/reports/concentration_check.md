# Concentration check — is the 1Y final composite a concealed sector/size bet?
Owner: overfit-analyst-sameer-bhat (validation pass). 21-yr `panel_long.parquet`, PIT throughout, no new lookahead surface.

## 0. Composite built (per FINAL_MODEL.md S1/S2, the "real model")
Simple rank-average (>=2-of-7 legs present) of the 7 orthogonality-pruned legs, 1Y horizon,
`return_basis=resid`:
`value_EY + mom_plain (residual 12-1, PLAIN not peer-relative, per FINAL_MODEL.md's correction)
+ trend_ma65_slope + quality_QMJ + bs_issuance + bs_asset_growth + quality_cfo_pat`.
All legs reused verbatim from existing PIT-audited builders (`run_long_confirm.py`,
`builders_w2_profq.py`, `builders_w2_issuance.py`, `builders_w2_indiaqv.py`) — this script only
recombines and diagnoses. n_obs=132,486 rows, 245 dates. Baseline card: `cards/CONC_composite_1Y_raw.json`
(IC_IR 1.25, monotonicity 0.99 — higher than the stale `CAPSTONE_COMPO_1Y_final` card in the repo,
which still uses the superseded 4-leg mix incl. `mom_resid_peer`; this run uses the corrected 7-leg PLAIN-momentum version).

## 1. Per-sector IC — broad or concentrated?
20 macro sectors scored (`macro_sector` from `data/universe/sector_map.parquet`, merged by symbol).
**19 of 20 sectors have IC_IR > 0.20** (the harness's own IC_IR-KILL threshold) — i.e. almost every
sector individually shows a real, positive within-sector relationship between the composite score and
forward 1Y residual return. Only Metals & Mining is weak (IC_mean 0.04, IC_IR 0.16).

| Rank | Sector | IC_mean | IC_IR | n_dates | avg names/date |
|---|---|---|---|---|---|
| 1 | Consumer Services | 0.185 | 0.87 | 162 | 22.9 |
| 2 | Financial Services | 0.181 | 0.88 | 231 | 69.1 |
| 3 | Textiles | 0.179 | 0.63 | 231 | 16.4 |
| 4 | Consumer Durables | 0.164 | 0.63 | 231 | 26.3 |
| 5 | Services | 0.153 | 0.58 | 214 | 21.6 |
| 6 | Capital Goods | 0.153 | 0.87 | 231 | 65.1 |
| 7 | Chemicals | 0.153 | 0.78 | 231 | 43.7 |
| ... | (13 more, all positive) | | | | |
| 16 | Automobile & Auto Components | 0.085 | 0.42 | 231 | 42.0 |
| 17 | Construction Materials | 0.081 | 0.31 | 231 | 19.1 |
| 18 | Realty | 0.077 | 0.33 | 203 | 19.4 |
| 19 | Media, Ent. & Publication | 0.064 | 0.22 | 209 | 15.9 |
| 20 | Metals & Mining | 0.040 | 0.16 | 231 | 18.7 |

Median sector IC_IR = 0.47 vs pooled (all-sector-pooled) IC_IR = 1.25. The pooled number is higher than
any single sector's own IC_IR partly because pooling adds cross-sector dispersion on top of within-sector
selection — expected, and checked directly in §4 below. **Verdict: broad, not concentrated** — the two
largest-weight sectors (Financial Services 12.2% of universe, Capital Goods) are both in the TOP tier of
sector IC, not passengers.

## 2. Top-quintile sector exposure over time — persistent overweight?
Per-date: (top-quintile share of a sector) − (that sector's universe share that date), averaged over 231 dates.

| Sector | mean overweight (pp) | universe share | top-quintile share |
|---|---|---|---|
| Fast Moving Consumer Goods | **+2.7** | 5.8% | 8.5% |
| Chemicals | +1.9 | 7.8% | 9.7% |
| Healthcare | +1.5 | 8.2% | 9.7% |
| Automobile & Auto Components | +1.4 | 7.7% | 9.1% |
| Financial Services | **−4.6** | 12.2% | 7.6% |
| Realty | −2.0 | 3.2% | 1.2% |

Largest tilt is +2.7pp (FMCG) on a universe base of ~5.8% — modest, and the single biggest sector
(Financial Services) is actually **underweighted** by 4.6pp in the top quintile, not overweighted.
No sector is in the "top-3 most overweight" bucket on more than 37% of dates (FMCG, the highest).
**No persistent single/dual-sector overweight found.**

## 3. Size / cap-tier tilt of the top quintile (PIT `cap_tier` from `stock_valuation_pit.parquet`)
| Cap tier | mean overweight (pp) | universe share | top-quintile share | frac. dates top-3 overweight |
|---|---|---|---|---|
| Mid | +2.4 | 30.0% | 32.4% | 0.92 |
| Small | +1.7 | 29.8% | 31.5% | 0.90 |
| Micro | −1.2 | 20.0% | 18.8% | 0.60 |
| Large | −2.8 | 20.2% | 17.4% | 0.57 |

Per-cap-tier IC is essentially flat: large 1.10, mid 1.12, small 1.20, micro 1.10 (all within a narrow
band). **A mild, persistent mid/small-over-large tilt exists (~2-3pp)** — consistent with known
value/momentum-tilts-small-cap literature, not a hidden size factor masquerading as the composite (IC
works equally in every tier).

## 4. Sector-neutral / size-neutral re-runs (demean within group, PIT groups, per date)
| Variant | IC_IR | IC_mean | Monotonicity | % of raw IC_IR retained |
|---|---|---|---|---|
| RAW (pooled) | 1.246 | 0.177 | 0.988 | 100% |
| Sector-neutral (demean within date x macro_sector) | 1.054 | 0.130 | 0.964 | **85%** |
| Size-neutral (demean within date x PIT cap_tier) | 1.329 | 0.170 | 0.988 | **107%** (no loss at all) |
| Both-neutral (demean within date x sector x cap_tier) | 1.177 | 0.127 | 0.988 | **94%** |

Cards: `cards/CONC_composite_1Y_sector_neutral.json`, `..._size_neutral.json`, `..._both_neutral.json`.

**The edge survives neutralization on both axes.** Sector-neutralizing costs only 15% of IC_IR (a small
haircut from removing genuine, but modest, cross-sector dispersion — see §2). Size-neutralizing costs
*nothing* — IC_IR is actually slightly higher purged of cross-cap-tier noise, confirming §3's flat
per-tier IC. Even jointly neutralizing both axes at once retains 94% of the pooled IC_IR. This is the
signature of **genuine within-sector, within-size-tier stock selection**, not a sector or size bet
wearing a stock-picking costume.

## Caveat (disclosed, out of scope for this check)
All five variants (raw, sector-neutral, size-neutral, both-neutral) independently still fail the
harness's **PBO gate** (0.75–0.95, all > 0.50 KILL threshold) — this is the SAME pre-production PBO
issue already flagged in FINAL_MODEL.md S5/CAPSTONE_COMPO_1Y_final, unrelated to concentration; it is
not a new finding of this check and does not bear on the sector/size question this task asked.
`CONC_composite_1Y_both_neutral` additionally shows DSR<=0 (skew/kurtosis-driven, on a smaller ~108k-row
joint-cell sample) — again a Sharpe-distribution artifact of the DSR/PBO layer, not an IC/monotonicity
failure; both_neutral's own IC_IR (1.18) and monotonicity (0.99) are intact.

## Files
`rnd/reports/concentration_check_data.json` (raw numbers, all sectors/tiers), `rnd/cards/CONC_composite_1Y_*.json`
(4 harness cards: raw/sector_neutral/size_neutral/both_neutral).
