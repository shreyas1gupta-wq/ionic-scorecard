# G24 — OPT-SWEEP-50 Phase-1 triage: OS-44 & OS-49 (Family H, long-vol/buying)
_Arjun Rao (Quant) · 2026-07-07 · FAST/CHEAP pass, rank-not-certify · edge in ₹-points + %-of-spot (never %-premium)_

## Result (headline)
| Setup | n | Edge net ₹-pts/trade | Edge %-spot | Gross (pre-cost) ₹-pts | Win% | Sharpe(/√52) | Verdict |
|---|---|---|---|---|---|---|---|
| **OS-44** gamma scalp (long ATM straddle + daily delta hedge) | 259 | **−18.83** | **−0.097%** | **−10.88** | 44% | −0.71 | **KILL** |
| **OS-49** trend debit spread (Donchian-20 breakout) | 83 | **−18.38** | **−0.071%** | **−15.96** | 35% | −0.90 | **KILL** |

Both lose money **before costs** (negative gross) — this is the structural finding, not a fee artifact.

## Data lineage (files, rows, max dates)
- Spot: `intraday_options_strategy/datasets/raw/hf_index_options_1m/index/NIFTY.parquet` — 477,738 1-min bars, 1,242 trading days, 2021-05-24 → 2026-06-03 (tz IST via guards.fix_ist_dates; guards.drop_preopen ≥09:15).
- Options: `.../options/NIFTY/*.parquet` — 262 weekly expiries, 2021-05-27 → 2026-06-09 (HF 1-min schema, guards.option_schema="minute").
- Costs: `06_TRADING_DESK/COST_STANDARDS.md` @1x (opt slip 0.25%/1-tick, STT 0.1% sell, exch 0.035%, brok ₹20/order, GST). Delta hedge = NIFTY spot proxy, brok + ~1bp/rebalance.
- BS delta: IV bisection-inverted from daily ATM-call close, r=6.5%, q=0, daily rebalance.
- Trades CSV: `os44_trades.csv`, `os49_trades.csv`; metrics `summary.json`; `run.log`.

## Guards passed
fix_ist_dates ✓ · drop_preopen (≥09:15 auction) ✓ · next-liquid-quote fill (entry-day first vol>0 bar, D+1 for OS-49 breakout signal — no same-bar sin) ✓ · no-fill on missing/zero-vol strike = DROP (OS-44 3/262 dropped; OS-49 signals w/ dead legs dropped) ✓ · P&L booked in EXIT period (per-trade, at expiry) ✓ · %-spot denominator (stable, never net-debit/premium) ✓.

## Kill-criteria battery (§5)
| Kill trigger | OS-44 | OS-49 |
|---|---|---|
| Edge ≤0 in ₹-pts AND %-spot | YES (−18.8 pts / −0.097%) | YES (−18.4 pts / −0.071%) |
| Edge only when pooled across Sept-2025 break | NO — negative BOTH sides (pre −15.2 / post −40.5 pts) | NO — negative BOTH sides (pre −13.6 / post −49.4 pts) |
| Vanishes under next-liquid-quote fill | Already primary fill; also negative at ZERO cost (gross −10.9) | Already primary; negative at ZERO cost (gross −16.0) |
| ≥30 trades | 259 ✓ | 83 ✓ |

Post-Sept-2025 is WORSE for both (post edge −40.5 / −49.4 pts) — no hidden regime rescue.

## Degenerate flags
Only "negative without top-5 trades" fires for both — the benign/expected signature of a structurally-losing strategy (losses are broad, not a few outliers). No Sharpe>4, no smooth-equity, no concentration flags (there is no positive edge to be suspicious of).

## Verdict
- **OS-44 — KILL.** Delta-hedged long straddle P&L ≈ ½·Γ·(realized var − implied var); gross −10.9 pts confirms **realized vol < implied vol** on the NIFTY weekly = the VRP the sellers harvest. Costs + hedge drag add ~8 pts. This is A.1 measured directly, not editorialized.
- **OS-49 — KILL.** Breakout debit spread's expiry value < debit paid on average (gross −16.0 pts); a 20-day-high trend trigger produces no follow-through large enough to clear the debit + theta on a 3–12-DTE spread. Defined-risk directional buying with 35% win rate and losers not paid for by winners.
- Both confirm the firm prior (K-001/K-004: buying loses; VRP is the meta-edge). Run for honest sweep completeness — neither advances to Phase-2.

**Single weakest assumption:** OS-44's hedge P&L uses BS delta backed out of the daily ATM-call close with r=6.5% and **daily** (not continuous) rebalancing on a spot proxy for futures. Discrete daily hedging adds path noise to hedge P&L, but cannot flip the sign here — gross is negative by ~11 pts on a ~150–250-pt straddle, in both regimes; a more careful continuous hedge would move the number, not the verdict. (For OS-49 there is no such assumption — payoff is exact expiry intrinsic vs. paid debit.)
