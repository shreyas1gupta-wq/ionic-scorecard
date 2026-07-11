# G13 Phase-1 triage — OS-26 (bear-call credit spread, regime-gated) + OS-27 (put ratio spread)
_Campaign OPT-SWEEP-50 · owner Arjun Rao (Quant) · 2026-07-07 · FAST/CHEAP pass, NOT certification_

## Result (headline)
| Setup | Verdict | NL edge ₹-pts/trade | NL edge %-spot | Honest ann. Sharpe | Beats uncond? |
|---|---|---|---|---|---|
| **OS-26** bear-call spread, gated (NIFTY<200DMA & neg-mom) | **SURVIVE (fragile)** | **+12.48** | **+0.062%** | ~1.0 (8 tr/yr) | **YES** (+12.5 vs +0.5) |
| OS-26 unconditional (every week, baseline) | (reference) | +0.54 | +0.0005% | 0.09 | — |
| **OS-27** put ratio spread (sell 2×15Δ PE / buy 1×25Δ PE) | **KILL** | +0.42 | +0.0055% | 0.06 | n/a |

NL = next-liquid-quote fill (D+1 first liquid bar); the honest number. SC = same-day-close (optimistic).

## Data lineage
- **Options:** `intraday_options_strategy/datasets/raw/hf_index_options_1m/options/NIFTY/*.parquet` — 261 weekly expiries 2021-05-27→2026-06-02; **257 usable trade-weeks** (1 dropped MemoryError huge file; 2 late-2026 expiries no index-settlement). 1-min, filtered ≥09:15, volume>0 only.
- **Spot:** `.../hf_index_options_1m/index/NIFTY.parquet` 1-min, 1,242 days.
- **200DMA + 20d momentum:** `datasets/index_daily/nse_official_all_indices.parquet` series `Nifty 50`, 2016-01-01→2026-07-06 (2,591 rows) — full warmup before option window.
- **Costs:** `06_TRADING_DESK/COST_STANDARDS.md` @1× (brokerage ₹20+GST/order÷75; STT 0.1% sell; exch 0.035%; stamp 0.003% buy; slippage max(1 tick, 0.25% prem)/leg/side).
- Strikes chosen by BS delta with ATM-IV backed from ATM straddle (Brenner-Subrahmanyam, r=0) — no greeks in raw data; approximate but adequate for triage.

## Guards passed
- Auction bug: ≥09:15 filter ✓  · No-fill on zero-vol bars (drop) ✓ · Next-liquid-quote D+1 fill computed vs same-day-close (A.17) ✓
- Edge denominator-free: ₹-points + %-spot, never %-premium (A.2/A.8) ✓ · P&L booked once at EXIT (no spreading across holding days) ✓
- PIT: gate from daily closes known at entry-day close; NL entry is D+1 → no lookahead ✓ · Sept-2025 Tuesday-expiry regime split reported, not pooled ✓

## Validation battery (Phase-1 subset — full battery deferred to Phase-2)
| Test | OS-26 gated (NL) | OS-27 (NL) |
|---|---|---|
| Per-trade edge >0 (₹-pts / %-spot) | +12.48 / +0.062% ✓ | +0.42 / +0.0055% (≈0) |
| Survives NL fill vs same-close | +12.48 vs +13.09 ✓ (robust) | +0.42 vs +1.56 ✗ (−73%, fill artifact) |
| Present in BOTH regimes (not pooling-only) | pre-Sep +6.80, post-Sep +34.37 ✓ | pre-Sep **−0.31**, post-Sep +4.95 ✗ (edge only post-break) |
| Gate beats unconditional (K-006 test) | +12.48 vs +0.55 ✓ | n/a |
| Sample size | n=34 (~8/yr) — THIN | n=257 |
| Yearly stability (NL ₹-pts) | 22:+15.5 23:−4.5 24:+18.7 25:−2.7 26:+34.4 | 21:+10 22:+7 23:−7.5 24:−8.9 25:+1.7 26:+9 (no stable sign) |

## Degenerate / red flags
- **OS-26 gated:** honest annualized Sharpe **~1.0** (script's 2.48 used a wrong 50-tr/yr assumption; it only trades 8/yr — corrected). Win 85% but that is a short-premium profile. Concentration: single best trade = 24% of gross positive P&L. Edge is **short-delta directional beta** (calls decay because the market fell in the down-trend window), NOT incremental VRP — magnitude leans on 7 post-Sep-2025 (2026 down-trend) trades.
- **OS-27:** win 77% with **W/L 0.31** (classic pennies-in-front-of-steamroller). **Worst trade −488 ₹-pts ≈ 2% of spot in ONE trade** — the naked-extra-short-put left tail; a single gap-down erases years of harvest. Per-trade Sharpe 0.008.

## Verdicts
### OS-26 — SURVIVE (fragile / conditional)
Passes ALL four pre-registered Phase-1 kills: edge >0 in ₹-pts and %-spot; survives next-liquid-quote fill (barely moves); positive in both pre- and post-Sept-2025 halves; and — the K-006 required test — the 200DMA/neg-mom gate materially beats the unconditional bear-call-every-week baseline (+12.5 vs +0.5 ₹-pts; unconditional is a pure ~0). REAL enough to advance, but **FRAGILE**: honest annualized Sharpe ~1.0 (well below the campaign's Sharpe>2 bar), only ~8 trades/yr, and the edge is directional down-trend beta rather than VRP. Per campaign §4.1 + K-006, it should take a Phase-2 slot ONLY after the Family-A VRP survivors, and its real Phase-2 test is **incremental Sharpe over the short-vol book with the short-delta stripped out**.
- **Single weakest assumption:** that a 34-trade, down-trend-conditioned sample generalizes rather than being 2022+2026 regime luck — this is a short-delta directional bet dressed as an option edge.

### OS-27 — KILL
Two pre-registered kills fire: (1) the tiny pooled edge is **regime-only** — pre-Sept-2025 is negative (−0.31 ₹-pts), all of the +0.42 comes from 36 post-break trades; (2) the edge largely **vanishes under next-liquid-quote fill** (+1.56 → +0.42, −73%). Honest edge is economically zero (+0.0055% of spot) before the mandatory Phase-2 2× cost, and it carries a −488 ₹-pt (~2% of spot) single-trade left tail. Net-credit skew harvest that collects pennies and gives them all back in a gap-down.
- **Single weakest assumption:** that the −488-pt gap-down tail is rare/survivable — one such event wipes multiple years of the pennies, and the "edge" doesn't even clear a same-day-close fill artifact.

## Limitations (fast pass)
No 2× cost stress, no DSR/PBO, no walk-forward, no lookahead-audit lag test — all deferred to Phase-2 per campaign design. Delta selection is approximate (ATM-IV proxy). Exit uses daily last-liquid marks for the 50% rule + expiry intrinsic at index close, not intraday-precise stops.
