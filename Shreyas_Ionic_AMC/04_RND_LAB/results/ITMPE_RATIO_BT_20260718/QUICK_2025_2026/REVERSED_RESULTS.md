# REVERSED-STRATEGY PREVIEW — 2025-2026 only, ~18 cycles, ungated, NOT CERTIFIED

**HINDSIGHT-BIAS WARNING (read this first):** this reversal was requested and built **because the
original structure lost money on this exact 2025-01→2026-06 window** (see `QUICK_RESULTS.md`).
Choosing to test "the other side" AFTER observing that the original lost is in-sample knowledge —
it is close to definitionally guaranteed to look good on THIS SPECIFIC realized path, since the
two are near-exact mirrors of the same price moves. **This is not evidence of a real long-premium
edge.** The only honest test is the full-history gated run (elsewhere), on data this reversal's
selection could not have seen. Treat everything below as "what the other side of this one path
looked like," not as a validated strategy.

Mechanics: bull → **BUY** 1 ITM PE (≈500 premium) + **SELL** 2 OTM PE (naked); bear → **BUY** 1 ITM
CE + **SELL** 2 OTM CE. Same signal, same weekly-Tuesday flip mechanics, same window, same 18
cycles. Per instruction, this run **reused the exact strikes/dates/expiries already in
`quick_trade_ledger.csv`** — no strike search or signal logic was re-run; only the long/short roles
flipped and costs were recomputed fresh for the new action direction. Script:
`run_reversed_backtest.py` (this folder).

---

## 1. Headline table

