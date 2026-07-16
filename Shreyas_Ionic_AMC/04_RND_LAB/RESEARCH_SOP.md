# RESEARCH SOP — how every idea becomes (or fails to become) a strategy
(From BUILD_ADDENDUM §7, §10, §12, §14. R&D Head enforces; Quant Head owns statistics; no skipping.)

## The 8-step loop
1. **INTAKE** — hypothesis one-pager (template below) → IDEA_PIPELINE row. No one-pager, no work.
2. **TRIAGE** (FM + Quant, ≤30 min, cheap tier) — economic WHY plausible? data on disk (DATA_CATALOG)? capacity ≥ target? → KILL or proceed.
3. **CHEAP TEST** — the single cheapest falsification (event study / decile spread / one-year slice). Kill threshold pre-registered BEFORE touching data.
4. **FULL BACKTEST** — per CODE_CHECKS.md (guards imported from `lib/guards.py`) + validation battery below + **mandatory /sensitivity report (Dr. Bhat, E-027): param surface, perturbation, subsample — Gate-4 cannot pass without it** + **mandatory LOOKAHEAD AUDIT (D-028): T1–T10 walk + `lib/lookahead_audit.py` battery + one-day-lag test, verdict filed as `LOOKAHEAD_AUDIT.md` in the run dir, signed Dr. Bhat — a FAIL quarantines the result (unquotable anywhere)**. Results per run-engineering rules below.
5. **RED TEAM** — one focused attack (D-008) + placebo battery. Verdict REAL / FRAGILE / FAKE → ADVERSARIAL_REVIEWS row. **Runs on Sonnet by default (D-036, 2026-07-16)** — escalate to Opus only for a genuinely hard call or a capital-sized decision. Gate-4 (Dr. Bhat, sonnet) and Gate-5 (Nikhil, sonnet) stay procedurally SEPARATE sign-offs even though both are cheap now — the value here is independent lenses + an audit trail before capital moves, not raw defect-count, so don't collapse them into one pass.
6. **IC MEMO** — /ic-memo skill → verdict, sizing, kill criteria, review date → STRATEGY_REGISTER.
7. **PAPER** — ≥20 trades or 8 weeks (whichever LATER); weekly reconcile vs Angel quotes; tracking error decomposed and explained (PAPER_LEDGER).
8. **LIVE GATE** — Principal only (D-010).
Every kill at any step → KILLED_IDEAS + resurrection condition (D-012). Count EVERY variant in the family trials ledger.

## Hypothesis one-pager template
name · one-line edge · **economic WHY** (who loses money to us and why do they keep doing it — forced / behavioral / structural?) · factor sleeve · universe · holding period · expected decay horizon · capacity estimate · data needed (on disk? Y/N per catalog) · cheap-test design · **pre-registered kill criteria** · trials run so far on this family.

## Benchmark law (D-029, Principal, 2026-07-04)
Every equity strategy is judged against its CAP-MATCHED RANDOM BENCHMARK (`datasets/derived/benchmarks_random/`): the mean + percentile-band NAV of 10,000 cost-loaded random baskets (same universe segment, comparable position count, quarterly rebalanced, full COST_STANDARDS + dynamic slippage/circuit rules). Beating an index is NOT enough; beating random-with-costs is the bar. Report: strategy CAGR vs random mean AND vs random 95th percentile AND vs a **TURNOVER-MATCHED random basket** (Red-Team rule 2026-07-04: the standing hurdles churn ~200-355%/yr; a low-turnover strategy 'beats' them by cost savings alone — I-016 lesson: 2.3 of 2.88pp was turnover, 0.6pp was skill. Placebo harness: results/factor_replication/20260704_red_team/placebo_turnover_matched logic). THE STANDING BARS (built 2026-07-04, 2005-2025, net of full costs): SMALL-50 mean 9.98%/p95 13.66% · SMALL-25 9.18%/14.47% · LARGE-20 11.93%/14.43% · MID-30 19.99%/22.39% · MID-15 19.33%/22.98% · N500-25 12.30%/16.96% · N500-50 12.74%/16.21% · N500-100 13.32%/15.65%. NOTE: net of costs, random LARGE beats random SMALL (drag 1.4 vs 3.8-4.2pp/yr inverts the size premium) — a smallcap strategy fights a 3x cost headwind before any alpha counts.

## Statistical validation battery (gate 4-5; Quant signs)
- **Walk-forward:** train 3y → validate 1y → roll 6m. Params frozen per window. Grid ≤ 3×3. Most recent 12m = FINAL untouched OOS, opened exactly ONCE per family.
- **Plateau rule:** best cell must not beat its parameter-neighborhood median by >20% (spike ≠ edge).
- **Deflated Sharpe + PBO via `purgedcv` (ADOPTED 2026-07-04, canonical B&LdP/CSCV):** DSR > 0.95 with HONEST trials; PBO < 25%. UNITS GUARD: bars_per_year must match the return series frequency (monthly=12) — a silent mismatch inflates DSR (Arjun's trap, logged). Every per-trade edge reported in RUPEE POINTS + %spot alongside any ratio denominator (denominator-disease rule).
- **Regime slices:** 2018 smallcap crash · 2020 COVID · 2022 rate shock · 2024 election vol · 2026 YTD — no catastrophic slice.
- Minimums: ≥30 trades per free parameter; ≤5 free parameters (P-11). P&L booked in EXIT period; stable denominators.

## Run & results engineering (no lost/overwritten results)
Every run → `results/<strategy>/<run_id>/` (run_id = `YYYYMMDD_HHMM_<confighash8>`): `config.json` (full params + data snapshot: paths, row counts, max dates), `metrics.json`, `trades.csv`, `equity.png`. Never overwrite a run dir. Guards imported from `04_RND_LAB/lib/guards.py`, not copy-pasted. Seeds fixed; same config must reproduce to the rupee.

## Paper SOP + Definition of DONE
Paper: signal logged BEFORE action (timestamp, intended price, size); fills marked vs actual Angel quotes; weekly reconciliation → TE decomposition (slippage/timing/fill/decay); ledger append-only.
**DONE (live-candidate):** LOOKAHEAD AUDIT PASS (D-028) · survived 2× costs · DSR>0.95 & PBO<25% · no catastrophic regime slice · capacity ≥3× intended size · paper ≥20 trades/8wk with TE explained · Red Team REAL · kill criteria + review date registered · Principal sign-off.

## Operating cadence
Daily (auto, DESK-100): capture task + EOD_ROUTINE + freshness ping. Weekly: paper reconcile · pipeline triage · WAR-room cleanup. Monthly: edge-decay review (2 consecutive fails → demote) · token-spend vs TOKEN_POLICY. Quarterly: red-team the PROCESS · knowledge-base pruning · AlphaPoints settlement · resurrection-conditions review.
