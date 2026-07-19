# W6SB — Sector-Bias Audit on the 7-leg Capstone Composite

Arjun Rao (Head of Quant), 2026-07-17. Script: `rnd/wave4/w6sb_sector_bias_audit.py`
(run synchronously, foreground, single pass, no retries needed). Cards:
`rnd/wave4/cards_w6sb/W6SB_TASK{1..5}_*.json`.

**Trigger**: Principal's point — earnings-yield (EY) is structurally biased:
financials/utilities run low P/E by business model (leverage/regulated
returns), and cyclicals show high EY (cheap-looking) at peak trailing
earnings just before a downturn. Part of the composite's "value edge" may be
a hidden long-financials/short-IT SECTOR BET, not cross-stock stock-picking
alpha.

## Data lineage
- `rnd/panel/panel_long.parquet` — 148,297 rows, 969 symbols, 2005-04-29 to
  2025-12-05, `sector` col (22 macro buckets, same source `build_panel.py`
  joins — n750 Industry).
- `rnd/panel/capstone_legs.parquet` — 1,310,958 rows, 12 legs (used the 7
  canonical: value_EY, mom_resid_plain, trend_ma65_slope, quality_QMJ,
  bs_issuance, bs_asset_growth, quality_cfo_pat — per `composite_pit.py`
  `TRUE7`, NOT the cached `mom_resid_peer`, see note below).
- Target: `fwd_ret_1Y_resid` for IC (matches CANONICAL_7LEG_1Y's
  `return_basis="resid"`), `fwd_ret_1Y_raw` for decile long-short / Brinson.
  Corporate-action guard applied: `disc_event_in_window_1Y>0` rows dropped
  (1,215 of 148,297 rows — same guard as the canonical card).
