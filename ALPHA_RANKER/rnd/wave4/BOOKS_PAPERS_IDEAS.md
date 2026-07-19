# Books & Papers mining pass -- WAVE-4 (Prof. Aditya Verma, R&D Head)

Mandate: mine investor books + academic papers for TESTABLE, ORTHOGONAL signals in the CYCLE/REGIME,
CROSS-ASSET, and durable-single-name-anomaly lanes -- explicitly NOT the single-name factor lane
(52w-high, Amihud, NOA, shareholder-yield, downside-beta, frog-in-the-pan, fundamental-momentum are the
parallel Fable agent's territory) and NOT re-litigating anything already in FRAMEWORK_CATALOG.md (67
factors), CONSOLIDATION.md, SURVIVORS.md, KILLED.md, FINAL_MODEL.md, IDEAS_GLOBAL.md (30 PMS/AMC-framework
hypotheses, IDG-G/IDG-I), or SCOUT_OPPORTUNITIES.md (22 more, W2S/W2SEC/W2MKT).

**Prior-art check result: this ground is heavily mined already.** Before drafting anything I read the full
catalog stack AND the parallel Fable/Opus session's fresh output (`wave4/hypotheses_w4.json`, 16 ideas,
`wave4/FRONTIER_OPUS.md`) that landed mid-task. Three of my initial candidates turned out to be exact
duplicates of ideas that session had just queued -- dropped immediately rather than re-proposed:
- **Capex/R&D intensity** -> already queued as **W4-02** (CWIP commissioning / capex-cycle inflection, priority H).
- **Cross-asset FX spillover (USDINR-driven, Asness-style)** -> already queued as **W4-09** (Currency-sensitivity
  rotation, macro-beta x macro-trend).
- **Profitability GROWTH (not level)** -> already covered by **IDG-G-15** (Profitability improvement / delta-ROA),
  tested and in the CONSOLIDATION record.
- **Leading regime classifier for SIZING (Dalio/Marks true cycle-timing)** -> already Opus's own #4-ranked
  direction and queued as **W4-14**; not re-proposed, only cross-referenced where a data field overlaps.

**Also explicitly NOT re-proposed (protocol-closed, not data-blocked):**
- **PEAD-quality-of-reaction.** `CONSOLIDATION.md` "WAVE-3 REJECTED-SOURCES RESURRECTION PASS" re-tested PEAD at
  true event-time (n=2,642 real earnings prints, IC -0.003, p=0.87, flat/negative sub-window drift) and closed
  it explicitly: *"PARKED for good, no further granularity variants"*. A quality-conditioned cut of PEAD is
  precisely the kind of granularity variant that verdict just closed the door on. Flagging per prior-art
  discipline, not proposing.
- **Analyst-dispersion / estimate-revision breadth.** Already firm-flagged DATA-BLOCKED in `IDEAS_GLOBAL.md`
  (no I/B/E/S or Trendlyne feed on disk; Trendlyne is an unapproved D-009 candidate). Restated in the BLOCKED
  list below for completeness, not re-derived.

## What survived the cross-reference: 4 genuinely new mechanisms

All four are cheap (existing on-disk data, one harness pass each), each a **distinct economic mechanism**,
and each explicitly checked against the 7 legs of the frozen composite (EY, QMJ, PLAIN residual momentum,
MA-65 slope, net-share-issuance, asset-growth, CFO/PAT) plus the 16 sibling wave-4 hypotheses for overlap.
Full machine-readable entries: `rnd/wave4/hypotheses_w4_books.json`.

