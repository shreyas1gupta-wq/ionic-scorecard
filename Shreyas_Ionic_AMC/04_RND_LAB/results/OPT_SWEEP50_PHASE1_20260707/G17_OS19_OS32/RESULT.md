# G17 Phase-1 confirm — OS-19 + OS-32 (Arjun Rao, Quant)
_Campaign OPT-SWEEP-50 · fast/cheap confirmation pass · 2026-07-07 · both setups OVERLAP-WITH-OWNED (confirmations routed to owners, NOT fresh families)_

## 0. Scope
Both G17 items are confirmations, not new research tracks:
- **OS-19** (Family C) — vega-neutral term-structure: SELL weekly ATM straddle / BUY vega-matched (~30-DTE) monthly ATM straddle, exit at weekly expiry. **Aakash owns the FF term-structure liquidity-native intake** — this is a light confirm, no build-out.
- **OS-32** (Family F) — SELL ATM straddle the session before RBI/Fed/Budget, exit T+1 after crush. **= the already-killed S-02 family, ported to the index.** Job = honestly RE-CONFIRM the kill on index-liquid NIFTY, not route around it.

## 1. Data lineage (files · rows · max dates)
| Input | Path | Rows / span |
|---|---|---|
| NIFTY option chains 1-min | `intraday_options_strategy/datasets/raw/hf_index_options_1m/options/NIFTY/*.parquet` | 262 weekly-expiry files, 2021-05-27 → 2026-06-09; cols incl strike/option_type/expiry |
| NIFTY spot 1-min | `.../hf_index_options_1m/index/NIFTY.parquet` | 477,738 rows, 2021-05-24 → 2026-06-03 |
| INDIA VIX daily | `datasets/index_daily/india_vix.parquet` | 2,591 rows, 2016-01-04 → 2026-07-03 |
| Event dates | RBI MPC (31) + Union Budget (5), 2021-06 → 2026-04 | **[INFERENCE]** hand-compiled from public record; **Phase-2 MUST verify vs official RBI/NSE on home network.** FOMC excluded (overnight-timing ambiguity for the Indian session — add in Phase-2 with proper T+1-reaction handling) |

