# SWING_MOMENTUM — REAL-COST RE-RUN (V2 "Line A", survivorship-safe)
**Author:** Tara Singh (Execution & TCA, E-015). **Date:** 2026-07-18.
**Scope:** re-run `swing_momentum/run_swing.py`'s published V2 result (the honest,
survivorship-fixed version cited in `RESULTS.md` — NOT the "Line B" version a sibling agent
is separately correcting) with the firm's APPROVED cost model
(`Shreyas_Ionic_AMC/06_TRADING_DESK/COST_STANDARDS.md`, STATUS: APPROVED, D-021, 2026-07-03)
in place of the flat 30bps assumption. Tags: [DATA] measured, [INFERENCE] flagged, [OPINION] flagged.

**Reproducibility:** `swing_momentum_realcost_rerun.py` (this folder) reproduces `run_swing.py`'s
signal engine verbatim (trend-template + RS rank + regime gate + 15% weekly trailing stop —
copied, not edited; `run_swing.py` itself untouched, legacy file). Confirms the published
baseline exactly (CAGR/Sharpe/MaxDD/Calmar match `RESULTS.md` to 1 decimal) before swapping the
cost line. Full console log: `swing_momentum_realcost_rerun_log.txt`.

## 1. Structure (unchanged from V2)
Weekly rebalance, top-20 Minervini-trend-template names ranked by RS (0.6×12m+0.4×6m),
equal-weight, regime-gated (Nifty>200&50DMA + breadth>40%), 15% weekly-close trailing stop.
No param changes, no new signal — this memo only touches the cost line.

