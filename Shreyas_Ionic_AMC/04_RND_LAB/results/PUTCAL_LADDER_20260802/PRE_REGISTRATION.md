# PRE-REGISTRATION — PUTCAL_LADDER_20260802
Written BEFORE any cell is run. NIFTY 50 index options only, PE-only calendars.

## Question (Principal ask, mid-session, "in parallel")
Buy a longer-dated PE, sell a shorter-dated PE (same strike = calendar, not diagonal), roll on a
fixed calendar-day schedule. Two tenor scales, three configs:
- **A-T5**: buy 45D PE / sell 15D PE, roll when the near leg has 5 calendar days left.
- **A-T2**: buy 45D PE / sell 15D PE, roll when the near leg has 2 calendar days left.
- **B-T7**: buy 90D PE (3mo) / sell 30D PE (1mo), roll when the near leg has ~7 calendar days left
  ("before last week").

## Prior art (checked before running)
- `K-002` reverse calendar (BUY near/SELL far) — killed, -174% cumulative, wrong-direction theta.
  This ask is the OPPOSITE (buy far/sell near = "standard" calendar) — not the same test.
- `K-003` double calendar (CE+PE both legs, single-stock FF book) — PE leg was "dead weight" vs
  CE-only because back-month PE is skew-rich. Same underlying risk (rich back PE) could apply
  here too — flagged as an expected headwind, not a reason to skip: this is NIFTY INDEX, fixed-DTE
  ladder, not FF-signal-gated single-stock, so it is a genuinely different test.
- `standard_calendar.py` (single-stock CE+PE straddle calendar, ~30D near / next-month far) is a
  different underlying class (stocks, straddle, signal-linked FF bucketing) — not directly reusable
  numbers, only a directional-convention check (confirms "sell near/buy far" = "standard", matches
  this ask).
- No prior NIFTY-INDEX PE-only fixed-DTE calendar ladder found in STRATEGY_REGISTER/KILLED_IDEAS.

## [INFERENCE] Pre-registered expectation
Back-month (far) NIFTY puts typically carry rich skew (crash-insurance demand), so the BUY-far leg
is expected to be a persistent cost drag; the SELL-near leg's faster theta decay is the only offset.
Expectation: small positive or breakeven at best before costs, similar to or worse than other
theta-harvest structures already found in this codebase (VRP ceiling ~15-25% CAGR family) — not a
guaranteed win. Reported honestly either way. Genuinely NEW here vs S1-F: this is a multi-day HELD
position (mark-to-market over ~1-3 months), not an intraday flatten — different risk character
(gap/weekend/overnight exposure across the whole rung life, unlike S1-F's zero-overnight design).

## Structure (per rung)
- Strike: ATM at entry (round(spot/50)x50, nearest, first strike where BOTH legs have CONTRACTS>0),
  SAME strike both legs (calendar, not diagonal) — [ASSUMPTION, no strike specified by Principal].
- BUY 1 PE @ far target DTE, SELL 1 PE @ near target DTE, both entered same day.
- Roll = CLOSE BOTH legs at CLOSE price (CONTRACTS>0 gated, fwd-fill <=3 trading days else drop+log),
  immediately OPEN a fresh rung (fresh ATM, fresh far+near pair) — "replace" mechanics, one rung open
  at a time (matches IRONFLY_LADDER_20260802 convention, avoids overlapping-capital ambiguity).
- Capital per rung = net debit paid at entry (far cost - near credit); if a rung nets to a credit,
  capital = near strike (max theoretical loss proxy) instead, flagged explicitly if it occurs.
- No stops/filters/vol-timing (Principal asked for a fixed-schedule roll comparison only).

## Method (matches firm convention)
- Entry/exit price = option daily CLOSE, CONTRACTS>0 gated (fwd-fill <=3 trading days, else drop+log).
- Costs: 1.77 premium points round-trip PER LEG (COST_STANDARDS-derived, reused verbatim from
  OPTBUY_CONVEXITY_20260731/IRONFLY_LADDER_20260802 for direct comparability) x 2 legs = 3.54
  pts/rung.
- Split pre-2019 / 2019-2024-09 / 2024-10+ reported separately; **2026 H1 held out**, never selected on.
- Placebo: random roll-date selection (matched count per config), 500x, percentile rank vs observed mean.

## Kill criteria (pre-committed)
- HARD KILL: fails its own placebo; any lookahead; `guards`-equivalent physical-bounds violation.
- SOFT (sets tier, never kills): t-stat, small-n, Bonferroni context (3 configs = 3 additional
  trials on top of the family's already-large honest count — reported against the wider family,
  not just these 3 in isolation).

## Deliverable
`cells.csv` (3 configs), per-rung trades, `FINDINGS.md`, comparison chart.
