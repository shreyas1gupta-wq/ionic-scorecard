# TRIAGE — Principal's Two-System Intraday NIFTY Options Spec (2026-07-10)

**Prepared by:** CIO chief of staff, synthesizing Librarian prior-art map, Kavya data-readiness audit, Arjun cheap-test designs (all 2026-07-10).
**Spec:** System 1 = <₹1cr medium-frequency intraday NIFTY options portfolio (5-min regime engine + 10 families, 5-20 trades/day). System 2 = ₹20k "GLBS" option-buying book (5 setups, score-gated, 0-3 trades/day).

## Headline
Both systems are predominantly intraday NIFTY option **buying** — the firm's most-killed family (K-001: ~14 legacy variants + 2026-07-07 re-kills VOL_BREAKOUT_ATM, VWAP_RSI_MOMENTUM, ORB×3). K-001 resurrection condition = sniper **<5 trades/month**; System 1 specifies **5-20 trades/day** — contradicts by ~2 orders of magnitude. Triple-confirmed structural facts: intraday MFE/MAE ≈ 1.0 (zero convexity), signals 10-25x weaker than option breakeven, theta+VRP+costs the final wall. ~10 of 16 mapped components TESTED-DEAD; **4-5 genuinely novel** (F8 premium-confirmation, FVG constructs, OI-wall/trapped-writer, F9 N-vs-BN RS, and conditionally the regime engine as portfolio ALLOCATOR).

