# Hypothesis one-pager — PEAD via available_date (beat/miss drift)
_Intake 2026-07-03 · R&D (Aditya Verma) · RESEARCH_SOP §template · stage 1-INTAKE_

- **Name:** `pead_available_date` — post-earnings-announcement drift, PIT-clean.
- **One-line edge:** After a quarterly earnings surprise, prices drift in the surprise direction for weeks; go long the biggest beats / short-or-avoid the biggest misses, entered strictly on the `available_date` (when the number was actually public), sized to liquid names only.

- **Economic WHY (who loses money to us, why do they keep doing it?):**
  Classic Bernard-Thomas under-reaction — the market anchors on prior expectations and updates too slowly to an earnings surprise. The losers are slow-updating retail and analysts who revise estimates with a lag; they keep doing it because belief revision is sticky (anchoring) and career-safe (move with consensus, not ahead of it). It is a **behavioral** premium, amplified **structurally** in India by thin analyst coverage on mid/small-caps — fewer eyes means slower incorporation. We win by mechanically acting on the surprise the day it is knowable, not the day the crowd's attention arrives.

- **Factor sleeve:** Earnings Revision (FACTOR_LIBRARY §Traditional — PROXY: beat_miss + PEAD via available_date; real estimates feed is a D-009 Trendlyne candidate, NOT yet approved).
- **Universe:** 210 F&O names for the tradeable book; scoring can run on the wider PIT set. **Liquidity gate mandatory** (see family history — the prior kill was illiquidity contamination).
- **Holding period:** 20–60 trading days (the drift window; Bernard-Thomas ~60 days, decays over the quarter).
- **Expected decay horizon:** Medium. PEAD is one of the most-published anomalies → post-publication decay is real (McLean-Pontiff), but it has persisted in EM/India with coverage frictions. Assume attenuated-but-alive; the edge lives in the low-coverage tail, which is exactly where liquidity bites.
- **Capacity estimate:** UNKNOWN pending the liquidity overlay. The honest tension: the strongest drift is on thinly-covered mid-caps, which is where the previous kill happened. Capacity is whatever survives a *tradeable-ADV* filter on the 210 names — estimate at cheap-test.

- **Data needed (on disk? Y/N per DATA_CATALOG):**
  - PIT quarterly earnings — `datasets/earnings_pit/unified_quarterly_pit.parquet`, **86.2% exact available_date** (2025: 95.3%, 2026: 98%) — **Y** (§3). THE join key. [books] count.
  - Beat/miss (SUE proxy) — `datasets/derived/earnings_beat_miss.parquet`, **31,891 rows** — **Y** (§3). [books]. This is a *proxy*, not real SUE — flag it.
  - Earnings calendar — `datasets/nse_earnings_dates/earnings_dates.csv` 2020-01→2026-07 — **Y** (§3).
  - Prices — Stock daily (HF) **Y** but **stale tail →2026-01-22** (landmine #1); Angel daily 2026 bulk Feb–Jul-2026 covers the recent drift windows. 2005-2026 long history + 42 PIT snapshots exist for survivorship.
  - Real analyst estimates (for true SUE, not proxy) — **N** — Trendlyne feed is a **D-009 gate** candidate (Data Officer + Principal), NOT auto-fetch.

- **FAMILY HISTORY (honest — read before triage):**
  PEAD was **killed once pre-firm**, before this formal KILLED_IDEAS ledger existed, on **illiquidity contamination** — the drift concentrated in names that could not actually be traded at the assumed price (bid-ask + impact ate the paper drift). It is therefore **not a K-row in KILLED_IDEAS.md today**, but it is a real prior attempt and **must be counted in the trials ledger** (see below). The resurrection premise this one-pager rests on: PEAD is legitimate *only* with an ex-ante tradeable-liquidity gate and PIT `available_date` entry — the two things the prior attempt lacked. This directly echoes KNOWLEDGE_BASE lesson 3 (no outcome-selected/untradeable filters) and lesson 5 (binary-event strategies degrade off large-cap).

- **Cheap-test design (the single cheapest falsification):**
  Decile/quintile event study on the beat/miss proxy: sort by proxy surprise at `available_date`, form top-minus-bottom, enter at `available_date+1 open`, hold 20 days, **on liquid names only** (pre-registered ADV floor). Report the drift spread and CAR *net of a tradeable-ADV filter* and compare against the *illiquid* bucket — the whole point is to show the edge does NOT live only in the untradeable tail. Pre-register kill threshold before touching data.

- **Pre-registered KILL criteria:**
  1. Liquid-bucket (ADV ≥ pre-registered floor) top-minus-bottom 20-day drift **< +1.5%/event gross** → KILL (the prior illiquidity kill repeats; no tradeable edge).
  2. Drift present in the illiquid bucket but **absent in the liquid bucket** → KILL (confirms it was always microstructure, not information).
  3. Result flips sign or vanishes when entry is moved from a naive report-date to true `available_date` → KILL (it was lookahead).
  4. Any pass that requires the real-estimate (Trendlyne) feed → **HOLD, route to D-009**, do not claim a pass on unapproved data.

- **Trials run so far on this family:** **1** (the pre-firm illiquidity-contaminated PEAD attempt — counted for DSR honesty; not a K-row because it predates the ledger).

- **Cheapest falsification (closing line):** Sort the beat/miss proxy by surprise at `available_date`, enter `available_date+1 open` hold 20 days **restricted to an ex-ante ADV floor**, and kill the family if the *liquid-bucket* top-minus-bottom drift is under **+1.5%/event gross** or exists only in the illiquid bucket — proving the prior kill was structural, not just under-tested.
