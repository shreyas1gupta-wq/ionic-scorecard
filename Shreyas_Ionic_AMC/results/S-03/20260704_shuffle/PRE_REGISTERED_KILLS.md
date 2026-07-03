# S-03 FF-Calendar — Pre-Registered Kill Thresholds (D-M2 prep)

**Written BEFORE computing the shuffle** (RESEARCH_SOP + 2026-07-04 IC-1 lesson: run incremental-vs-base shuffle before every IC; an edge is what remains after the null).

**Date:** 2026-07-04 · **Owner:** Arjun Rao. Gate-5 deliverable for the S-03 FF-calendar IC.

## The question
The FF-calendar picks entry timing by **selecting the peak forward-factor** (FF>=0.25) within each expiry cycle. The null hypothesis: **FF selection adds nothing over a random calendar entry** — i.e. any long-calendar in this universe/period earns the same, and "FF>=0.25" is just picking noisy-high-FF entries that mean-revert (a form of selection on the entry premium denominator).

## Universe (LARGE-CAP gate applied FIRST)
- **Ex-ante large-cap proxy:** symbols with a FF candidate BEFORE 2024-01-01 (had liquid single-stock options pre-2024). 54 symbols. This avoids the retro-selected-list lookahead lesson (the "16 landmines").
- Large-cap FF>=0.25 slice: **673 trades, 54 symbols** [DATA].
- Return formula (from `filtered_portfolio.py` L59-60, CE-leg only, SLIP=0.015):
  `ret = (CE_fe*(1-SLIP) - CE_be*(1+SLIP) - CE_fx*(1+SLIP) + CE_bx*(1-SLIP)) / CE_be`
- Tier sizing 0.75 / 1.0 / 1.25 by FF band (<0.5 / <0.75 / >=0.75).

## Decomposition to be run
- **(a) FF SELECTION vs within-month shuffle.** Base = the FF>=0.25 selected trades. Null = for each expiry-month, shuffle the FF values across the candidate calendars available that month, re-apply the FF>=0.25 filter + tier sizing on the SHUFFLED FF, and measure the return. If FF selection has no edge, shuffled ≈ actual. 1,000 shuffles → empirical p-value on (actual mean − shuffled mean).
- **(b) Per-year + build/forward with COUNTS.** build = entry ≤ 2024-12-31; forward = entry > 2024-12-31. Per-year mean/hit/n.
- **(c) Trials ledger.** Honest family-trials count for DSR (FF threshold sweep {0,0.10,0.20,0.30,0.50} × {single-CE, double CE+PE} × {2 slip levels} = documented in forward_factor_v2.py = 6+ per pipeline).

## PRE-REGISTERED KILLS (decide BEFORE seeing results)
1. **KILL if incremental edge is not significant.** If the FF-selection incremental mean (actual − shuffled) has empirical p >= 0.05 (one-sided), FF selection adds nothing over random calendar entry → **FRAGILE/FAKE**, do not advance to IC as a *timing* edge.
2. **KILL if the raw base edge is negative net of costs** on the large-cap slice (build OR forward) — a positive full-universe number carried by small/illiquid names is not investable.
3. **KILL if forward (2025-26) mean <= 0** on large-cap — the edge is a pre-2024 artifact.
4. **KILL if P&L concentrates** — one symbol > 30% of |P&L|, or negative without the top-5 trades (degenerate detector).
5. **KILL if incremental survives shuffle but < 2× the approved cost stack** — same promotion rule as S-04.
6. **DEGRADE (not kill) if** significant but with < 30 trades/parameter or per-year counts too thin to trust a year — flag for capacity/robustness, not an outright kill.

## Honesty notes
- [DATA] The task states "2,612 candidates"; the current `forward_factor_v2.parquet` has 4,585 total rows and 1,494 at FF>=0.25 (full universe). The 2,612 does not match this build — flagged; I proceed on the ACTUAL file with row counts shown.
- The shuffle preserves the within-month set of available calendars and the entry economics; it only randomizes WHICH FF value maps to which calendar. This isolates the *selection* skill from the *universe/period* beta.