## 2. Guards passed
- 09:15 auction-bug filter on all 1-min reads (landmine #2). Timestamps tz-converted Asia/Kolkata.
- **Entry-fill = next-liquid-quote (vol>0) at/after signal time**, NOT same-day-close (A.17 pre-registered). No liquid quote at the ATM strike → trade DROPPED (D-031).
- Edge reported in denominator-free **₹-POINTS and %-of-SPOT** (A.2/A.8 — never return-on-premium). Lot=75 for ₹-value only.
- Costs @1x COST_STANDARDS: slippage 0.25%/leg/side (liquid ATM index), STT 0.1% sell-side, exch 0.035%, brokerage ₹20×2, GST 18%. (2× stress is a Phase-2 gate, not run here — confirm pass.)
- Sept-2025 expiry-regime break: reported as a split, never pooled to manufacture an edge.

---

## 3. OS-32 — pre-event short straddle (S-02 kill re-confirm)

### Results (net @1x, per 1 straddle, ₹-points and %-spot)
| Cut | n | mean pts | %-spot | win | worst pts | per-trade Sharpe |
|---|---|---|---|---|---|---|
| Event straddle (raw) | 36 | **+47.8** | +0.236% | 80.6% | −65.8 | 0.72 |
| — RBI only | 31 | +34.9 | +0.178% | 77.4% | −65.8 | 0.66 |
| — Budget only | 5 | +127.7 | +0.593% | 100% | +20.8 | 1.42 |
| — pre-Sept-2025 | 31 | +55.2 | +0.274% | 83.9% | −54.9 | 0.85 |
| — post-Sept-2025 | 5 | **+1.9** | −0.00% | 60% | −65.8 | 0.03 |
| Unconditional baseline (2-sess Mon straddle) | 210 | +22.6 | +0.110% | 70% | −319.4 | 0.27 |

### The decisive test — is the CRUSH incremental over VIX-matched short-vol? (the exact mechanism that killed S-02)
Event entry VIX (mean 15.6) ≈ baseline VIX (15.5), so events are only mildly richer. Matching each event to same-VIX (±1.5) baseline trades:
| Quantity | value |
|---|---|
| Event raw net | +47.8 pts (t=4.32) |
| VIX-matched baseline net | **+28.3 pts (t=6.37)** ← generic VRP earns most of it |
| **INCREMENTAL (event − matched)** | **+19.4 pts, t=1.63 (NOT significant)**, win 69% |
| RBI-only incremental | **+9.1 pts, t=0.79 (≈ zero)** |
| Budget-only incremental | +83.5 pts, t=2.04, **n=5 (fragile, calendar-obvious)** |
| pre-Sept incremental | +25.8 (t=2.16) |
| **post-Sept incremental** | **−20.0 (t=−0.46) — flips negative** |
| VIX-reweighted baseline (overall) | +24.7 pts vs event +47.8 |

### Degenerate / red flags
- ~60% of the raw event edge is plain short-vol carry (VIX-matched baseline +28.3 of the +47.8). The event-SPECIFIC crush increment is **statistically indistinguishable from zero** (t=1.63; RBI-only t=0.79).
- All the certifiable-looking edge is **Budget, n=5** — too small and too crowded/obvious to build on.
- Incremental edge **flips negative post-Sept-2025** (n=5).
- Tail understated: n=36 never sampled a vol-spike-through-event; worst was only −65.8 while the unconditional baseline shows the real left tail (−319). CIO book rule #1 — this bleeds with the whole short-vol cluster.
- Per-trade Sharpe 0.72 raw — nowhere near the campaign bar (Sharpe>2).

### Verdict: **KILL — CONFIRMED (S-02 holds on index-liquid NIFTY).**
The single weakest assumption if anyone argues to keep it: that the +47.8 raw event mean is a distinct "crush edge." It is not — it is ~60% generic VRP plus a crush increment (+9 pts on RBI, t=0.79) that fails the S-02 resurrection bar (2024-25 crush CI lower-bound must exceed +3%; here the incremental CI straddles zero and post-Sept is negative). Same death as single-stock S-02: the crush adds nothing certifiable over being short vol on a comparable-VIX day.

**Routing / S-02 kill-record:** update STRATEGY_REGISTER S-02 row — index port of the earnings/event short-vol family re-tested on NIFTY macro events (RBI+Budget), incremental crush over VIX-matched short-vol = +9 pts RBI (t=0.79), post-Sept negative; **resurrection condition still NOT met, stays FAILS-PRE-IC.** Do not advance to Phase-2. This line-item counts toward the short-vol family trials ledger (§6, DSR honesty).

---

## 4. OS-19 — vega-neutral term-structure calendar

### Result: NOT EVALUABLE on cataloged data — back leg does not exist at entry
Expiry-coverage index (built from all 262 files): **median listed history = 9 trading days; only 27/262 expiries list ≥20 days.** Weekly (non-monthly) contracts in this HF dataset only appear ~8-9 days before expiry, so a ~30-DTE back-month straddle is simply **not in the data on the entry day.**

Of 263 weekly cycles attempted (front weekly ATM available):
| Outcome | n | % |
|---|---|---|
| Back leg NOT listed at entry | 162 | **61.6%** |
| Back leg listed but ATM straddle unfillable (entry or exit) | 99 | 37.6% |
| Front+back tradeable & filled | **1** | 0.4% |

The 1 filled cycle (+38.0 net pts) is n=1 — meaningless.

### Degenerate / red flags
- **61.6% back-leg-not-listed** eerily mirrors K-012's 61% dead-back-leg exitability wall — but here the cause is **DATA COVERAGE**, not market death. In the real market NIFTY carries 3 liquid serial monthly expiries; the free HF dataset just never captured back-month bars until ~9 days out.
- Therefore this dataset **cannot backtest OS-19** (or any term-structure/calendar needing a liquid ~30-DTE back leg). Any "edge" printed on 1 cycle would be pure noise.

### Verdict: **CANNOT-CONFIRM (DATA-BLOCKED) → do not advance.** Not a clean edge-kill; a data-adequacy failure. On cataloged data OS-19 produces no credible result, so it does not earn a Phase-2 slot.

**Routing / coordinate-with-Aakash (REQUIRED before any Phase-2 escalation):**
- OS-19 IS a candidate vehicle for Aakash's FF term-structure liquidity-native intake (IDEA_PIPELINE row: "FF term-structure on a LIQUIDITY-NATIVE vehicle").
- Direct input to his **pre-registered kill #1 (fwd back-leg drop-rate <20%)**: on the current cataloged HF source the drop rate is **61.6%** — the source FAILS that gate on its face. Before OS-19 can be tested at all, Phase-2 needs a real back-month data source (Angel multi-expiry capture — 2 expiries/day per DATA_CATALOG §1; or NSE full-chain), not the HF free set.
- Do NOT duplicate Aakash's track; hand him the coverage index (`expiry_coverage.parquet`) and this drop-rate as the data-adequacy pre-check.

---

## 5. Kill-criteria adjudication (section-5 pre-registered)
| Setup | edge ≤0 both metrics | edge only pooled across Sept-2025 | vanishes under next-liquid-quote fill | fails vs unconditional parent | VERDICT |
|---|---|---|---|---|---|
| OS-32 | raw +0.236% (no) | post-Sept ≈0 / incremental negative (YES, partial) | fill already applied; cost small | **YES — incremental t=1.63 / RBI t=0.79 ≈ 0** | **KILL-confirmed** |
| OS-19 | n/a (untestable) | n/a | n/a — back leg absent 61.6% | n/a | **CANNOT-CONFIRM / data-blocked** |

## 6. Artifacts
`os32_events.csv`, `os32_events_vixmatched.csv`, `os32_baseline.csv`, `summary.json`, `summary_os32_incremental.json`, `os19_calendar.csv`, `summary_os19.json`, `expiry_coverage.parquet` (all in this dir). Backtest scripts in session scratchpad (`g17_bt.py`, `g17_os19_v2.py`, `g17_os32_vixmatch.py`).
