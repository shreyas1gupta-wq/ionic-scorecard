# K-012 Resurrection — Leg 3 of 3: Thin-Strike Fill Audit
**Owner:** Tara Singh (Execution & TCA) · **Date:** 2026-07-05 · **Charter Q:** does the recommended (equal-premium, 3x-median-cap) forward P&L survive honest, volume-gated fills?

## VERDICT: **MARGINAL — state the honest number**
**Forward (2025-26), n=199 attempts: honest +Rs3.88 per Rs100 deployed, vs the +Rs10.04 frictionless-cap headline (38.6% retained).** Below the "≥half the headline" bar for a clean FILLS-SURVIVE, but unambiguously positive, not noise, and not FILL-FICTION either.

**The story is a FILL-RATE crisis, not a COST crisis:**
- **61.3% of forward signals (122/199) are DROPPED outright** — the back-leg (2nd-forward-month) CE has **zero recorded trading volume** on the exact day the FF signal requires entry. Drop cost = **-5.86pp of the -6.16pp total gap (95%)**.
- Of the 77 trades that DO clear both entry legs, tiered slippage only costs **-0.30pp (5% of the gap)** — conditional-on-fill economics are close to headline: PF 2.24→2.05, honest fill-conditional average **+10.03/Rs100** (vs +10.80 headline on the same 77 — a 7% haircut, not the story).
- The headline's own **worst single trade (-464% of notional, BOSCHLTD)** is itself one of the dropped trades — the backtest's tail-risk number rests on a fill that could never have happened.
- The failure is **structural, not stock-picking**: even mega-cap, liquid names (APOLLOHOSP, SUNPHARMA, BRITANNIA, COLPAL) show a 100% forward drop rate on this exact structure — 2nd-forward-month single-stock CE liquidity is thin across the Indian large-cap universe, not just in a few bad names.

---