- **Methodology validation**: raw composite reconstruction here reproduces
  `CANONICAL_7LEG_1Y.json` almost exactly (ic_mean 0.1890 vs card's 0.1890;
  ann_return_LS 3.696 vs card's 3.696) — confirms the audit's raw-side
  construction is faithful before touching the sector-neutral side.
- **momentum-leg note**: the canonical composite's momentum leg is
  `mom_resid_plain` (residual vs NIFTY500 only, rebuilt fresh here via
  `run_long_confirm.build_mom_resid_12_1`, exactly as `composite_pit.py`
  does) — NOT the cached `mom_resid_peer` in capstone_legs.parquet, which is
  already `sector_analytics.peer_relative(..., level="sub_sector",
  method="z")`-transformed upstream. Cross-checked: cached mom_resid_peer's
  raw IC = 0.0626, close to this audit's own sector-neutral mom-resid IC of
  0.0643 (task 3) — consistent, independent confirmation.

## Guards passed
Corp-action guard applied. PIT discipline: sector-neutral ranks and the
cyclical peak-earnings flag are computed with EXPANDING (not centered/full-
sample) windows — no lookahead. min_names_per_date=20 (matches
`harness.evaluate` default) for pooled IC; min_peers=5 for sector-date rank
buckets (smaller buckets dropped, not fabricated).

## TASK 1 — sector composition of raw EY deciles (145 dates)
| | Financial Svcs | Metals & Mining | Chemicals | Oil&Gas | Power | Capital Goods |
|---|---|---|---|---|---|---|
| **Long (top decile, cheapest)** | 22.5% | 13.6% | 11.8% | 11.1% | 9.4% | — |
| **Short (bottom decile, priciest)** | 17.6% | — | — | — | 6.7% | 13.4% |
| Universe weight | ~16.3% | ~4.0% | ~7.8% | ~3.3% | ~3.6% | ~13.7% |

HHI (sector concentration): top decile 0.128, bottom decile 0.093, universe
0.117. **Long book concentration is HIGHER than universe** (0.128 vs 0.117),
driven by Metals & Mining at 3.4x its universe weight and Oil&Gas at 3.4x.
Financial Services is large in absolute terms in BOTH long and short legs
(22.5% vs 17.6% — heavily represented on both sides, so it is not a clean
long-financials/short-financials bet net, but Financials + cyclicals
(Metals/Chemicals/Oil&Gas/Power) together are 68% of the long book vs a
combined ~35% universe weight).

**Verdict Task 1: YES — raw EY IS a sector tilt**, concentrated long
Financial Services + Metals & Mining + Chemicals + Oil Gas + Power (all
structurally-low-P/E or commodity-cyclical sectors), short Capital
Goods/Telecom/FMCG.

## TASK 2 — sector-relative EY vs raw EY
| | ic_mean | ic_ir | ann LS return | n dates |
|---|---|---|---|---|
| Raw EY | 0.0774 | 0.76 | not separately re-run (see Task 3 table) | 154 |
| Sector-neutral EY (rank within macro_sector) | 0.0517 | 0.58 | | 154 |

IC retention after sector-neutralization: **66.8%** (delta −0.0257). The edge
SURVIVES but is meaningfully smaller — roughly a third of raw EY's IC was a
sector bet, two-thirds is genuine within-sector stock selection.

## TASK 3 — per-leg raw vs sector-neutral IC (all 7 + composite)
| leg | raw IC | neutral IC | delta | retention |
|---|---|---|---|---|
| EY | 0.0774 | 0.0517 | −0.0257 | 66.8% |
| mom-resid (plain) | 0.1113 | 0.0643 | −0.0469 | 57.8% |
| MA65 | 0.0957 | 0.0550 | −0.0407 | 57.5% |
| QMJ | 0.1461 | 0.0930 | −0.0530 | 63.7% |
| **issuance** | 0.0609 | 0.0242 | **−0.0368** | **39.7%** |
| asset-growth | 0.0351 | 0.0252 | −0.0099 | 71.8% |
| cfo-pat | 0.0386 | 0.0452 | **+0.0065** | **117%** (survives fully, no sector tilt) |
| **COMPOSITE (7-leg)** | **0.1890** | **0.1132** | **−0.0758** | **59.9%** |

**Issuance is the single most sector-contaminated leg (only 40% of its raw
IC is genuine cross-stock alpha)** — worse than EY. cfo-pat is the only leg
that is NOT a sector bet (IC unchanged/slightly higher net of sector). All
other legs (momentum, MA65 trend, QMJ quality) lose 35–45% of their raw IC
to sector — this is not an EY-only problem, it is a composite-wide
construction gap.

## TASK 4 — cyclical peak-earnings value-trap check
- Raw EY IC within cyclical sectors only (Metals, Capital Goods, Autos,
  Oil&Gas, Construction, Cons.Materials, Power, Realty): **0.0662** (n=151
  dates) vs non-cyclical: **0.0731** (n=154). Edge is slightly weaker in
  cyclicals but still clearly positive — no collapse.
- Peak-earnings test (expanding, PIT-safe, own-history top-quartile of
  sector-mean EY, ≥24mo history required, "cheap" = top quintile of pooled
  cyclical raw EY that date): forward 1Y raw return of cheap-cyclical picks
  made **at** a sector-EY peak = mean 0.545 / median 0.282 (n=613) vs made
  **not** at a peak = mean 0.371 / median 0.155 (n=4,176). Winsorized (1/99%)
  means: 0.53 vs 0.35. **Peak-regime picks did BETTER, not worse** — no
  value-trap signature found in this sample. Caveat: peak-flag dates
  cluster 2018–2022 (21 of 76 in 2020 alone, 16 in 2022) — the result is
  likely dominated by the COVID crash/recovery and 2021-22 commodity
  supercycle, where "sector EY at its own historical high" mostly meant
  genuine price-crash cheapness rather than an earnings-peak trap; EY alone
  cannot distinguish the two mechanisms. **Not a clean refutation of the
  trap thesis generally — an artifact of a crash-heavy sample window.**

## TASK 5 — Brinson decomposition (sector-timing vs stock-selection)
| | ann total LS | ann sector-timing | ann stock-selection | % from sector timing |
|---|---|---|---|---|
| EY alone | −0.034 | +0.225 | −0.259 | not meaningful (total ≈0, ratio explodes) |
| **COMPOSITE (7-leg)** | **3.047** | **1.258** | **1.789** | **41.3%** |

Cross-check: composite's raw IC (0.189) → sector-neutral IC (0.113) is a
40.1% cut; raw ann-LS (3.696) → sector-neutral ann-LS (1.532) is a 58.6%
retention (41.4% cut) — **two independent methods (Brinson decomposition on
raw returns, and full sector-neutral reconstruction on resid returns) agree
to within 1 point: ~41% of the composite's edge is a sector bet, ~59% is
genuine stock selection.**

EY alone shows a striking pattern: its raw (non-resid) long-short return is
near ZERO (−3.4%/yr), decomposing into a *positive* sector-timing effect
(+22.5%) offset by a *negative* stock-selection effect (−25.9%). This means
EY's positive IC (measured against benchmark-residualized returns) largely
reflects sector/factor exposures that the "resid" target already strips out
— on RAW returns, cheap-within-sector EY picks alone would have LOST money
net of the sector tilt over this sample. This is the clearest single piece
of evidence that EY's apparent edge is sector/beta-exposure-dependent, not
robust bottom-up stock selection.

## Degenerate flags
None of Sharpe>4 / win>75% pattern checked here (out of scope, IC-level
audit only). Flag: EY's raw-vs-resid Brinson split (above) is itself a mild
degenerate signature — an "edge" that flips sign between return bases is
fragile, not robust.

## Verdict
**FRAGILE, not FAKE.** The 7-leg composite's edge is REAL but roughly
40–41% sector bet / 59–60% stock-selection, confirmed by two independent
methods. EY, momentum, MA65 trend, and QMJ quality all lose 35–45% of raw
IC to sector; issuance loses 60% (worst); cfo-pat loses none (best,
already sector-clean). Single weakest assumption: the composite is
currently built with full-universe cross-sectional ranking (no sector
neutrality step) for 6 of 7 legs — the ~41% sector-timing share is an
UNPRICED, uncontrolled bet the model is silently taking, not a designed
exposure with its own risk budget.

## Recommendation
1. Make **issuance, mom-resid (plain), MA65, QMJ, EY** sector-relative
   (rank/z within macro_sector or sub_sector) — in that priority order by
   IC lost. cfo-pat can stay as-is (no sector tilt found); asset-growth is
   borderline (72% retention, lowest priority).
2. Composite's ~41% sector-timing share should either be (a) removed by
   switching all legs to sector-neutral construction (expected new
   composite IC ≈0.113, ann-LS ≈1.53 — the sector-neutral figures already
   computed in Task 3), or (b) kept but EXPLICITLY budgeted as a sector-
   rotation sleeve with its own risk limits, not smuggled inside a
   "stock-selection" value/quality/momentum composite.
3. Do NOT claim the composite's published ~0.19 IC / ~370% ann-LS is pure
   stock-picking alpha — restate as ~59% stock-selection (IC ≈0.11,
   ann-LS ≈1.5–1.8) + ~41% sector-timing, and certify/size each piece
   separately.
4. The cyclical-peak value-trap hypothesis is NOT supported in this sample
   (peak-regime cheap cyclicals did better, not worse) — but the test is
   confounded by a crash-heavy window (2020/2022); do not treat this as a
   general refutation, re-test once a non-crash-dominated OOS window
   accumulates.
