# ALPHA_RANKER — Wave-4 Coverage Map (tested vs. genuine gap)
Compiled by Lakshmi Narayanan (Librarian), 2026-07-17. Machine-readable twin: `rnd/wave4/coverage_map.json` (97 entries; covers all 67 catalog rows, all 96 trials_counter families, and the catalog GAPS section).
Sources: FRAMEWORK_CATALOG.md (67 factors + GAPS), trials_counter.json (457 trials, 96 families), scoreboard_v2.csv (430 rows), SURVIVORS.md, CONSOLIDATION.md, KILLED.md, FINAL_MODEL.md §4 (canonical kill list), backlog.json, backlog_scout.json, card spot-reads (H035/H037/H040/H047/H049, W2 batch summaries). Every non-GAP status cites a card or doc line in the JSON. [DATA] throughout unless tagged.

## Summary by category
| Category | SURVIVOR | CANDIDATE | KILLED | DATA-BLOCKED | GAP-UNTESTED | UNKNOWN |
|---|---|---|---|---|---|---|
| Momentum | 3 | 1 | 5 | 0 | 1 | 0 |
| Value | 2 | 1 | 1 | 0 | 3 | 1 |
| Quality | 1 | 1 | 9 | 1 | 2 | 0 |
| Growth | 1 | 1 | 0 | 2 | 2 | 1 |
| Technical | 0 | 0 | 3 | 0 | 1 | 2 |
| Volatility | 0 | 2 | 0 | 0 | 0 | 1 |
| Flow/sentiment | 0 | 0 | 3 | 4 | 2 | 0 |
| Forensic | 1 | 1 | 0 | 2 | 4 | 1 |
| Composite (PMS + model) | 0 | 2 | 5 | 0 | 0 | 0 |
| Balance-sheet | 1 | 0 | 0 | 0 | 1 | 0 |
| Other families | 1 | 3 | 12 | 1 | 1 | 0 |
| Scout queue | 0 | 0 | 1 | 0 | 2 | 0 |
| Infrastructure (validation machinery) | 1 | 0 | 0 | 0 | 0 | 0 |
| **Total (97 entries)** | **11** | **12** | **39** | **10** | **19** | **6** |

Catalog GAPS section reconciliation: #1 sector-momentum tilt = CLOSED (tested, 1M leg); #2 quality-momentum overlay = CLOSED (MOMQ 6/6 PROMOTE*, rank-average preferred); #3 analyst-estimate feed = still DATA-BLOCKED; #4 TS momentum = still GAP; #5 Novy-Marx + asset-growth = CLOSED (both tested; asset-growth is a model leg, gross-profitability killed twice under two names — H021 and IDGG01).

## 1. GAP-UNTESTED (never tested, buildable from on-disk data) — raw material for wave-4
Ordered roughly by (data-readiness × prior). Items 12-15 carry a caveat: possible overlap with the un-enumerated H040 forensic composite — read `cards/H040_forensic_safety_1Y.json` construction before building.