## 2. Assumed costs — line items (this is the correction)
`run_swing.py`'s own header comment: `COST_BPS = 30  # round-trip per name turnover
(brokerage+STT+slippage), bps`. **This bundled number is arithmetically inconsistent with
COST_STANDARDS on its own terms** — STT on equity DELIVERY (this is a days/weeks swing
strategy, not intraday) is 0.1% **both sides** = 20bps round-trip on the statutory line alone,
before slippage, brokerage, stamp duty, exchange, or GST are added. A flat 30bps RT leaves only
10bps for slippage+brokerage combined — below even the **large-cap** one-way slippage floor
(10bps) doubled to a round trip (20bps), let alone the small-cap floor (35bps one-way / 70bps RT)
that applies to most of this universe. [DATA — arithmetic from COST_STANDARDS' own tables]

Realistic per-event cost applied (one-way, per buy or sell leg):
| Component | Buy leg | Sell leg | Source |
|---|---|---|---|
| STT (equity delivery) | 10.0 bps | 10.0 bps | COST_STANDARDS §Per-order charges |
| Stamp duty | 1.5 bps | — | delivery buy only |
| Exchange/SEBI/GST (bundled, sub-bp each) | ~0.5 bps | ~0.5 bps | negligible at this position size |
| Slippage tier × volume-multiplier | 10/20/35/50 bps × {1x,2x,3x,NO-FILL} | same | COST_STANDARDS §Slippage floors + Dynamic rule |
| **Statutory total (fixed)** | **~12.0 bps** | **~10.5 bps** | not doubled in the 2x-stress (these are regulatory rates, not estimates) |

Tiering proxy [INFERENCE]: no full-universe market-cap series exists for 2005-2025, so
liquidity tier is assigned from 20-day trailing average TRADED VALUE (₹, PIT-safe, `.shift(1)`)
— ≥₹25cr/day large, ₹5-25cr mid, ₹0.5-5cr small, else micro. This is a liquidity-based proxy
for the market-cap tiers in COST_STANDARDS, not a literal sector classification, but it serves
the same underlying purpose (cost scales with how thin the name actually trades).

**Coverage gap (disclosed, not hidden):** OHLCV+volume exists in this repo only for 238/976
close-panel symbols (`raw/nifty500/*.csv`, 24.4% of names by count, 16.4% of actual weekly
entry/exit events by count — `n_evt_covered=830/5072`). For the other ~84% of events, no
volume/OHLC data exists anywhere in the repo to check tier, circuit-lock, or ADV — this
matches Dhruv Kapoor's assessment finding this data gap independently. **Conservative default
applied to uncovered events: small-cap tier (35bps) + full statutory, no lock-check possible**
— the retail-conservative direction per charter, but it means the circuit-lock and ADV-breach
figures below are measured only on the checkable 16.4% subset, not the full book.

## 3. Realistic fill scenario
- **Circuit-lock = NO FILL, ever** (`lib/execution_realism.circuit_locked`, zero-range/band-pin
  detector) — entry deferred (name simply not added that week, retried next rebalance since
  RS-rank re-evaluates fresh); exit deferred (name stays held, stop/rank-out re-checked next week).
- **Volume-conditional multiplier** (`slippage_multiplier`): day-volume ≥50% of 20d median → 1x
  tier floor; 20-50% → 2x; <20% → 3x; zero/absent → NO FILL — same as the flat rule, this
  requires OHLCV, so only applied on the 830 checkable events.

## 4. Margin / worst-case MTM
N/A — this is a long-only cash-equity strategy (no options/derivatives, no margin structure to
model beyond the ₹10cr capital-at-risk itself; MaxDD is the risk figure, reported below).

## 5. Results — original (flat 30bps) vs realistic (tiered + statutory + circuit/no-fill)
| Segment | Metric | Original (30bps flat) | Realistic | Δ |
|---|---|---|---|---|
| Full 2005-25 | CAGR | +11.6% | **+9.5%** | −2.1pp |
| | Sharpe | 0.43 | **0.30** | −0.13 |
| | MaxDD | 23.0% | **24.4%** | +1.4pp |
| | Calmar | 0.51 | **0.39** | −0.12 |
| IS (2005-~2019) | CAGR | +9.8% | **+7.8%** | −2.0pp |
| | Sharpe | 0.34 | **0.19** | −0.15 |
| OOS (~2019-2025) | CAGR | +16.1% | **+13.7%** | −2.4pp |
| | Sharpe | 0.60 | **0.48** | −0.12 |
| | MaxDD | 23.0% | **23.6%** | +0.6pp |
| | Calmar | 0.70 | **0.58** | −0.12 |
| Always-on (no regime) | CAGR | +21.7% | **+16.5%** | −5.2pp |
| | Sharpe | 0.66 | **0.49** | −0.17 |

**2× promotion-gate stress** (doubles the slippage-tier estimates only — statutory STT/stamp
are fixed regulatory rates, not doubled, per the "2x ALL of the [cost] assumptions" intent):
| Segment | CAGR | Sharpe | MaxDD | Calmar |
|---|---|---|---|---|
| Full, 2x | **+5.3%** | **0.02** | 31.9% | 0.17 |
| OOS, 2x | **+7.8%** | **0.19** | 28.2% | 0.28 |

## 6. Circuit-lock materiality check (the specific ask)
Of 5,072 total entry+exit events across the backtest, 830 (16.4%) had OHLCV coverage to check.
Of those checkable events, **16 hit circuit-lock (1.9% of checkable events, 0.3% of all
events)**; zero hit a zero/absent-volume no-fill. **Verdict: circuit-lock is NOT material at
this strategy's WEEKLY-close rebalance granularity** — a weekly snapshot rarely lands on the
exact day of a lock. Caveat [INFERENCE]: this likely UNDERSTATES the real-world number, because
actual execution would attempt to buy the breakout itself (intraday, the day momentum triggers)
— exactly the upper-circuit-prone moment COST_STANDARDS' dynamic rule was written for — not a
5-trading-days-later weekly snapshot. A daily/intraday-execution version of this strategy would
need this re-measured at daily granularity; the weekly architecture as currently coded cannot
surface that risk.

**ADV/capacity cap (separate finding, not folded into the CAGR above):** at the strategy's own
stated ₹10cr AUM ceiling, position size ₹10cr/20 = ₹50L per name. Of 408 checkable entries,
**94 (23%) would breach the ≤10%/5%-of-20d-ADV cap** — i.e. nearly 1 in 4 measurable trades in
this universe would need multi-day execution or a smaller effective size than the equal-weight
model assumes. This is a genuine capacity constraint, distinct from the slippage question, and
not currently priced into any of the CAGR numbers above (it would only bind in live sizing).

## 7. Sim-vs-paper gap
N/A — this strategy has never been forward-tested or paper-traded; there is no live fill data
to reconcile against. This memo is purely a backtest-cost-realism correction.

## 8. Verdict — SURVIVES at 1x, MARGINAL at 2x, sign never flips
- **1x realistic costs: edge is REAL and intact.** OOS CAGR +13.7% / Sharpe 0.48 / Calmar 0.58
  is a modest give-up from the published +16.1%/0.60/0.70, not a collapse. Per the firm's
  low-t/effect-size discipline: this is exactly the "real but modest" case to KEEP, not kill —
  logic (regime-gated trend-template momentum) is sound and costs did not flip the sign or gut
  the edge.
- **2x promotion-stress: passes on sign, not with margin.** Full-period Sharpe at 2x collapses
  to 0.02 (statistically indistinguishable from zero) though CAGR stays positive (+5.3%); OOS
  (the more policy-relevant recent regime) holds up better at Sharpe 0.19/CAGR +7.8%. **This is
  a border-line pass of COST_STANDARDS' promotion gate, not a comfortable one** — [OPINION] I
  would not block promotion on this alone (sign never flips, OOS margin is real), but I would
  not certify it as "clears costs with room to spare" either.
- **The bigger catch than the re-run itself:** the ORIGINAL flat-30bps assumption was already
  below the statutory STT floor alone (20bps RT) before slippage — this would have understated
  costs for EVERY future backtest reusing that constant, not just this one. [DATA]
- **Genuine data gap, not a silent assumption:** only 16.4% of transaction events are
  OHLCV-checkable in this repo; the circuit-lock (1.9%) and ADV-breach (23%) figures are
  measured on that subset and defaulted conservatively elsewhere. A full-universe volume pull
  (2013-2025, all ~1000 names, not just the 238 already on disk) would tighten this — flagged
  as the next data-office ticket if this strategy is prioritized further, not done here as it
  is a materially larger pull than this cheap re-run's scope.

## Files
- `swing_momentum_realcost_rerun.py` (this folder) — full re-run script, reproducible
- `swing_momentum_realcost_rerun_log.txt` (this folder) — console output, both cost regimes
- Inputs (read-only, unmodified): `swing_momentum/run_swing.py`, `swing_momentum/RESULTS.md`,
  `swing_momentum/processed/{eq_close,membership}.parquet`, `raw/nifty500/*.csv` (238 symbols),
  `Shreyas_Ionic_AMC/04_RND_LAB/lib/execution_realism.py`,
  `Shreyas_Ionic_AMC/06_TRADING_DESK/COST_STANDARDS.md`
