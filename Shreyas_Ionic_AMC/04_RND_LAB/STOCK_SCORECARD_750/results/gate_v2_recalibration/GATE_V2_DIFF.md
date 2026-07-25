# Balance-sheet gate v2 — recalibration diff (Principal-approved 2026-07-25)

**Ratified calibration** (amends FROZEN_METHODOLOGY §Overlay gates):

| Context | D/E RED / AMBER | Cover RED / AMBER | Note |
|---|---|---|---|
| Default (incl. Realty) | >2.5 / >1.5 | <1.5 / <3.0 | realty leverage IS the risk — no relief |
| Utilities / Power | >4.0 / >2.5 | <1.2 / <2.0 | regulated cash flows |
| EPC / Construction / Cement | >3.0 / >2.0 | <1.5 / <3.0 | industry-normal WC leverage |
| Jewellery (gold-metal loans) | >4.0 / >2.5 | <1.5 / <3.0 | hedged inventory financing |
| Lease-heavy (airlines/hotels/QSR/flex-space) | D/E leg OFF | <1.5 / <3.0 | Ind-AS 116 inflates D/E |
| Financials | exempt (unchanged) | — | bs_flag = N/A-financial-sector |
| **Negative equity** | **always RED** | — | no context rescues it |
| **Debt-free fix** | — | cover leg fires only if D/E > 0.3 | loss-making ≠ levered; profitability lives in the Quality pillar |
| PSU / sovereign backing | one-notch relief (RED→AMBER, AMBER→GREEN) | — | never on negative equity |
| Promoter-group backing | NO automatic relief | — | analyst-confirmed only, logged (3 candidates flagged in diff) |

**Blast radius (full 750):** 52 names change flag/penalty → `gate_v2_full750_diff.csv`.
Transitions: 21 AMBER→GREEN, 10 RED→AMBER, 10 RED→GREEN, 5 RED stay RED (negative equity),
1 GREEN→RED (DIACABS — negative equity that v1's `D/E>2.5` test could not see), 5 financial-sector
penalty-only fixes (debt-free cover flags removed).

**Recommendation changes: 14** — 13 Sell→Hold (INDIGO, SWIGGY, MEESHO, URBANCO, NAZARA, ATHERENERG,
ACMESOLAR, WEWORK, SMARTWORKS, ASHOKA, JUBLFOOD, LLOYDSENT, SOBHA), 1 Hold→Sell (DIACABS).
IDEA / GMRAIRPORT / TTML stay Sell (RED = automatic Sell, frozen rule).

**Client 59-book effect:** TATAPOWER, TITAN, BHEL de-AMBER under v2 (scores rise ~15%);
their calls are analyst-governed and unchanged (TATAPOWER analyst Sell stands on leverage
direction). PPLPHARMA stays AMBER (no qualifying context).

**Caveats:** quant-layer recompute (validated: median reproduction error 0.000 vs the engine;
residual carries the +3 clean-bill boost). Analyst `your_recommendation` still overrides where
research exists. The 3 group-context names (ADANIGREEN, JSWENERGY, ADANIENSOL class) get NO
automatic relief — analyst confirmation of demonstrated group support required.
DIACABS: verify negative equity is distress, not buyback-driven, before acting.

Engine integration: apply `gate_v2()` + `lev_flags(v2)` from `scripts/gate_v2.py` at the next
quarterly full re-score; this diff is the sign-off artifact.