| Metric | Cell A (two-sided) | Cell B (bull-only) |
|---|---|---|
| Total P&L, net-of-cost | **+₹2,80,739** | **+₹1,18,728** |
| Total P&L, 2×-cost stress | +₹2,68,050 | +₹1,11,368 |
| Win-rate by cycle | 9/17 = 52.9% | 11/17 = 64.7% |
| Max drawdown (₹, realized) | −₹91,661 (2025-06-27) | −₹1,26,150 (2025-06-27) |
| **Worst cycle** | Cycle 1, 2025-01-01→01-30, **−₹26,160** (original was **+₹25,737** — this was the original's 3rd-best cycle) | Cycle 10, 2025-10-01→10-28, **−₹27,409** (original was +₹26,977) |
| **Best cycle** | Cycle 16 (the Apr-2026 crash cycle), **+₹71,345** (original was **−₹73,501**, its worst) | Cycle 7, 2025-06-27→07-31, +₹57,424 (original was −₹58,538) |
| ROM, annualized (new margin) | **+64.8%** | **+19.8%** |
| ROM, total window | +102.9% | +29.2% |

(17 cycles, not 18 — cycle 15/Cell A had no original position to mirror: the original's ITM-CE
strike search failed outright that cycle, so there is nothing to reverse.)

## 2. The algebra check (requirement 1 — costs are NOT mirrored away)

Computed by refetching the **raw option CLOSE** (not the slippage-adjusted fill) at every original
ledger event's exact date/strike/expiry, then verifying the mirror identity empirically rather than
assuming it:

```
Cell A:  max|orig_gross_leg + rev_gross_leg| across all 104 legs = 0.000000  (exact — same close
         prices, opposite economic role, confirms no other divergence crept in)
Cell A:  original gross (price-only, no costs) = −₹2,93,435   original cost = ₹12,840
         original net (ledger)                  = −₹3,06,274  (matches QUICK_RESULTS.md exactly)
         reversed gross = +₹2,93,435 (= −original gross, exact)
         reversed cost  = ₹12,695  (recomputed FRESH for BUY-ITM/SELL-OTM directions — NOT copied
                                    from the original; similar magnitude by coincidence, not by rule)
         reversed net   = ₹2,93,435 − ₹12,695 = ₹2,80,739

Cell B:  original gross = −₹1,26,091   original cost = ₹7,485    original net = −₹1,33,577
         reversed gross = +₹1,26,091   reversed cost  = ₹7,364    reversed net = ₹1,18,728
```

**Does the gross swing survive 2× costs?** Cell A: |gross|=₹2,93,435 vs 2×(orig+rev cost)=₹51,071 —
gross dominates by **11.5×**. Cell B: |gross|=₹1,26,091 vs 2×(₹14,849)=₹29,698 — dominates by
**8.5×**. Costs are a real but small drag here (~2-4% of the swing) — this window's result is a
genuine price-mirror effect, not a costs-washed-out illusion. That is expected: the whole point of
a same-underlying-data reversal is that gross P&L mirrors near-exactly; the interesting number was
never "does it survive costs" (it obviously will, on a large enough swing) but whether the
**structural risk** changed — see §3.

## 3. NEW margin model (requirement 2 — the honest higher denominator)

Original structure: 1 short (ITM) + 2 long (OTM) = **bounded max loss** (the 2 long lots'
convexity eventually overwhelms the 1 short beyond the hedge strike).
Reversed structure: 1 long (ITM) + 2 short (OTM) = **net 1-lot-equivalent naked short exposure**
beyond the OTM strikes — open-ended, not capped, because only 1 long lot offsets 2 short lots.

**Formula used** (stated per instruction, analogous in style to the original's simplification):
```
naked_2short_pts = 2 × (0.12 × spot)                         [2 lots, each at 12% notional]
margin_pts        = max(0, naked_2short_pts − long_ITM_entry_premium)   [offset: premium paid for the 1 long]
```

| | Cell A | Cell B |
|---|---|---|
| Avg naked-2-short margin (no offset) | 5,841.7 pts | 5,881.7 pts |
| Avg margin used (offset by long premium) | **5,335.1 pts** | **5,384.9 pts** |
| Offset ratio (margin/naked) | 0.913 | 0.915 |
| vs ORIGINAL hedged-structure margin (2,776.0 / 2,791.3 pts) | **1.92×** | **1.93×** |

The long ITM premium (≈500 pts) only offsets ~9% of the naked-2-short base (2×0.12×spot≈5,760 pts
at spot≈24,000) — a single long lot's premium is small relative to two lots' full notional margin.
**Margin nearly doubles** relative to the original's capped structure. ROM in §1 uses this honest,
higher denominator — that is why ROM (+65%/+20%) is a much smaller multiple of the net-P&L-on-fixed-
capital story than the raw rupee totals alone would suggest.

## 4. Worst-case behavior (requirement 3)

**Biggest single-cycle loss**: Cell A cycle 1 (−₹26,160 / −349 pts per lot-unit at lot=75), Cell B
cycle 10 (−₹27,409). Both are modest relative to the ~5,300-5,900 pt margin base (loss ≈ 5-6% of
margin) — **this 18-cycle sample never contained a move violent enough to test the reversed
structure's true open-ended tail.** The realized worst cases stayed well inside the sampled range
of ordinary trending moves; nothing here should be read as "the open-ended risk is fine in
practice" — it means the tail simply wasn't drawn in this window.

**The April-2026 crash cycle (cycle 16), specifically what happened:**
- **Cell A**: the original held the disastrous CE-short (rally hurt it, −₹73,501, its worst cycle
  overall) via a full-cycle short-ITM + hedge structure that was continuously in the market. The
  reversed long-ITM-CE + naked-2-short-OTM-CE mirrors that same rally into a **+₹71,345 gain** — the
  best cycle in the entire reversed run for Cell A. The mechanism: the long CE gained from the same
  rally that hurt the original's short CE; the 2 naked short OTM CE legs also moved against the
  reversed position (they were long-hedge-gains in the original, so they're short-losses in
  reverse) but the 1-lot long's gain still dominated the 2-lot short's loss in net terms this cycle.
- **Cell B**: cash during the initial bear phase (same as original — Cell B's cash rule doesn't
  reverse, only its held-PE trades do), then entered a PE position when the signal flipped bull
  mid-cycle. The original's PE trade that cycle was a **small win** (+₹5,668) — so the reversed
  version is a **small loss** (−₹6,089). This is the important nuance requirement 3 asked to check:
  **the reversed structure does NOT uniformly turn the crash cycle into a windfall for both cells**
  — it depends on which specific leg each cell was actually holding, and whether that leg won or
  lost in the original. Cell A was fully exposed to the CE carnage (big original loss → big
  reversed gain); Cell B mostly sidestepped it via its cash rule and only had a small, unrelated PE
  trade to mirror.

## 5. Deliverables in this folder

- `reversed_trade_ledger.csv` — 208 rows, same shape as the original ledger, roles flipped
  (`LONG_ITM`, `SHORT_OTM`), fresh fills/fees/cashflows recomputed at the mirrored strikes/dates.
- `reversed_equity_curve.png` — both cells, net + 2×-cost, drawdown subplot.
- `reversed_reconciliation_detail.csv` — the per-leg algebra check underlying §2 (raw closes,
  original gross/cost, reversed gross/cost, the mirror-identity diff column — all ~0.00).
- `reversed_margin_detail.csv` — per structure-open: spot, long premium, naked-2-short base,
  margin used, offset ratio.
- `reversed_results_bundle.json`, `reversed_run_log.txt` — machine-readable + full stdout.

## 6. Caveats

1. **Hindsight-bias (repeated for emphasis)**: see the banner at the top. This is descriptive
   forensics on one already-observed path, not a forward-tested strategy.
2. Same scope limits as the original preview: no placebo battery, no one-day-lag test, no
   sensitivity grid, n=17-18 cycles. None of DSR/PBO/walk-forward were attempted.
3. Margin formula (§3) is a stated simplification, not a real SPAN computation, same as the
   original's disclosed approximation — the true open-ended tail risk of this structure is
   real and NOT fully priced by any simple notional-percentage margin proxy; a genuine gap-through
   event would need actual exchange margin/stress-test numbers, not this preview's proxy.
4. The mirror-identity check (max abs diff = 0.000000 across 104 legs) confirms the reversed
   run's gross P&L is mechanically correct relative to the original — it does NOT validate that
   reversing the strategy is a good idea going forward.
