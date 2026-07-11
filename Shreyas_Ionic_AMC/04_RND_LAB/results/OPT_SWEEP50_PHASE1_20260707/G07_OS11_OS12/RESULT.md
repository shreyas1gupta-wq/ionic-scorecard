# G07 — OS-11 / OS-12 defined-risk iron condors — Phase-1 triage (STATUS: RUNNING)

_Owner: Arjun Rao (Quant). Campaign OPT-SWEEP-50, Phase-1 fast/cheap pass. This file will be overwritten with final numbers when the engine completes._

## Method (pre-registered, frozen before results seen)
- Underlier: NIFTY index options 1-min (`hf_index_options_1m/options/NIFTY`, 262 weekly-expiry files 2021-05 -> 2026-06) + NIFTY spot 1-min. Data >=09:15 (auction guard L2).
- Strike selection: BS delta computed by inverting IV per strike from the entry-bar quote (skew/term-structure honest), not VIX-flat.
- OS-11: weekly, entry ~5 DTE (target 5, window 2-8), SELL 20d CE+PE, BUY 10d wings. Exit 50%-profit (EOD marks) or expiry.
- OS-12: monthly (last expiry of month), entry ~30 DTE (window 24-36), SELL 25d, BUY ~10d wings. Exit 50%-profit or 21-DTE time-stop or expiry.
- Fill: next-liquid-quote = FIRST liquid bar (vol>0, close>0) on entry day per leg. No-fill legs -> DROP trade (D-031). Sensitivity vs same-day-CLOSE fill computed.
- P&L booked in EXIT period only (Arjun lesson 2026-07), in index RUPEE POINTS and %-of-SPOT (never %-premium). Credit condor only (cr_open>0).
- Costs: COST_STANDARDS 1x — proportional (slippage max(1tick,0.25%)+STT+exch+GST+stamp) applied; brokerage reported separately (₹20x8 orders = 2.13 pts/lot at 1 lot, ~0.2 pts at 10 lots).
- Regime split at 2025-09-01 (Sept-2025 expiry-regime break) — edge must not exist only pooled across it.

## Status
Engine (`scratchpad/ic_engine2.py`) running; per-trade CSVs (`OS11_trades.csv`, `OS12_trades.csv`) and `_summary.txt` will be written on completion. First run confirmed ~1 trade/weekly-expiry (healthy N ~250 for OS-11, ~55 for OS-12). Final verdict pending numbers.
