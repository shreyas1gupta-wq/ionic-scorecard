# Hypothesis one-pager — Expiry / reconstitution / turn-of-month seasonality
_Intake 2026-07-03 · R&D (Aditya Verma) · RESEARCH_SOP §template · stage 1-INTAKE_

- **Name:** `expiry_seasonality` — calendar-mechanical effects (expiry pin, index reconstitution, turn-of-month).
- **One-line edge:** Predictable, calendar-driven flows — expiry-day pinning/settlement, forced index-rebalance buying/selling, and turn-of-month inflows — create small, repeatable price and OI patterns we can position around because the flow is *mandatory*, not opinion-driven.

- **Economic WHY (who loses money to us, why do they keep doing it?):**
  This is the cleanest **structural/forced-flow** WHY in the queue. The losers are **price-insensitive forced traders**: index funds and ETFs that MUST buy the added name / sell the deleted name at (or near) the reconstitution close regardless of price; option writers/hedgers who must settle at expiry causing pin-to-strike; and month-end institutional flows. They keep doing it because their **mandate forbids opinion** — a Nifty tracker cannot decline to buy an inclusion, it is contractually obligated. Forced flow → temporary price pressure → mean-reversion or drift we can pre-position. This is textbook "who loses money to us and can't stop": they are paid to track, not to trade well.

- **Factor sleeve:** Event & Seasonality (FACTOR_LIBRARY §Proprietary — corporate actions, quarterly patterns, index reconstitution, expiry effects; data READY).
- **Universe:** NIFTY / BANKNIFTY (OI surface, expiry effects); NIFTY-500 constituents at reconstitution events (index add/drop names from the 42 PIT snapshots).
- **Holding period:** 1–10 trading days per effect (expiry: intraday-to-days; reconstitution: entry pre-effective, exit post-inclusion, ~1–2 weeks; turn-of-month: a few days around the turn).
- **Expected decay horizon:** These are famous and partly arbitraged (McLean-Pontiff decay applies), BUT forced flow does not fully disappear — it re-prices to a thinner residual. Reconstitution effect in India has attenuated but persists around effective dates. **Live structural break to flag below.**
- **Capacity estimate:** UNKNOWN, effect-specific. Expiry effects on NIFTY/BANKNIFTY options are capacious (deep index book); single-name reconstitution capacity is bounded by the add/drop name's float and the rebalance size — estimate per effect at cheap-test.

- **⚠ LIVE STRUCTURAL BREAK TO FLAG (pre-registered, do not average across it):**
  NSE moved the **monthly expiry to Tuesday (effective ~Sept-2025)** — a regime change in the expiry-day calendar. Any expiry-seasonality study that pools pre- and post-Sept-2025 data **will contaminate the day-of-week signal**. This MUST be handled as a hard regime cut: pre-Sept-2025 (old expiry-day convention) vs post-Sept-2025 (Tuesday monthly). Treat post-break data as the only regime that describes the live world; pre-break is context, not out-of-sample confirmation of the current effect.

- **Data needed (on disk? Y/N per DATA_CATALOG):**
  - NIFTY+BANKNIFTY OI surface — `datasets/derived/` OI surface, **633K rows** — **Y** (§1) [books]. Max-pain / PCR / pin inputs.
  - PIT index snapshots — **42 PIT snapshots 2005-2025** (`NIFTY500_TICKER_2005_2025_Final.xlsx`) — **Y** (§3) — these ARE the reconstitution add/drop events, survivorship-clean (landmine #6).
  - NIFTY/index daily + 1-min — **Y** (§2); 1-min carries auction landmine #2 and the pre-open 09:00-vs-09:15 open bug (MEMORY: filter time≥09:15 or gap calcs corrupt on ~94% of 2026 days).
  - Corporate actions — `datasets/derived/corporate_action_factors` (613 events) — **Y** (§3) for turn-of-month / ex-date overlaps.
  - Exact effective-date calendar for the Tuesday-expiry change — verify precise effective date with Data Officer before the regime cut (do not hard-code from memory).

- **Cheap-test design (the single cheapest falsification):**
  Three cheap event studies, **post-Sept-2025 regime only** for anything expiry-day-of-week dependent:
  (a) **Reconstitution:** on the 42-snapshot add/drop events, measure the add-names' abnormal return from announcement→effective→post, vs a matched control — the canonical forced-flow test.
  (b) **Expiry pin:** distance of settlement from nearest high-OI strike (max-pain) on the OI surface, post-break Tuesdays.
  (c) **Turn-of-month:** mean index return on the ±3-day turn window vs the rest of the month.
  Pre-register kill thresholds before touching data; run the *cheapest* (reconstitution event study on data already on disk) first.

- **Pre-registered KILL criteria:**
  1. Reconstitution add-name abnormal return (ann→effective) **not distinguishable from a matched-control placebo** → KILL that effect.
  2. Expiry pin: settlement-to-max-pain distance **no smaller than a random-strike null** in the post-Sept-2025 regime → KILL the pin effect.
  3. Turn-of-month spread **< +5 bps over the window net of nothing** (i.e. not even gross-material) → KILL that effect.
  4. **Any headline effect that only exists when pre- and post-Sept-2025 data are pooled → KILL** (it's the regime break masquerading as a signal, not a tradeable pattern).
  5. Effect exists gross but **cannot survive 2× COST_STANDARDS** given its small per-trade magnitude → demote to context, not a sleeve.

- **Trials run so far on this family:** **0** (new family; no prior seasonality variant in KILLED_IDEAS or the register).

- **Cheapest falsification (closing line):** Run the index-reconstitution event study on the 42 PIT add/drop snapshots already on disk — measure add-name abnormal return from announcement to effective date vs a matched control — and kill the effect if it is indistinguishable from a matched-control placebo, all while keeping the post-Sept-2025 Tuesday-expiry regime strictly separate from the old convention.