## Staff-report reconciliation (chief-of-staff note)
Arjun's cheap-test doc pre-registered all OI-wall/OI-confirm variants as UNTESTABLE ("no intraday OI history"). **Kavya's audit supersedes this:** minute-level OI EXISTS in the HF NIFTY weekly option files (#4, verified nonzero 2022-2024 samples). OI variants ARE testable 2021-06→2026, subject to a mandatory **3-bar (≈3-min) OI lag** (exchange dissemination delay — T-series lookahead control). Consequence: GLBS-D / F7-OI move from BLOCKED-DATA to CHEAP-TEST (conditional, via Track-3 dealer-gamma/GEX intake `ideas/20260703_dealer_gamma_gex.md`).
Also: COST_STANDARDS file header reads **APPROVED (D-021, 2026-07-03)** — binding for all kill bars below. Honest ATM NIFTY weekly round-trip ≈ 1.2% of premium (2.4% stressed) ≈ 3 underlying pts at 0.5Δ on ₹150 premium.

## FULL VERDICT TABLE

| # | Component | Prior-art verdict | Data verdict | ACTION |
|---|---|---|---|---|
| 1 | Layer-1 regime engine (5-min A/B/C/D) | PARTIALLY-TESTED — regime-as-buy-filter dead (K-001 §regime-aligned, K-015/KB A.19); as multi-family ALLOCATOR untested | READY — spot+VIX 1-min 2015→2026 (regimes validatable pre-option era) | **CHEAP-TEST (T1, run first)** |
| 2 | F1 VWAP mean-rev ATM buy (Z±1.5/2/2.5) | TESTED-DEAD — 15,812 legacy signals fwd≈0, skew NEGATIVE for bounce-buys; KB A.23 mean-reversion = SELLER's edge | READY | **SKIP-DEAD**; the one live sub-signal (down-spike PUT-sell spread + vol gate) = FOLD-INTO-EXISTING (MEANREV_RSI resurrection note) |
| 3 | F2 liquidity-sweep reversal (PDH/PDL/round) | PARTIALLY-TESTED — SWEEP_SCAN (D-028 exploratory): tiny spot edge +1-6bps, never costed as option trade | READY (spot) | **CHEAP-TEST (T2)** — pass sanctions underlying/sell-side vehicle ONLY |
| 4 | F3 ORB (15/30/60m ×3 entries) | TESTED-DEAD ×3 vehicles (K-001, ORB_MOMENTUM50, ORB_SHORTONLY, ORB_SHORTFADE_PUTOPTIONS; option captures ~0% of 8bps gross edge) | READY | **SKIP-DEAD** |
| 5 | F4 vol-compression breakout ATM | TESTED-DEAD 2026-07-07 exact family (VOL_BREAKOUT_ATM: loses GROSS, negative every year 2021-26, structural long-premium tax) | READY | **SKIP-DEAD** (no resurrection condition — loses at zero cost) |
| 6 | F5 trend pullback 0.4-0.6Δ buy | TESTED-DEAD — K-001 delta test, all deltas net-negative | READY | **SKIP-DEAD** |
| 7 | F6 failed-breakout fade | TESTED-DEAD (sell vehicle PF 0.78-0.89; buy inherits K-001; underlying edge ≈ absent) | READY | **SKIP-DEAD** |
| 8 | F7 0DTE gamma breakout | TESTED-DEAD (K-001 expiry variant; K-005; OS-08/09/15 sell-side kills) — EXCEPT OI-wall trigger | 0DTE testable every week 2021-05→; minute OI available (3-bar lag) | **CHEAP-TEST (T5, conditional on T1-C surviving; highest bar)**; OI-wall variant via GEX intake |
| 9 | F8 option-premium confirmation filter | **NOVEL** — zero prior art firm-wide; only spec element that raises per-trade quality vs adding entries | READY (ATM premium series 2021-06→2025-12) | **CHEAP-TEST (T3)** — as VETO inside surviving strategies only; does NOT reopen buying |
| 10 | F9 NIFTY-vs-BANKNIFTY RS | **NOVEL** | Signal testable on spot (both 1-min 2015+); BN weeklies absent (monthlies only) — fine, spec trades NIFTY options | **CHEAP-TEST-LATER** — fresh Gate-1 one-pager, queue behind T1-T5 |
| 11 | F10 time-of-day models | PARTIALLY-TESTED — 25-bucket map built (INTRADAY_STUDY); no window's mean move approaches 0.3-0.5% option breakeven; Europe-open buying dead | READY | **SKIP-DEAD** as standalone models; map = FOLD-INTO-EXISTING (baseline conditioning in T1/T2) |
| 12 | Position mgmt (50% book / ATR-trail runner) | TESTED-DEAD as rescue (K-001 convex exits WORSE than fixed 1:2; zero convexity to trail) | n/a | **FOLD-INTO-EXISTING** — fine as risk plumbing on any survivor, never as edge |
| 13 | GLBS daily-bias gate (CE only if daily bull) | TESTED-DEAD — K-001 regime-aligned MTF: bull-longs WR 40%, breakeven-BEFORE-costs (best-of-dead), fwd 0-for-10 | READY | **SKIP-DEAD** (K-001 sniper condition stands) |
| 14 | GLBS-A sweep+FVG reversal | Sweep half = #3; **FVG half NOVEL** (zero firm prior art) | READY | **CHEAP-TEST** — FVG as a flag inside T2/T4 |
| 15 | GLBS-B 15-30m compression breakout | = F4. TESTED-DEAD | READY | **SKIP-DEAD** |
| 16 | GLBS-C 0DTE gamma explosion buy | TESTED-DEAD (only convex niche >2ATR ≈ 8 trades/yr, sub-breakeven) | READY | **SKIP-DEAD**; T5 covers the family's last doorway |
| 17 | GLBS-D option-chain trap (OI wall breaks) | **NOVEL** — nearest = Track-3 GEX (1-INTAKE, never run); OS-35 pin (sell, do-not-advance) | Minute OI EXISTS (Kavya #4) — testable with mandatory 3-bar lag; derived daily OI surface stale (ends 2024-07), do NOT use | **CHEAP-TEST (conditional T6)** — route through GEX intake one-pager, after T1-T5 |
| 18 | GLBS-E FVG continuation | **NOVEL** | READY | **CHEAP-TEST** — via T4 FVG flag; standalone only if flag shows marginal edge |
| 19 | GLBS score-gate (≥4/6 confluence) | PARTIALLY-TESTED — K-001 filter-mining: NO single filter reached required 60% WR, every bucket lost; 6-factor joint score w/ novel flags untested | 5 of 6 flags computable (OI-confirm needs 3-bar-lag build; volume = option-volume proxy) | **CHEAP-TEST (T4)** |

Score: **SKIP-DEAD 8** (F1, F3, F4, F5, F6, F10, GLBS-bias, GLBS-B, GLBS-C ≈ 9 counting both) | **CHEAP-TEST 7** | **FOLD-INTO-EXISTING 2** | **BLOCKED-DATA 0** (OI unblocked by Kavya's finding; only era-2020 options and bid-ask quotes remain structurally missing, both acceptable).

## RANKED CHEAP-TEST QUEUE (pre-registered; Arjun's designs verbatim, kill bars binding)

Results dir: `Shreyas_Ionic_AMC/04_RND_LAB/results/GATE3_MFI_SYSTEMS_20260710/`. Mandatory guard block every script: `guards.fix_ist_dates`, `guards.drop_preopen` (BEFORE PDH/PDL), `guards.assert_next_bar`, `guards.degenerate_flags`, `execution_realism.fill_check` + `slippage_multiplier`, `lookahead_audit.audit_session` / `audit_same_bar` / `one_day_lag_test` (metric must survive one-bar lag, <50% collapse), within-day label-shuffle placebo. All costs = COST_STANDARDS (D-021 APPROVED), promotion bar = net-positive at 2× costs.

| Rank | Test | Kills/greenlights | Pre-registered KILL threshold | Runtime |
|---|---|---|---|---|
| **T1** | Regime-engine predictivity (5-min A/B/C/D, FIXED thresholds, one pass, spot 2020-2025) | All of System 1 Layer-1; 7/10 families ride A & C | Regime survives only if day-clustered \|t\|≥3 AND ≥6 NIFTY pts/30-min. A+C both fail → System 1 dead as designed; <2/4 survive → Layer-1 killed, families unconditioned-only | <10 min |
| **T2** | Liquidity-sweep reversal on underlying (PDH/PDL/round/OR15; sweep ≥0.05% + close-back within k∈{1,3,5}) | F2, GLBS-A sweep half | Mean reversal edge <5 pts OR t<2.5 vs time-of-day-matched baseline on BOTH PDH & PDL → kill. Era-split 2020-22 vs 2023-25 mandatory; sign flip = kill regardless of pooled t. PASS ≠ option buying | <5 min |
| **T4** | Score-gate confluence monotonicity (5/6 flags incl. FVG + premium-breakout; OI flag deferred to T6 lag build) | System 2's central mechanism; FVG novelty | Spearman t<2 OR (bucket≥4 − bucket≤1) <6 pts → gate killed. Top bucket alone must clear 10 pts (2× stressed round-trip) or System 2 has no vehicle | +15 min (parallel w/ T2) |
| **T3** | Option-momentum confirmation filter (F8) on 20260707-campaign breakout events, confirmed vs unconfirmed | F8; potential veto for all survivors | Spread <4 pts OR t<2 → kill. Also report rejection rate (80%+ rejection of scarce signals = dead even if positive). PASS = veto only, not buying reopen | ~20 min |
| **T5** | 0DTE gamma breakout, expiry days, ATM buy, full cost stack — CONDITIONAL on T1-C surviving | F7 core; the K-family's last doorway | At 2× costs: expectancy <+8% premium/trade OR PF<1.15 OR n<100 OR t<2.5 → kill, filed against K-001 | 30-45 min, background |
| **T6** (new, conditional) | OI-wall / trapped-writer trigger with 3-bar OI lag — only after T1-T5, via GEX Gate-1 one-pager | GLBS-D, F7-OI variant | Thresholds to be pre-registered in the one-pager before any run (not yet designed — do not improvise) | design pending |

Sequencing: T1 → (T2 ∥ T4) → T3 → T5-conditional → T6-conditional. Total T1-T5 ≈ 1.5 hrs laptop compute, zero agents, zero new data sources. DSR trial ledger (log in results README): T1=4, T2=6 (3 variants × 2 levels), T3=1, T4=1+5 marginals, T5=1.

## DATA-ACQUISITION / BUILD ASKS (Kavya)
1. **Tail refresh** — spot/VIX/option minute files end 2026-05/06; extend via Angel capture + HF re-pull before any forward window. (Required, cheap.)
2. **Daily breadth series build** — A/D line from `nse_bhavcopy_daily/close_all.parquet` (~30-min script job); intraday breadth (hf_stock_minute, 2022+) only if T1 demands it. (Build, not buy.)
3. **Volume-proxy decision** — index has no volume; adopt ATM option volume as proxy, document as spec deviation. (Decision, no acquisition.)
4. **OI 3-bar-lag column build** in the weekly option loader (for T6). (Small script.)
5. **NOT acquiring:** 2020 option minutes (not free at minute level — accept 2021-06→2026 window ≈ 5 full years); BANKNIFTY weeklies (F9 doesn't need them); bid-ask quotes (model spread per spec, calibrate penalties vs `angel_capture_2026` live captures before trusting 0DTE fills).

## STANDING CONSTRAINTS
- K-001 + 2026-07-07 re-kills stand as pre-registered prior art with unmet resurrection conditions; no dead family re-runs inside a big harness. Novel components route through fresh Gate-1 one-pagers.
- Any Layer-1 allocator claim must beat BOTH static parents (KB A.19 / K-015), judged on Sharpe/DD.
- Forward-test freeze (D-030) applies to anything that survives to paper.