## 1. Structure (verified, file path + row count)
- **Trade universe:** `intraday_options_strategy/buying/forward_factor_v2.parquet` (4,585 rows, 205 syms, entry 2021-07-12→2026-05-08). SELL front-month CE / BUY back-month (2nd forward) CE, **same strike** (nearest-to-spot at entry). Entry = peak-FF day across a [30,25,20,15,12]-session lookback (`forward_factor_v2.py` L55-76). Exit = 2 sessions before front expiry, both legs together.
- **Slice audited:** large-cap gate (symbol's first FF candidate pre-2024-01-01) ∩ FF≥0.25 = **673 trades / 54 symbols**, exactly matching `results/S-03/20260704_shuffle/config.json` and `verdict.md` (independently re-derived, row counts asserted in code). BUILD (entry≤2024-12-31) = 474; **FWD (entry>2024-12-31) = 199** — the resurrection's whole evidentiary basis.
- **Raw price/volume source:** `intraday_options_strategy/datasets/raw/hf_index_options_1m/stocks_options/<SYM>/<EXPIRY>.parquet` — the **same files** `forward_factor_v2.py` priced legs from (`dispersion_strategy.SOPT`). Confirmed dual-schema empirically (not just per CLAUDE.md's note): HF 1-min (tz-aware, `open_interest` col) pre-Apr24/post-Aug25; bhavcopy DAILY (`settle`+`oi` cols, comprehensive one-row-per-strike-per-day) for Apr24-Aug25. **Bhavcopy rows carry a nonzero theoretical close/settle at ZERO volume** (verified: ABB 5600 CE, 2024-04-26, close=1068.55 settle=1047.25 **volume=0**) — `forward_factor_v2.leg_px` gates only on price>0, never on volume. That gap is exactly what this audit closes.
- **Cross-check:** re-derived all 4 leg prices per trade via the identical `dispersion_strategy._series`/`_nearest` pricer (byte-level import, not reimplementation) — **100.0% match (673/673)** vs the stored `CE_fe/be/fx/bx` values, confirming identical data lineage before any volume analysis was trusted.

## 2. Assumed costs — line items (headline / frictionless-cap baseline)
| Item | Value | Source |
|---|---|---|
| Slippage | flat 1.5% premium, one-way, both legs, both sides | `forward_factor_v2.py SLIP=0.015`; sits at the **top** of COST_STANDARDS' approved "single-stock near-ATM: 0.5–1.5% premium" band |
| Sizing | equal-premium: qty = min(100/CE_be, **3×median(100/CE_be) = 6.0**) per Rs100 notional | reconstructed [INFERENCE] — script not on disk, see §5 |
| Liquidity gate | **none** — price>0 only | this is the hole being audited |
| Circuit/volume rule | **not applied** | this is the hole being audited |

Headline reproduction (validates the reconstruction): n=673, win 71.8%, avg_win 29.2, avg_loss -33.1, **PF 2.24**, total **Rs7,812.1** (register: 7,812.0), worst **-464.4** (register: -464.0) — matches `trading_brief_stats.json` to <0.1%. FWD headline avg **+10.04/Rs100** (SIZING_RECHECK quotes +9.91 — 1.3% off, the closest of the three independent reconstructions run today, see §5).

## 3. Realistic fill scenario
**Method:** for all 4 legs × 673 trades, pulled exact-day traded volume (+OI where present) for the exact strike/expiry from the raw files above; classified vs COST_STANDARDS/`execution_realism.py` tiers (day-vol / trailing-20-session median of **that specific contract**, PIT — strictly prior sessions only):

| Tier | Rule | Slippage |
|---|---|---|
| NORMAL | ratio ≥ 0.5 (or first-ever trading day, no history to compare — see caveat) | 1.5% (base) |
| THIN | 0.2 ≤ ratio < 0.5 | 3.0% (2×) |
| THIN-ABRUPT | 0 < ratio < 0.2 | 4.5% (3×) |
| UNTRADED | zero volume / no row / 0-close that day | **NO FILL** |

**Per-leg tier distribution (all 673 trades):**
| Leg | NORMAL | NORMAL-NOHIST | THIN | THIN-ABRUPT | UNTRADED |
|---|---|---|---|---|---|
| front-entry (fe) | 608 (90.3%) | — | 15 | 15 | 35 (5.2%) |
| **back-entry (be)** | 62 (9.2%) | 212 (31.5%) | — | — | **399 (59.3%)** |
| front-exit (fx) | 439 (65.2%) | — | 97 | 122 | 15 |
| back-exit (bx) | 538 (79.9%) | 10 | 12 | 4 | 109 (16.2%) |

**Back-leg entry is the single point of failure.** Standing-OI supplementary check (COST_STANDARDS: "standing OI **or** volume required") on the 399 UNTRADED back-entries: 228 (57%) have no data row at all that day; of the 171 that do, **141 (82.5%) show zero OI too** — these are dead markets, not quiet ones. Only 30/399 (7.5% of all UNTRADED cases) show any standing interest at all.

**Drop / defer resolution:**
| Action | Rule applied | Count (673) | Count (FWD-199) |
|---|---|---|---|
| **DROP** (either entry leg UNTRADED) | trade never happens | **399 (59.3%)** | **122 (61.3%)** — 100% have be=UNTRADED |
| DEFER (exit leg UNTRADED → next traded day, re-tiered) | found within same file | 11 (all back-exit, 1 session) | 2 |
| SETTLE-FALLBACK (no future fill found) | never triggered | 0 | 0 |
| Surviving trades | | 274 (40.7%) | **77 (38.7%)** |
| Slippage-escalated survivor (≥1 leg THIN/THIN-ABRUPT) | | 100/274 (36.5%) | 24/77 (31.2%) |

## 4. Margin & worst-case MTM
COST_STANDARDS treats calendars as spread-margin (well below the ~12% notional for a naked short strangle) — no independent SPAN recompute done here (no SPAN dataset on hand; flag to Aakash/Structurer if K-012 proceeds to a live-vehicle design). What this audit DOES measure directly — realized worst-case P&L per Rs100 notional:
| | Headline (frictionless) | Honest (survivors only) |
|---|---|---|
| Worst trade, full 673 | **-464% of notional** (BOSCHLTD, Jul-2025) | **-258%** |
| Worst trade, FWD-199 | -47.5% (AUBANK) | **-50.7%** (AUBANK, same trade — deferred back-exit made it marginally worse) |

The headline's own worst-case tail (-464%) is **itself a dropped trade** — both its front-exit AND back-exit were UNTRADED that day; the -464% mark could never have been realized because the position could never have been fully closed (or entered) at those prices. **Any margin buffer sized off the frictionless worst-case is sized off a fill that doesn't exist.** The honest worst-case (-258% full sample / -51% forward) is the number to reserve against.

## 5. Sizing reconstruction — cross-validated three ways
No script survived for the sizing recheck (grepped repo-wide for the recorded `cap: 1201.7857142857142` and "premium_cap" — zero hits beyond the two summary docs). I reconstructed independently as `qty=min(100/CE_be, 3×median(100/CE_be)=6.0)`; **Nikhil (RED_TEAM_FF_RESURRECTION.md) and Sameer (SENSITIVITY_FF_SIZING.md) reconstructed independently in parallel and, once their differently-parameterized formulas are algebraically unwound, land on the exact same sizing rule** (Sameer's `target=median(CE_be)=50, cap_mult=3` × his separately-doubled pnl convention is identical to mine after substitution) — three independent analysts converging on one formula is good evidence it's right, even though none of us can explain the recorded "1201.79" scalar (Sameer's hypothesis: an external lot-size/ADV reference now lost — plausible, unverifiable, and **does not matter**: my liquidity read comes from raw traded volume, not from the cap formula). My BUILD/FWD split (+12.27 / +10.04) is the closest of the three to `SIZING_RECHECK.md`'s quoted +12.43/+9.91 (Nikhil ~7% off, Sameer ~2.1× off and self-flagged as such) — used as this audit's baseline for that reason.

## 6. Validating the 3× liquidity cap (task requirement)
- **PIT/lookahead:** the reconstructed cap uses `median()` over the **full 673-trade sample** (2021-2026) — a build-2022 trade's cap is informed by 2026 premiums. Technically lookahead (T6-class). **Practically small**: an expanding-median PIT-honest cap (≥20 prior obs) seen by FWD trades ranges 6.00-6.40 vs the lookahead value of 6.00 — under 7% different. Doesn't move the verdict; still worth fixing in any production spec (Sameer's memo makes the identical recommendation independently).
- **Is 3× of it absorbable without moving the market?** This question is **moot at the scale it's asked**. qty_capped ≤ 6.0 "premium units" (≤Rs36 of the cheapest legs) is trivially smaller than real NSE lot sizes and real daily volumes (hundreds to 1.4M+ units on the days these contracts DO trade — see §3 table). The cap was never going to move any market. **What actually gates this strategy is binary, not continuous: does the back-month contract trade at all that day.** A sizing cap — of any width — cannot fix a zero. This is the core finding: the SIZING_RECHECK's framing ("equal-premium books more contracts on cheap strikes, exactly where fills are fictional") turns out to be the wrong mechanism — cheap-premium trades were **not** the more fragile ones (see below) — but the underlying liquidity worry was directionally correct for a different reason (contract EXISTENCE, not contract PRICE).
- **Correction to the SIZING_RECHECK's own hypothesis:** sorting the 673 trades into qty_capped quartiles, the **cheapest/most-capped quartile has the LOWEST drop rate (48.8%)** and the **most-expensive quartile has the HIGHEST (70.6%)** — the opposite of what "cheap strikes = fictional fills" predicts. Reason: CE_be (premium level) is driven by the underlying stock's per-share PRICE, not its option-market ACTIVITY — a Rs30,000 stock (e.g. BOSCHLTD) has expensive ATM premium regardless of how often its options actually trade. Liquidity risk here tracks the **stock's F&O activity**, not its **premium level**. (Full quartile table in the per-trade CSV / reproducible from `qty_capped`.)

## 7. Headline vs Honest — full breakdown
| Period | n | Headline avg | Honest avg (dropped=0) | Honest avg (survivors only) | Retention |
|---|---|---|---|---|---|
| BUILD | 474 | +12.27 | +2.21 | +5.32 (n=197) | 18.0% |
| **FWD** | **199** | **+10.04** | **+3.88** | **+10.03 (n=77)** | **38.6%** |
| Full | 673 | +11.61 | +2.71 | +6.94 (n=274) | 23.3% |

**pp decomposition, FWD (the number that matters for K-012):**
| Step | Rs/Rs100 | pp cost | % of total gap |
|---|---|---|---|
| (0) Headline, frictionless-cap | +10.04 | — | — |
| (1) After DROPS only (survivors keep original fills) | +4.18 | **-5.86pp** | **95.1%** |
| (2) After drops + tiered slippage on survivors | +3.88 | -0.30pp | 4.9% |
| **Total honest gap** | | **-6.16pp** | (**-61.4%** of headline) |

Sim-vs-paper gap: **N/A** — S-03 has no paper/live fills yet (K-012 is a killed idea under resurrection review, not on PAPER_LEDGER). This is a backtest-vs-honest-backtest audit, not a paper reconciliation.

## 8. Recommendation (Derivatives/structure lens, per charter)
The edge, where fillable, looks intact (PF 2.05 vs 2.24 honest-survivor vs headline; fill-conditional forward average +10.03 vs +10.80 headline — a 7% haircut, not a collapse). The problem is that **61% of signals aren't fillable at all**, structurally, across the large-cap universe (even APOLLOHOSP/SUNPHARMA/BRITANNIA/COLPAL = 100% FWD drop rate) — 2nd-forward-month single-stock CE liquidity is thin market-wide in India, not a name-selection problem. Two structural fixes worth costing before any resurrection, neither requiring new data:
1. **Ex-ante liquidity pre-filter** (COST_STANDARDS already licenses this — "standing OI or volume at the strike required" — just never wired into `forward_factor_v2.py`): require back-leg volume or OI above a floor over the trailing 5 sessions before the FF signal is allowed to fire. This converts today's "signal, then discover 61% can't be filled" into "only signal the 39% that can" — mechanically this is close to what the 77 honest survivors already show (+10/Rs100), just decided BEFORE the fact instead of after.
2. **Shorter back-leg tenor** (near/next serial instead of next/next) if capacity allows — worth a Structurer (Aakash) pass on whether a 1-month-gap calendar preserves enough forward-vol signal to be worth the FF re-derivation.

## Files
- `results/S-03/20260705_resurrection/fill_audit.py` — full audit code (slice rebuild + sizing reconstruction + per-leg volume/OI pull + tier/defer/settle logic), checkpointed.
- `results/S-03/20260705_resurrection/fill_audit_per_trade.csv` — 673 rows × 38 cols: per-trade identifiers, qty_capped, headline vs honest pnl100, and per-leg (fe/be/fx/bx) tier/volume/median20/history-days/slippage/exit-note.
- `results/S-03/20260705_resurrection/fill_audit_run.log`, `fill_audit_summary.json` — run checkpoint + xcheck validation (100.0% match).
