# IDEAS_GLOBAL — global-investor frameworks mined for cross-sectional edges (ALPHA_RANKER)

Compiled by Prof. Aditya Verma (R&D), 2026-07-17. Curated extraction of the CORE testable
principle of each named framework, adapted to Indian equities and OUR data reality.

- **15 queued** as pre-registered hypotheses in `rnd/backlog_scout.json` (IDG-G-01..15) — all
  buildable from data on disk (panel/panel_long, cube_close(_long), MASTER_fundamentals_pit [ANNUAL],
  stock_valuation_pit, sector_map), all orthogonal to the confirmed durable core
  (residual momentum / MA-slope / earnings-yield), all with a published economic rationale.
- Everything below is **DATA-BLOCKED or out-of-scope for the cross-sectional ranker** — NOT queued.
  Kept here so we do not re-derive them and so the resurrection trigger (new data) is explicit.

## DATA-BLOCKED (do not queue until the gating data arrives)

| Framework / source | Core testable principle | Why blocked now | Unblock trigger |
|---|---|---|---|
| **Estimate-revision breadth / SUE** — Asness, Chan-Jegadeesh-Lakonishok | Net analyst upgrades + magnitude → forward returns ("single most reliable 1Y signal") | No analyst-estimate feed on disk (Trendlyne/Bloomberg BEst is a D-009 candidate, unapproved). PEAD proxy already queued as W2S-01/02. | Approved estimate feed (Trendlyne D-009 or Bloomberg BEst dump) |
| **Anti-Marcellus quarterly-deceleration exit** — SageOne (PMS study candidate #1, highest-confidence codable rule) | Sell when trailing-4Q growth decelerates <8% for 2 consecutive quarters | MASTER_fundamentals_pit is ~99% ANNUAL (verified); no clean quarterly PAT/revenue series for the 8-quarter / 2-consecutive-quarter logic | Quarterly PIT fundamentals (screener quarterly scrape) |
| **O'Neil CANSLIM "C" (current quarterly earnings accel)** | Latest-quarter EPS acceleration + RS | Same annual-only limitation; "A" (annual growth) + RS are partially covered by momentum, "C" needs quarterly | Quarterly PIT fundamentals |
| **Concall / news NLP tone** — FinBERT rubric | QoQ management-tone delta, evasion markers → returns | Data exists (india_fin_news 125K, MiMIC 1,042 calls) but it is a separate NLP pipeline, not a clean PIT-joined cube factor; no per-(date,symbol) tone series built yet | A built, PIT-stamped `tone(date,symbol)` panel |
| **Wyckoff accumulation / OBV / delivery-based distribution** — Wyckoff | Volume-price effort-vs-result, delivery-% accumulation | Delivery data is stale (2022-2026 only, flagged stale 2024) and does not span the 21yr panel where bears live | Fresh + long-history delivery-% series |
| **Buyback / creeping-acquisition pre-purchase screen** — Aequitas | Flag recent promoter buyback / creeping acquisition | Needs SAST/buyback filings (403 for us at office); shareholding deltas partially covered by W2S-04 | Home-network / approved SAST filing feed |

## OUT-OF-SCOPE for a cross-sectional stock-selection ranker (kept for completeness)

- **Dalio** — economic-machine regime / risk-parity / all-weather: a portfolio-construction &
  macro-overlay method, not a stock-selection cross-section. FRED US-macro is proxy-blocked
  (stooq/home-network only). Our regime-probability overlay (CONSOLIDATION wave-3) is the
  in-house expression of the regime idea.
- **Marks** — "where are we in the cycle": a market-level exposure/timing read. Partially
  expressed by the market-state work (W2MKT-01, cheap-market-vs-history → forward market return),
  not a per-stock score.
- **Druckenmiller / Soros** — reflexivity, liquidity-driven positioning: macro/liquidity, no
  clean cross-sectional stock construct on our data; discretionary by nature.
- **Buffett/Munger moat DIRECTION, CAP duration, TAM/optionality** — Dorsey moat taxonomy: the
  quantifiable parts (profitability, low leverage, stable earnings, low reinvestment-free growth)
  ARE queued via IDG-G-01/02/12/14; moat *direction* and TAM are qualitative/judgment scores,
  not backtestable as a factor.
- **Minervini/Zanger VCP, Darvas box, Livermore pivotal points, Wyckoff springs** —
  technical entry-TIMING patterns. Firm prior-art: standalone price breakouts are dead
  (K-postbreakout-orb) and ADX/stage entry-gating never beat the exit (K-adx-atr-family,
  K-AF07-stage-turn). Admissible ONLY as timing overlays on names already selected for other
  reasons, judged against a same-exit placebo — not as cross-sectional selection factors.
- **Amihud illiquidity premium** — buildable (|ret|/volume from cubes) but our own lesson is that
  honest costs INVERT the size/illiquidity premium (KNOWLEDGE_BASE #17); would be a cost-fragile
  factor. Deferred, not queued, pending a real execution-realism overlay if ever revisited.
