# STRATEGY REGISTER — every strategy the firm runs or is validating (FM owns)
Nothing trades (even paper) without a row here: owner, edge, gates, kill criteria, review date.

| ID | Strategy | Stage | Owner | Per-trade edge (fwd, 210-univ unless noted) | Gates/sizing | Kill criteria | Review |
|---|---|---|---|---|---|---|---|
| S-01 | IV/RV short straddle (IV/RV≥1.4, IV<100% cap) | **SEND-BACK (IC 2026-07-03)** — paper-tracking only, FIREWALLED | Paper: FM (Vikram) · Resurrection: Quant (Arjun) | **REGISTERED EDGE: +11.4pts INCREMENTAL over unconditional short-vol (~+8.8 at 2× costs)** — the +37.6% headline is 71% regime beta (Red Team, memo 20260703) | NO capital. Paper small, live-feed IV-cap fixed first, event-gated | Resurrection: 2018+2020 backfill re-run + per-trade sizing DSR + genuine 3×3 grid + positive incremental through a real vol-spike | first VIX>20 event or 8 wks |
| S-02 | Earnings short-vol (ATM straddle through print) | **FAILS-PRE-IC (2026-07-04)** — registered +21.6% was a DENOMINATOR ARTIFACT (per-leg premium→0 on expiry-week rows; max row +6,759%). Honest gated: +9.7%/event; crush incremental vs exit-before base only +4.8% (CI [+0.08,+9.6]); vs calendar-matched unconditional short-vol **−10.1%** (CI all-negative); 2023 carries the crush | Resurrection: Arjun | NO IC until: stable-denominator recompute + 2024-25 crush CI lower-bound >+3% + Nikhil placebo (random non-earnings dates ≈ 0) | results/S-02/20260704_shuffle | on resurrection |
| S-03 | FF calendar single-CE | **KILLED PRE-IC (2026-07-04)** — 3rd denominator artifact (pnl/back-premium); in RUPEE POINTS large-cap gated: build +5.85 → **forward −9.30 pts (loses money 2024 AND 2025)**. Honest family trials ≥20 | — | K-012 -- RESURRECTION REVIEW CLOSED 2026-07-05 (CIO): STAYS-KILLED-WITH-NEW-INTAKE. Signal REAL (100th-pctile placebos) but calendar VEHICLE DEAD -- pre-registered causal gate fwd -0.03/Rs100 @1x, -2.36 @2x, BUILD -0.51; 61% dead back-leg markets. Edge graduates to a NEW liquidity-native intake (Structurer/Aakash, 5 pre-reg kills). No paper tracking. | results/S-03/20260705_resurrection/CIO_RULING.md | CLOSED |
| S-04 | Short strangle 14-DTE managed | **FULLY CERTIFIED 2026-07-04: 2x-cost (12/12) + Gate-4 sensitivity PASS-WITH-FLAGS (plateau: certified cell = 0.995x neighbor median, 27/27 cells positive) + D-028 lookahead PASS (0 FAIL, T8 purge bit-exact) -> PAPER-WATCH** | Paper: Vikram · Weekly: Tara · Flags: Sameer | +0.22%/spot managed; 2025 subsample +0.081%/spot (near-breakeven); decay zero-cross 2025.4-2028.9 (hinges on unverified 2026 datum); ~5-7% entry fills suspect under circuit rule; exit-leg volume = data gap | ₹1cr book (D-026); inverse-IV ≤1.0x; event-gate; PAPER MEASURES FIRST: realized buyback fill vs 50% trigger, then 2026-data verification | fwd <+0.1%/spot over 3 cycles OR fill-optimism >30% of edge OR 2026 datum proves inflated | weekly paper |
| S-05 | Track-1: delta-hedged 0DTE/DTE1 NIFTY short straddle, morning-straddle ≥0.45% spot filter | Paper-ready (pre-firm validated) | FM (Vikram) | CAGR +5.9%, MaxDD 5%, 6/6 yrs positive [books] | Index-only; real-fill validated | 2 consecutive negative quarters | monthly |
| S-06 | Equity Mom-12-1 + LowVol blend | Backtest (re-run w/ PIT universe + draft costs pending) | Quant | +15%/yr ann (below bar, diversifier) | The only long-equity diversifier vs short-vol book | DSR<0.95 | quarterly |

## Book-level standing rules (CIO)
1. All S-01..S-04 are SHORT-VOL — correlated in a vol spike. Combined book sizing must assume they draw down TOGETHER.
2. No naked short-vol through a name's known binary (earnings/FDA/big policy date). Sector analysts publish the calendar; desk gates entries.
3. Compounded portfolio CAGRs are reporting artifacts — size from per-trade edge × worst-case MTM, never from headline CAGR.
4. Paper first (RESEARCH_SOP §12 DoD), Principal approves any LIVE step (D-010/D-018).

## S1-F — 0DTE NIFTY ATM Short Straddle (REGISTERED 2026-07-10, paper forward test)
- **Spec (FROZEN, D-030):** `06_TRADING_DESK/specs/S1F_SPEC.md` · pinned commit `b8d2f3d` · v1.0
- **Edge:** expiry-day VRP harvest; +10.7 pts/day net (t=3.92, PF 1.79, 259 expiry days 2021-26, 1% slip + TC); vetoes F1 (RSI5 D-1 80/20) + F2 (|D-1 ret|>1.5%); sensitivity plateau 72/84; COVID-modeled survivable.
- **Sizing:** 0.75×equity / dynamic margin (~15% notional ≈ ₹2.7L/lot 2026) ≈ 3-4 lots/₹10L; halve on 3d-vol>2× 1yr median. Honest expectation ~13-17% CAGR, maxDD ~−5% (corrected-margin sim).
- **Forward clock:** first expiry ≥ 2026-07-14 · **Kill (pre-registered):** 26 expiries expectancy≤0, or paper maxDD>15%, or fills 3+pts/day worse than model over 13 expiries → HALT/CIO.
- **Shadow (zero size):** S1 unconditional; S1b ATM−50 challenger. Runner: `06_TRADING_DESK/paper/s1f_daily_runner.py` → `paper/s1f_paper_log.csv` (intent BEFORE action).
- **Docx:** `09_PRODUCT/reports/S1F_STRATEGY_PACK_20260710.docx` (not in git per gitignore).