| ID | Name | Source | Priority | Mechanism (one line) |
|---|---|---|---|---|
| W4B-01 | Credit-cycle (Minsky) sector tilt via BankNifty relative strength | Minsky financial-instability hypothesis (via Marks' credit-cycle positioning) | **H** | Bank-sector relative strength leads credit-dependent cyclicals (construction/capex/auto) vs defensives |
| W4B-02 | Distress-composite (adapted Ohlson O-score / Campbell-Hilscher style) | Ohlson (1980); Campbell-Hilscher-Szilagyi (2008); Dichev (1998) distress-risk-puzzle | **H** | Bankruptcy-probability composite; distressed firms earn LOWER returns -- distinct from any single leverage/quality leg already in the model |
| W4B-03 | Gold-vs-equity momentum as a Dalio-quadrant sector tilt | Dalio economic-machine / all-weather (adapted proxy -- true India CPI/growth data blocked) | **M** | Real-asset/pricing-power sectors vs long-duration growth sectors, conditioned on gold-vs-equity regime |
| W4B-04 | Sector-level calendar seasonality | Heston-Sadka seasonality, re-granularized to sector (monsoon/festive/budget cycles) | **M** | Aggregation may isolate genuine India structural calendar drivers the noisy name-level version (already dropped as a passenger) could not |

**Count: 4 total. H=2, M=2, L=0.**

Two of the four (W4B-01, W4B-02) are unambiguously new axes with no data caveats beyond normal disclosure.
The other two (W4B-03, W4B-04) are flagged with an explicit **pre-gate check** each -- they sit close enough
to existing work (W4-14's use of the same gold_vs_equity_1m field; the already-dropped name-level seasonality
card) that the very first, cheapest step is a correlation check against that existing card's scores, BEFORE
any full harness run. This is the "cheapest falsification first" discipline applied to the mining step itself,
not just to the eventual test.

## Why the cycle/regime lane (Dalio/Marks/Minsky) yielded so little net-new material

`IDEAS_GLOBAL.md` had already explicitly evaluated Dalio and Marks and ruled most of their content
OUT-OF-SCOPE for a cross-sectional stock-selection ranker: *"Dalio -- a portfolio-construction & macro-overlay
method, not a stock-selection cross-section... our regime-probability overlay (CONSOLIDATION wave-3) is the
in-house expression"* and *"Marks -- a market-level exposure/timing read... partially expressed by
W2MKT-01... not a per-stock score."* Checked and confirmed true: `rnd/panel/macro_state.parquet` (127 monthly
rows, 2016-2026) has India CPI/WPI, India 10Y yield, Brent, and DXY all explicitly **PARKED** (per
`macro_state.py`'s own docstring: no series found on disk, stooq blocked, home-network/RBI DBIE fetch needed)
-- so the TRUE Dalio growth x inflation quadrant cannot be built at all today, only proxied. W4B-01 and W4B-03
are the two constructions that survive this constraint by re-purposing existing macro_state/index columns as
CROSS-SECTIONAL SECTOR TILTS (a genuinely different question -- which names to prefer -- from the market-level
SIZING use those same fields already have in W4-14 and the breadth/VIX exposure scalar). This is the honest
maximum extractable value from this literature given current data; the rest is correctly out of scope.

---

## BLOCKED (data not on disk -- do not build; flagging for the Data Officer / Principal, not auto-fetching)

| Idea | Literature | Blocked on | Unblock path |
|---|---|---|---|
| Broad commodity momentum (Gorton-Rouwenhorst) | Gorton-Rouwenhorst (2006) commodity risk premia | No broad/industrial-metals commodity index on disk; only gold/silver ETF proxies exist (`datasets/etf_gold_silver/`). Brent and DXY explicitly PARKED in `macro_state.py` (stooq blocked, verified 2026-07-17). | Home-network commodity index pull (D-033-conditional, needs Data Officer D-009 verification + DATA_CATALOG entry) |
| True Dalio growth x inflation quadrant | Dalio *Principles*/economic-machine | India CPI/WPI, IIP/GDP nowcast, India 10Y G-sec real yield -- none found anywhere on disk (checked `ALPHA_RANKER/data/`, `datasets/`, `Shreyas_Ionic_AMC/05_DATA_OFFICE/data/`); `macro_state.py` leaves `real_rate_proxy` as NaN for exactly this reason | RBI DBIE / MOSPI CPI-WPI-IIP series (home-network pull, D-033-conditional) |
| Analyst-dispersion / estimate-revision breadth (Chan-Jegadeesh-Lakonishok) | Named "single most reliable 1Y signal" in own reading list | No I/B/E/S or broker-consensus feed on disk; Trendlyne flagged but unapproved (D-009 pending) | Approved estimate-revision feed (Trendlyne D-009 or equivalent) -- already flagged firm-wide in `IDEAS_GLOBAL.md`, restated here only for this brief's completeness |
| Koijen-style rates/FX "carry everywhere" as a single-stock cross-sectional factor | Koijen-Moskowitz-Pedersen-Vrugt (2018) carry everywhere | The clean India single-stock analogue (dividend/shareholder yield) is explicitly the parallel Fable single-name agent's lane -- not proposed here to avoid duplication; a genuine cross-asset carry construction (funding-cost differential, ADR-carry) has no clean India equity-level data on disk | N/A -- redirect to the single-name agent's shareholder-yield work rather than unblock separately |

---

## Files
- `rnd/wave4/BOOKS_PAPERS_IDEAS.md` -- this file.
- `rnd/wave4/hypotheses_w4_books.json` -- 4 machine-readable entries, schema matches `hypotheses_w4.json`
  (id, name, source, construction, expected_sign, data_assets, orthogonality_vs_7legs, money_rationale,
  priority, refinement_allowed, caveats).
