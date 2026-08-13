# v3 freeze audit

**20 of 21 hard invariants pass.**

| # | invariant | result | detail |
|---|---|---|---|
| 1 | no Sell at or above 40 | PASS | 0 violations |
| 2 | no non-Hold above 50 | PASS | 0 violations |
| 3 | every name below 40 is a Sell | PASS | 0 violations |
| 4 | only two calls exist at universe level | PASS | values ['Hold', 'Sell'] |
| 5 | no Sell is marked trim-eligible | PASS |  |
| 6 | 40-50 band eligibility set exactly on the band | PASS |  |
| 7 | analyst-view eligibility implies an analyst Sell | PASS |  |
| 8 | scores within [5,95] | PASS | range 5.00 to 87.82 |
| 9 | no NaN scores | PASS | 0 NaN |
| 10 | adjustment = growth + conviction, clamped 20 | PASS |  |
| 11 | Ionic = base + adjustment (pre-cap) | PASS | max diff 0.0000 |
| 12 | analyst Sell never gets a net uplift | PASS |  |
| 13 | expected growth <10% never gets a net uplift | PASS |  |
| 14 | conviction leg only ever -6/0/+6 | PASS | values [np.float64(-6.0), np.float64(0.0), np.float64(6.0)] |
| 15 | growth leg only ever on the frozen bands | PASS | values [np.float64(-15.0), np.float64(-5.0), np.float64(0.0), np.float64(5.0), np.float64(10.0), np.float64(15.0)] |
| 16 | rescued names never below -5 on the growth leg | PASS |  |
| 17 | rescue only fires on FORWARD revenue >15% and expected EPS <10% | PASS |  |
| 18 | rescue never fires on trailing revenue | PASS | the whole point of the forward-only correction |
| 19 | all financials exempt from the balance-sheet gate | PASS |  |
| 20 | no exempt-sector name flagged RED on D/E alone | PASS |  |
| 21 | most names on March-to-March | **FAIL** | 0% |

## Observations (not failures)

| item | value |
|---|---|
| Sell rate | 26% (frozen note expects ~33%) |
| double-count risk | growth-leg and conviction-leg correlation +0.24; 95 names charged by both |
| revenue rescue | 0 applied; 23 names eligible on EPS but DORMANT — expected_next_3y_revenue_growth_pct not yet in the research files |
| trim-eligible Holds | 195 (188 on the score band, 26 on the analyst view) |
| analyst rescues suppressed | 7 of 35 blocked by the low-growth cap |
| names at the -20 clamp | 16 |
| bottom band | 32 names under 20 |
| thin history | 84 names, 0 given a listing-price technical |
| earnings-quality flags | OI-driven 75, level 140, spike 81 |
