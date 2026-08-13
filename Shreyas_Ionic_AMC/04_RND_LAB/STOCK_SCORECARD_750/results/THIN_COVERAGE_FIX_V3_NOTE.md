# Thin-history fix v3 — FINAL (v3 columns beside v1; engine untouched)

751 names. Replication verified: max composite diff 0.0000.

## What changed vs v2

- **No withdrawals.** v2 withdrew 8 names; v3 scores every one (Principal: a large cap like Swiggy can legitimately be thin).
- **1-year siblings substituted** where a 3-year pillar is unavailable (backtest: rank corr 0.906 -> 0.932, MAE 3.86 -> 2.72).
- **Listing-price technical** for <1y names: return since listing, ranked over the same window (rank corr 0.601 -> 0.701 at 3 months, 0.735 at 12; no added bias).
- **50/25/25 redistribution REJECTED on measurement** — it scored worse than the bug (bias +3.07 vs +2.95, MAE 11.83 vs 10.08, corr 0.445 vs 0.601). Neutral-fill used instead.
- **Call taken on the blended score**, so no name above 40 is ever a Sell.

## Coverage

- history: full **667**, 1-2y **45**, <1y **39**
- names receiving a 1y-sibling or listing-price substitution: **137**
- <1y names given a listing-price technical: **0**
- growth artefacts neutralised: **6** (SPARC, TSFINV, NSLNISP, ONESOURCE, JIOFIN, TARC)

## Forward adjustment (implemented for the first time — it was missing)

- growth leg, banded on the analyst's expected EPS growth ALONE (100% EPS / 0% revenue, matching v1): mean **+0.82** pts
- conviction leg: analyst Sell **191** at -6, analyst rescue of a quant-Sell **35** at +6
- net adjustment: mean **-0.50**, range -20 to +16
- base vs Ionic: median 49.5 -> 49.5

## Analyst-AI conversions

- **21** names the quant would have sold are held on analyst conviction (the Sell->Hold path the Principal asked to keep)
- **26** Holds are trim-ELIGIBLE on the analyst's view, **188** on the 40-50 score band (weight decides, at book level). Sell rate 26% (the frozen note expects ~33%).
- gates: liquidity now caps at 50; D/E exemption widened to financial services, power, realty, telecommunication, construction -- names whose balance-sheet flag improved: **5**

## Recommendation change

| | v1 (either horizon <40) | v3 (Ionic + analyst gate) |
|---|---|---|
| Sell | 246 | 199 |
| Hold / Trim band | 505 | 552 |

- of the v3 Holds, trim-eligible for any reason: **195**

## Largest score corrections (3Y, v3 minus v1)

| symbol | history | pillars | v1 | v3 | change | imputation |
|---|---|---|---|---|---|---|
| AIIL | full | 5 | 66.6 | 50.4 | -16.2 | growth_3y<-1y |
| ONESOURCE | 1-2y | 5 | 41.9 | 27.0 | -14.9 | growth_3y<-1y |
| UNIONBANK | full | 6 | 71.0 | 57.4 | -13.7 | growth_3y<-1y |
| KTKBANK | full | 6 | 67.8 | 55.0 | -12.8 | growth_3y<-1y |
| SKFINDUS | <1y | 3 | 79.8 | 67.7 | -12.1 | stage_3y<-1y,accumulation_3y<-1y |
| KSB | full | 4 | 62.4 | 50.4 | -12.0 | growth_3y<-1y |
| ABB | full | 4 | 72.1 | 60.8 | -11.3 | growth_3y<-1y |
| TMCV | <1y | 3 | 74.6 | 63.5 | -11.0 | stage_3y<-1y,accumulation_3y<-1y |
| CIEINDIA | full | 4 | 69.2 | 58.2 | -10.9 | - |
| J&KBANK | full | 6 | 73.2 | 62.3 | -10.9 | growth_3y<-1y |
| SAMMAANCAP | full | 5 | 51.9 | 41.4 | -10.5 | growth_3y<-1y |
| CANBK | full | 6 | 71.8 | 61.4 | -10.5 | growth_3y<-1y |