1. **NLP tone on news/call-transcripts** (FinBERT prepared-vs-Q&A, QoQ tone delta) — data READY on disk: india_fin_news 125K + MiMIC 1,042 calls (`FACTOR_LIBRARY.md` L20). Largest untouched data asset.
2. **Stock-level valuation vs OWN 5-10y history percentile** (H016, queued, never run) — market-level analog already PROMOTE* (W2_market_M1/M3), stock-level is the open half.
3. **Reinvestment runway: ROIC × reinvestment rate** (H038, queued, never run) — adjacent Andrade capital-efficiency (IDG_I_02) tested 3× PROMOTE* and unadjudicated, so the family has live signal.
4. **Shareholder yield composite** (H039) — issuance component is already a SURVIVOR leg; test full composite only on an incremental-over-issuance bar.
5. **Earnings-inflection × multi-year-base-breakout coincidence** (MULTIBAGGER_DNA's universal setup) — needs the daily event-time harness W3_pead already built.
6. **PE-top-decile-of-own-history + growth-deceleration JOINT exit trigger** — the untested half of Anti-Marcellus; an equity-curve-layer test, not an IC test.
7. **Ex-dividend/bonus record-date drift** (W2S-13) — corporate-action dates on disk; reuse W3_pead event harness.
8. **Beneish M-score** (standalone) — PIT-buildable. (H040-overlap caveat.)
9. **Montier C-score** (standalone) — PIT-buildable. (H040-overlap caveat.)
10. **Receivables/inventory growth vs revenue divergence** — PIT-buildable. (H040-overlap caveat.)
11. **CWIP-to-assets never-capitalizing** — verify CWIP column coverage in fundamentals first (unverified).
12. **Time-series (absolute) momentum** for single stocks (catalog GAP #4) — buildable from prices.
13. **Earnings-yield vs bond-yield gap** — rate series on disk (W2_macro used one); frame as valuation adjustment, not regime switch.
14. **Moat-direction proxy: 5y gross-margin stability** (the codable slice of the moat factor / PMS #5 leg).
15. **Policy-lever / structural-theme catalyst tag** — sector_industry_map.parquet exists; partly judgment.
16. **Index-level PCR/OI overlays** (W2S-05/08/10) — index option data on disk; scope = exposure-scalar layer, and sibling max-pain (W2S-06) already killed → low prior.
17. **Base-length / multi-year-base accumulation** (price/volume part only) — adjacent kills (52w-high, VCP, stage-2) lower the prior.
18. **Passive index-weight-change pressure** (W2S-12) — buildable in reduced add/drop-event form from the 42 PIT snapshots (true weights not on disk).
19. **Hurst / trend-persistence** (H047, card says computable today) — but both sibling trend-quality tilts (R², frog-in-pan) killed as momentum-dilutive → cheapest-test-only.

Also unresolved but NOT new ideas (wave-4 housekeeping): adjudicate IDG_I_02 (Andrade, 3× PROMOTE*, never accepted/rejected); H043 beta-adjusted momentum (1× PROMOTE*, unadjudicated); validate the India-VIX panic-floor input of the exposure scalar (adopted-unvalidated per FINAL_MODEL §5a); independent lag-test for bs_asset_growth (5-RISKOFFICE flagged); fix the issuance proxy (bonus/split noise ~8%); the H028-size SURVIVORS-vs-FINAL_MODEL discrepancy (canonical: KILLED, resurrection = signed long-panel run clearing KB #17 cost hurdle).

## 2. DATA-BLOCKED (real idea, blocked on a feed we don't have)
| Idea | Blocking feed | Evidence | Priority note |
|---|---|---|---|
| **Promoter-buying drift / shareholding deltas** | fresh NSE shareholding/SAST (stale 2023-12; home-network pull) | W2S_flow_promoter cards: IC_IR 1.33, gates CLEAN, 17% coverage; CONSOLIDATION resurrection #1 | **Chase FIRST when data lands** — strongest blocked signal |
| Buyback / creeping-acquisition flag | same SAST/shareholding feed (403) | SYNTHESIS.md §5 non-codable | rides the same pull |
| Promoter pledge level & trend | same shareholding/pledge feed | 08_FORENSICS_REDFLAGS L22; no card | rides the same pull |
| Delivery-% accumulation/spike/divergence (H035, W2S-14/15) | delivery bhavcopy refresh (stale 2024-06) + panel columns | cards/H035_delivery_flow.json PARK | explicit parked card |
| Estimate-revision breadth/SUE | real analyst-estimate feed (Trendlyne = D-009 candidate, unapproved) | catalog GAPS #3 | proxy path (PEAD) is dead — no workaround |
| Forward earnings-growth trajectory/acceleration | same estimates feed | H025 trailing version tested, unconvincing | rides the same feed |
| Stock-level F&O positioning (OI buildup, strike-wall — W2S-07/09) | dense single-stock option OI (210-symbol coverage thin/patchy) | CONSOLIDATION cleanup pass; W2_OPT_DATA_COVERAGE.md | dual-schema landmine applies |
| Bulk/block deal flow (stock-level) | NSE bulk/block API (403, home-network) | FACTOR_LIBRARY L21 | FII/DII drift sibling already KILLED wrong-sign |
| Revenue durability (volume-led vs price-led) | segment/volume disclosure data | no source on disk | |
| Auditor/covenant/KMP-churn/RPT event flags | corporate-announcements + annual-report detail feed | no cards; Train.parquet annual_report corrupt (landmine #5) | hard-veto DESIGN rules, empirically untested |
| US/global macro regime (H049) | US/global index series (unwired; only India indices in factor_navs) | cards/H049_macro_regime.json PARK | cheap unblock (Stooq/FRED) but India-macro siblings all failed — low prior |

## 3. KILLED — DO NOT RETEST (resurrection condition beside each)
| Killed idea | Card/doc | Resurrection condition |
|---|---|---|
| PEAD (all grains) + W2S-01/02 variants + H037 | W3_pead_eventtime.json (n=2,642, IC −0.003) | **None — "PARKED for good"**, closed at both monthly and event-time |
| Weinstein stage-2 (H009) | LONG_H009 sign-flip; SURVIVORS red-team #5 | None — confirmed OVERFIT (sign-flip class = auto Gate-4 fail) |
| Regime return-blend overlays (H031, K-015, cont/band overlays) | CONSOLIDATION (root cause: gross-return shortfall) | Only as exposure-SIZING; never as score blending — no more variants |
| Short-term mean-reversion (H034 + K-stock-meanrev) | H034 cards; KILLED_IDEAS | Entry-timing overlay on existing trades only; no standalone re-tests |
| Raw growth CAGR (H024) | H024_1Y.json IC_IR −0.59 | None as a positive factor (growth-trap confirmed) |
| GARP/PEG/QARP/Greenblatt/magic-formula/Buffett's-alpha (H018/H030/H046/W2SEAS_garp/IDGG12) | FINAL_MODEL §4 | Only if an interaction beats EY-alone on incremental bar (three constructions already failed) |
| ROCE-longevity streak (IDG_I_03) | wrong-sign −0.79 | None — longevity is priced |
| Deleveraging momentum (IDG_I_06) | dead-cat, CONSOLIDATION | None stated |
| Under-owned value (IDG_I_04) | doesn't beat EY; stale 2023 data | Fresh shareholding data AND incremental-over-EY bar |
| Earnings stability (H023/W2SEAS_earn); seasonality (W2SEAS/CAPSTONE); SMILE | inverted / LOO passenger (ΔIC_IR −0.047) | Seasonality: new incremental case over the 7-leg base |
| Accruals & cash-conversion (H022/H045/IDG_G05) | beaten by cum-CFO/PAT on incremental bar | Only vs CFO/PAT incremental |
| 52w-high (H006/H041); RS-line (H007); VCP (H008); CANSLIM (H027) | scoreboard_v2 | None stated; 12-1 residual owns the space |
| MA sweeps (H001/H002/H042 distance constructs) | KILLED.md | Longer/less-autocorrelated panel or harness-owner sign-off on the PBO/DSR blanket-fail artifact; slope-only if revisited |
| Peer-relative (sub-sector) momentum | FINAL_MODEL §1 correction | None — 5yr-bull-panel artifact; plain wins on 21yr |
| Multi-lookback momentum blend (W2_volmom_blend3_6_12) | IC_IR 0.145 | None — 12-1 owns the family |
| Idio-vol, MAX-lottery, downside-beta, beta-standalone, vol term-structure (H011/H012/H013/H033/IDG_G07/IDG_G09) | FINAL_MODEL §4 | MAX: parked (1M lag-fail, nets ~0) — new data grain only |
| Size tilt (H028) | FINAL_MODEL §4 (canonical) vs SURVIVORS candidate note — discrepancy logged | Signed long-panel run + clear KB #17 smallcap cost-inversion hurdle (2.4-4.2pp/yr) |
| BAB standalone | dropped, corr 0.77 w/ QMJ | Orthogonality case vs QMJ |
| Frog-in-pan, trend-R² tilts (MOMQ_fiptilt/r2tilt) | FINAL_MODEL §4 | None — dilute momentum |
| NH-NL, breadth-divergence, dispersion scalars | CONSOLIDATION L21 | Non-additive vs %>200DMA scalar — none |
| FII/DII accumulation drift (W2S-03) | wrong sign | None as drift; DII-flow rank (K-B1c) = forward shadow-ledger only |
| Max-pain magnet (W2S-06) | p=0.134, n=153 | Denser expiry coverage (source only 33% date density 2021-24) |
| Sector rotation constructions (W2S-11 relPE+mom; IDG_I_15 sector-breadth) | net −12%/yr; gate-fail | None stated; small-N=15 sector IC series is structurally unstable |
| India macro regime conditioners (INR/rate/risk, W2_macro) | 4 FAIL/2 WEAK | Regime-as-sizing only |
| Ridge weight-learning (H050) | overfits vs rank-average | None — rank-average is canonical |
| OBV / volume-price divergence (H036) | FAIL_GATE | None stated |
| PMS composites #1/#2/#3/#4/#6/#7 | load-bearing legs killed individually (see JSON) | Per-leg conditions above; #7 additionally carries prior-art CAUTION (−3.7% 5yr alpha) |

## Cross-checks performed (anti-fabrication log)
- Every trials_counter family (96) is mapped to a JSON entry; families absent from trials_counter but carded (H035/H037/H047/H049, W2_macro, W3_pead) were card-read directly — three turned out PARK-not-run (H035 data-blocked, H047 deferred-buildable, H049 data-blocked), one deferred-but-superseded (H037).
- Differently-named-family traps caught: Novy-Marx tested as BOTH H021 and IDGG01 (gap flag stale → CLOSED); sector-momentum tilt tested as W2SEC/W2sector (gap flag stale → CLOSED); quality-momentum tested as MOMQ/H029 (gap flag stale → CLOSED); PEAD's "needs event-time" caveat closed by W3_pead_eventtime.
- Known open discrepancy carried, not resolved here: H028 size (SURVIVORS candidate vs FINAL_MODEL §4 rejected — canonical kill list wins, noted in both outputs).
- UNKNOWN used only for non-harness-testable items (qualitative/portfolio-layer): 6 entries.
