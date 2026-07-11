# G23 Phase-1 triage — OS-47 (conversion/parity arb) + OS-48 (dispersion)
_Arjun Rao (Quant) · 2026-07-07 · FAST/CHEAP pass, rank-not-certify · campaign OPT-SWEEP-50_

## Data lineage
- NIFTY index options: `intraday_options_strategy/datasets/raw/hf_index_options_1m/options/NIFTY/*.parquet` (262 expiry files, 2021-05→2026, 1-min tz-aware OHLCV+OI; ~300-400k rows/expiry). 5 expiries sampled across eras (2021/2022/2024/2025/2026).
- Single-stock options: `.../stocks_options/{SYM}/*.parquet` (210 F&O names, DUAL SCHEMA — HF 1-min + bhavcopy DAILY w/ `settle`, 0.00-px untraded strikes). 49/50 NIFTY-50 names present; 6 most-recent expiries/name = 584 ATM-leg observations.
- INDIA VIX / index daily in `datasets/index_daily/` (not needed — both setups killed upstream of a VIX gate).
- **No NIFTY equity futures in the repo** (only MCX commodities) — material for OS-47 (see below).
- Leg-liquidity detail: `os48_leg_liquidity.csv` (this dir).

## OS-47 — conversion / reversal (put-call-parity) arb → **KILL**
Measured GROSS apparent parity dislocation as the cross-strike spread of the implied forward `F=K+(CE−PE)` on same-minute last-trade prints (≥3 strikes/minute):

| expiry | minutes | median fwd-spread | p90 | p99 |
|---|---|---|---|---|
| 2021-08-05 | 3,379 | 4.35 pt | 11.3 | 41.8 |
| 2022-12-15 | 3,381 | 4.75 | 12.6 | 36.7 |
| 2024-04-18 | 2,630 | 7.10 | 20.5 | 78.5 |
| 2025-08-21 | 3,007 | 6.75 | 12.9 | 22.2 |
| 2026-05-12 | 2,632 | 12.55 | 24.5 | 54.1 |
| **pooled** | | **6.45 pt** | 17.4 | 46.0 |

Why KILL (edge ≤ 0 net, and structurally):
1. **The 6.45-pt "dislocation" is a measurement artifact, not tradeable edge.** It is built from *last-trade* prints inside the same minute (CE and PE trade at different seconds while spot drifts) plus stale OTM last-trades. It is a non-synchronicity/staleness spread, not a synchronized quote spread.
2. **No bid/ask → the real tradeable edge is smaller still and certainly negative.** A conversion crosses 2 option legs + the underlying; a box crosses 4 legs. NIFTY option crossing cost is ~0.5–2 pt ATM and 5–20+ pt OTM → round-trip ≈ 10–40+ index pts, **larger than the entire gross gross dislocation.** Net = deeply negative.
3. **No futures leg in our data.** The synthetic-underlying leg can't even be constructed/tested from the repo — a hard Phase-1 data-blocker on top of the economic kill.
4. **Structural ceiling.** Conversion/box on cash-settled European index options is a *financing/rate arb* held to expiry — real edge is basis points of notional. It cannot reach XIRR>50% / Sharpe>2. Exactly the "looks-like-free-money" artifact that is guilty until proven innocent. As pre-registered in the spec (score 2, "market-neutral, tiny edge, execution-bound"), it prints an arb, not an alpha source.

**Verdict: KILL. Weakest assumption it fails: that a last-trade cross-strike spread is a tradeable dislocation — it is non-synchronicity noise, and net-of-crossing it is negative.**

## OS-48 — dispersion (short index vol / long constituent vol) → **KILL (Phase-1); NOT blocked by the exitability wall**
Pre-registered gate (mandate + spec red-flag #5): run the fill/existence check on constituent single-stock legs BEFORE any backtest; if most are dead like the FF calendar (A.14, 61% dead back-legs) → report BLOCKED-EXITABILITY-WALL. **Ran it first. It does NOT fire:**

| metric (ATM straddle legs, 49 NIFTY-50 names × 6 recent expiries × entry/exit) | value |
|---|---|
| DEAD ATM leg (min(CE,PE) day-volume = 0, no fill possible) | **2.6%** (entry 5.1% \| exit 0.0%) |
| THIN ATM leg (min-leg day-volume < 75) | 2.9% |
| names with ≥50% of leg-obs dead | 0 / 49 |
| median day-volume among live legs | ~49,250 (p25 ~2,950) |

**Honest correction of the prior (report the number straight, in both directions):** the a-priori assumption was that these legs inherit the 61% A.14 wall. They do not. Dispersion is specified as **ATM straddles on the largest 50 names** — the single liquid corner of the single-stock chain — whereas the FF calendar died on *far-OTM* single-stock back-legs. So OS-48 genuinely sidesteps the wall at the ATM/large-cap corner. I do **not** rubber-stamp a BLOCKED verdict just because it was expected.

But OS-48 is still **KILL for Phase-1** on grounds that don't need a full backtest:
1. **Not a fast/cheap-testable edge.** A real dispersion P&L needs per-name IV surfaces + vega/correlation matching against the index straddle — a dedicated build, out of scope for a triage pass.
2. **Our data can't price the edge.** Single-stock marks are `settle`-based EOD (no bid/ask; intra-cycle prints are sparse — RELIANCE, the *most* liquid name, is ~371 total prints for a whole HF-era expiry). "Day-volume > 0" is an existence floor, NOT proof you get filled at a tradeable price on ~50 legs each cycle. The implied-correlation premium is a few vol-points; it will not survive real crossing on 50 legs.
3. **Capacity / margin prohibitive + short-correlation tail.** 50 long single-name straddles = enormous SPAN margin; dispersion is short-correlation → it blows up precisely when correlation spikes in a crash, its own nasty left tail. Per CIO book rule #1 the short-index-vol leg also joins the one correlated short-vol cluster; incremental Sharpe over S-04/S-05 is unproven and untestable cheaply.

**Verdict: KILL (Phase-1) — NOT-BLOCKED-EXITABILITY-WALL (2.6% dead, not 61%). Deprioritize; if ever revived it needs a per-name IV/vega build + a bid/ask data source, not a fast pass. Weakest assumption it would fail at Phase-2: that a few-vol-point correlation premium survives real bid/ask on ~50 legs + margin.**

## Summary
| Setup | Verdict | One-line reason |
|---|---|---|
| OS-47 conversion/parity arb | **KILL** | Gross 6.45-pt dislocation is non-synchronicity/stale-print noise; net-of-crossing negative; financing-arb ceiling below the bar; no futures leg to even build it |
| OS-48 dispersion | **KILL (Phase-1)** | Exitability wall does NOT fire (2.6% dead ATM legs, not 61%) — honest correction of prior — but edge not fast-testable, unpriceable on settle-only single-stock marks, margin/short-corr tail prohibitive |
