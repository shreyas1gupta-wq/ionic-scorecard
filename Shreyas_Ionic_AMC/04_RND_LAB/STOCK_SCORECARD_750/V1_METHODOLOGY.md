# STOCK_SCORECARD — V1 OPERATING MODEL (frozen 2026-07-20)

**V1 supersedes V0 for production.** V1 is the leaner, **weekly-runnable, token-incremental** version.
The scoring engine, the Ionic Score, and the client Sell/Trim/Hold layer are UNCHANGED from
`FROZEN_METHODOLOGY.md` v6.3 — V1 changes only (a) the analyst's override power, (b) the fund-manager
pass weight, and (c) how a run is executed (incremental, not full every time).

## What changed vs V0
| | V0 (retired, preserved) | V1 (production) |
|---|---|---|
| Analyst override | full discretion, both directions | **asymmetric: Sell -> Hold only** |
| Analyst pass | deep (~3min + self-review) | focused **~2 min**, cached-thesis-anchored |
| FM pass | full judgment | quick **~1 min** (Trim target + one-line view) |
| Run mode | full research of every stock | **weekly incremental**: earnings -> full, news -> delta, else -> carry |

## 1. The pipeline
`quant score  ->  ~2min analyst  ->  ~1min fund manager  ->  client Sell/Trim/Hold sheet`

## 2. The analyst override is ASYMMETRIC (the core V1 rule)
The quant SCORE is the sole source of a Sell signal. The analyst may argue for leniency, never for
extra pessimism:
- Quant says **Sell** -> analyst MAY convert to **Hold** (a "rescue"), with a written reason. This is
  the analyst's only override.
- Quant says **Hold** -> analyst may **NOT** convert to Sell. A Hold stays a Hold.
- Rationale: the model is the disciplined pessimist; keeping Sell-creation with the model makes the
  book repeatable and defensible, and stops subjective, hard-to-audit Sell calls. A genuine "this
  should be a Sell but the score says Hold" case is an **escalation** to the Principal, not an override.
Enforced in code: `run_weekly_v1.apply_full()` / `apply_delta()` silently clamp any analyst Sell on a
score-Hold back to Hold and log `_override_blocked`.

## 3. Weekly cadence — the incremental router (token optimizer)
Each week `run_weekly_v1.py` reads per-stock state + the earnings feed and puts every covered stock in
ONE lane:
- **FULL** — a results print landed since the stock's last full research (deterministic, from
  `datasets/nse_earnings_dates/`). Redo the full ~2min analyst pass; the new quarter resets its thesis.
- **DELTA** — no earnings, but a cheap batched news-scan flagged something material (rating action,
  M&A, regulatory, management change). A ~30s look at JUST that news vs the cached thesis; update the
  rec only if warranted (asymmetric rule still applies).
- **CARRY** — nothing new. Keep the cached recommendation. ~0 tokens.
Only FULL + DELTA consume analyst tokens. On the seeded book, a normal week is a handful of FULLs;
a post-results-season week is ~10-20. Naive re-research-everything would be 125 every week.

## 4. Per-stock state (`pf_state/<SYM>.json`) — the memory that makes it incremental
Seeded from the 125 researches by `build_v1_scaffold.py`. Fields: symbol, version, coverage
(client_holding|universe), last_full_research_date, based_on_earnings_date, quant{scores, quant_rec},
analyst{rec, growth_pct, override_applied, summary}, fm{action, trim_to} (holdings only), escalation,
next_earnings_date, last_checked_date, **delta_log[]** (every weekly touch journaled: date, mode,
note, rec, changed / override_blocked), pf_qual_ref. The delta_log is the audit trail of what changed
and when, so we never re-derive a stock we already understand.

## 5. V0 is preserved (track record)
`V0_ARCHIVE_20260720/` is the immutable snapshot of all 125 V0 recommendations + the shipped
workbooks + scores. Do not edit. Purpose: score the V0 calls for hindsight accuracy later
(forward return vs Nifty 500, hit-rate / decile spread by cohort). Every future weekly run likewise
appends to state rather than overwriting history, so the full recommendation timeline stays auditable.

## 6. Scripts
- `09_PRODUCT/scripts/build_v1_scaffold.py` — archive V0 + seed pf_state (rerunnable).
- `09_PRODUCT/scripts/run_weekly_v1.py` — weekly router (plan) + `apply_full/apply_delta/apply_carry`
  state updates with the asymmetric-override guard.
- Client/analyst Excel builders (`build_client_excel.py`, `build_analyst_excel.py`) unchanged — a
  weekly run rebuilds them from the updated state + pf_qual after FULL/DELTA passes.

## 7. Unchanged from v6.3 (do not re-open)
Dual-horizon pillars + weights, regime tilt, gates/penalty/boost, the Ionic Score (0.60/0.40 + forward
adjustment, growth table, caps), the two-gate client Sell/Trim/Hold + concentration guidance, the
analytics layer, and all house-style / epistemic-conduct rules.
