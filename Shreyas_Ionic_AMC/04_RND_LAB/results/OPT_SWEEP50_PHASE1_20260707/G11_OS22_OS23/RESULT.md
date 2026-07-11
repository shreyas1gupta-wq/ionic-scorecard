# OPT-SWEEP-50 Phase-1 — Group G11 (OS-22 covered call, OS-23 collar)
_Arjun Rao (Quant) · 2026-07-07 · FAST/CHEAP triage · Family D low-alpha overlays (rank 38, 41)_

## Verdict
| Setup | Edge (Rs-pts / %-spot) | Fill under next-liquid-quote | Verdict |
|---|---|---|---|
| **OS-22** monthly ~5% OTM covered call on NIFTYBEES | net **< 0** (cap drag 0.190%/mo of spot > single observed 5%-OTM CE premium 0.13%/mo) | **1/59 cycles fillable** at 5%OTM/~30DTE | **KILL-as-overlay** |
| **OS-23** quarterly zero-cost collar (buy 5% PE / sell 5% CE) | net **< 0** (gives up upside via call AND pays net put premium; put skew ⇒ not truly zero-cost; protection only 4/59 mo) | **0/59 cycles fillable** (needs both legs); 3-month legs absent (max contract history 60d) | **KILL-as-overlay** |

Both are **portfolio risk-reduction / income overlays, NOT standalone Sharpe>2 candidates** — consistent with their own thesis and their rank (38/41). Neither is designed to, nor does, clear the Principal's XIRR>50 / Sharpe>2 bar. Do not advance to Phase-2.

## Data lineage
- Spot: `intraday_options_strategy/datasets/raw/hf_index_options_1m/index/NIFTY.parquet` — 477,738 rows 1-min, 2021-05-24→2026-06-03 (≥09:15 filtered; auction-bug guard applied).
- Options: `.../options/NIFTY/*.parquet` — 262 expiry files; **62 monthly expiries** (last-of-month) 2021-05→2026-06.
- INDIA VIX: `datasets/index_daily/india_vix.parquet` (2016→2026-07-03) — regime context only.
- Costs: `06_TRADING_DESK/COST_STANDARDS.md` @1x (STT 0.1% sell, exch 0.035%, GST 18%, slip max(1tick,0.25% prem)).
- 59 monthly cycles carried spot on both ends. Lineage CSVs: `cycles_raw.csv`, `cycles_analyzed.csv`; code `extract.py`, `final_analysis.py`.

## Guards / bug caught (audit trail)
- **Swallowed-exception bug in v3 extract** produced a fake "0/61 fills" — the pyarrow timestamp filter raised `ArrowNotImplementedError` (tz `+05:30` vs `Asia/Kolkata`, unit mismatch) inside a `try/except` that silently returned empty. Would have been mis-read as "market illiquid." Refit to filter on `trading_day` (string) — confirmed working (911 rows/day). **The fill numbers below are post-fix.**
- **ITM-fallback bug** in first pass: "nearest available strike" grabbed deep-ITM calls (Kc=11500 vs spot 15200, premium 3949) when the 5%-OTM strike didn't trade. Replaced with a strict [1.03–1.08]×spot / [0.92–0.97]×spot band + DROP-on-no-fill (D-031).

## Why KILL (data + structure)
**Binding fill fact:** at the specified 1-month (~30 DTE) write horizon, the 5%-OTM monthly-serial strikes are essentially absent from traded quotes in our catalog — 38/59 entry-days had **zero** CE trades at all; only **1/59** cycles fills the covered-call CE, **0/59** the collar. The pre-registered kill "edge vanishes under next-liquid-quote fill" fires unambiguously.
- *Caveat (honest):* this 2%/0% fill rate is a **DATA-COVERAGE limit of the HF weekly-centric dataset**, not real-world illiquidity — actual NIFTY monthly 5%-OTM options are highly liquid, huge capacity. So the fill-kill is a Phase-1 cheap-data blocker; the **decisive** kill is the economics below + the VRP/BXM prior. A definitive test would need a monthly-serial source (Angel capture / NSE monthly bhavcopy) — but there is no case to spend it on a documented non-alpha overlay.

**Deterministic economics (option-fill-free, from spot; NIFTY +56% over the window):**
- OS-22: mean upside GIVEN UP to the 5% cap = **0.190%/mo of spot** (35 pts; 11.2% cumulative over 59 mo; up->5% months = 17%). The one observed 5%-OTM CE premium was **0.13% of spot** (Feb-2026, VIX≈12). Premium < cap-drag even in calm vol ⇒ overlay net-negative in points BEFORE costs → clearly negative after. Textbook BXM: it trades right-tail upside for lower variance, it does not add edge.
- OS-23: adds a bought put that protected only **4/59** months (down>5%), yet is paid every cycle; put skew makes the 5% put richer than the 5% call ⇒ **not zero-cost**, persistent net-debit drag ON TOP of the covered-call cap. Strongly negative overlay in a bull tape; a pure drawdown/vol reducer.
- Regime: post-Sept-2025 (n=8, NIFTY −0.55%/mo) cap drag falls to 0.037% — the overlay only "helps" in flat/down regimes, i.e. regime-dependent, not a pooled edge. No edge survives the Sept-2025 break.

**Correlation note (CIO book rule #1):** OS-22 is net-short vega on the upper wing; adds to the firm's one correlated short-vol cluster with negative carry — worst of both worlds. OS-23 is long-vol (bought put) → fights VRP (A.1). Neither earns its slot.

## Single weakest assumption
That a 1-month/quarterly 5%-OTM overlay is *fillable at spec on Phase-1 cheap data* — it is not (2%/0%). But the verdict does not rest on that: the deterministic cap-vs-premium and put-skew drag kill both as alpha regardless of fill.
