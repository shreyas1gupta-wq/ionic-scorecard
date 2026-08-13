# PORTFOLIOS RE-COST — Budget-2026 STT hike applied to the 5-sleeve book
**2026-08-03 · Vikram Shah (FM). Script: `recost_and_rebuild.py` in this folder. Reuses
THREE_PORTFOLIOS_20260731/build_portfolios.py methodology unchanged — HISTORICAL run reproduces
PORTFOLIOS.md bit-for-bit (all 3 mandates, all weights, to 4dp) as a fidelity check before trusting
the FORWARD numbers.**

## 0. TWO VARIANTS, NOT ONE — read this before any number below
- **HISTORICAL** = every sleeve's existing daily P&L, UNCHANGED. This already reflects whichever STT
  rate was actually law at each historical date (correct for what actually happened; effectively "old
  rate throughout" since the Budget-2026 change only touches the last 1.1-3.0% of days in each
  series — see §5).
- **FORWARD** = HISTORICAL minus a per-trade re-cost delta, as if EVERY historical trade had instead
  paid the post-Budget-2026 rate (0.05% futures sale value, 0.15% options sale premium). This is "new
  rate throughout" — what we would face running this exact book from here. **This is the number that
  matters for a forward capital decision.**
Conflating the two overstates history (if you quote HISTORICAL as today's economics) or understates
the future (if you quote FORWARD as what already happened). Both are reported below, labelled.

## 1. PER-SLEEVE RECOST METHOD (own data quality, stated per sleeve — no blind flat haircut)
| Sleeve | Vehicle | Recost basis | Precision |
|---|---|---|---|
| **SWEEP** | Futures, delta-1, LOT=75 | REAL entry/exit spot per trade (`SWEEP_11YR_20260729/trades_E_swing3_trail60_1lot.csv`, 4,378 trades). Sell-leg spot = exit if long, entry if short (STT charges the sell leg only). delta = (0.05%-0.02%) x sell-leg spot x 75 | **EXACT** |
| **CALENDAR** | Options (ATM/ATM 1x1 monthly), LOT=75 | No premium column on disk. Premium ASSUMED 150pt (reused from STT_RECOST_20260803/recost.py's own assumption for this cell) | **[INFERENCE]**, immaterial magnitude |
| **OVERSHOOT** | Options (0-1DTE spike-sell, delta-hedged), LOT=65 | No single trade-log maps 1:1 to the final 913-day series. Premium ASSUMED 60pt (reused from recost.py), applied on the sleeve's own 913 active days | **[INFERENCE]**, immaterial magnitude, and hard-capped anyway (no crash data) |
| **LD_SELL** | Options (biweekly 0.10-delta naked), LOT=65 | REAL premium (`credit_pt` column, `LONGDATED_SELLING_20260730/best_config_trades.csv`, 286 trades, confirmed via `credit_pt x 65 == pl_rs_gross` exactly) | **EXACT** |
| **BOOK** (existing_book) | **MIXED — this refines the task's "BOOK is futures-based" framing** | Decomposed via `STACKED_BOOK_20260711/book_daily_pnl.csv`'s own 4 columns: **midsmall + breakout = equity CASH, delta=0 EXACT** (F&O STT does not touch equity delivery); **s1f = 0DTE short straddle, options, 3 lots x LOT75, premium ASSUMED 110pt** [INFERENCE]; **b1b = futures overlay at a FIXED Rs50L notional (not lot-based) — delta = (0.05%-0.02%) x Rs50L per trade-day, EXACT, no spot needed** | Mixed exact/assumed, weighted toward exact |

**Correction to the task's framing:** BOOK is not uniformly futures. Only its `b1b` sub-component (a
Rs50L notional futures overlay) takes the full 1.99x-equivalent hit; `s1f` (options) is barely touched;
`midsmall`+`breakout` (equity momentum, ~half of BOOK's historical net P&L) are **completely unaffected**
by this Budget change. BOOK's degradation below comes entirely from `b1b` + a small `s1f` residual, not
from "being futures."

## 2. PER-SLEEVE STANDALONE METRICS, natural 1x = Rs10L, full available history
| Sleeve | | CAGR% | MaxDD% | Calmar | Sharpe | Month win% |
|---|---|---|---|---|---|---|
| SWEEP | HIST | 13.82 | -17.61 | 0.785 | 1.76 | 64.2 |
| SWEEP | **FWD** | **9.79** | **-24.49** | **0.400** | **1.00** | 56.9 |
| CALENDAR | HIST | 0.66 | -1.65 | 0.398 | 2.85 | 57.2 |
| CALENDAR | **FWD** | 0.65 | -1.66 | 0.392 | 2.82 | 57.2 |
| OVERSHOOT | HIST | 0.55 | -1.76 | 0.313 | 0.72 | 53.3 |
| OVERSHOOT | **FWD** | 0.51 | -1.82 | 0.283 | 0.68 | 51.7 |
| LD_SELL | HIST | 1.45 | -5.92 | 0.245 | 2.19 | 68.6 |
| LD_SELL | **FWD** | 1.44 | -5.93 | 0.244 | 2.18 | 68.6 |
| BOOK | HIST | 16.9 | -19.24 | 0.879 | 1.50 | 62.5 |
| BOOK | **FWD** | **11.93** | **-24.06** | **0.496** | **0.99** | 60.4 |

**Total forward-cost delta by sleeve (rupees, full history):** SWEEP -Rs1,454,491 (43.6% of historical
net) · BOOK -Rs296,574 (34.3% of historical net) · OVERSHOOT -Rs1,780 (6.5%) · CALENDAR -Rs1,001 (0.9%)
· LD_SELL -Rs614 (0.2%). The asymmetry the Principal predicted is exactly this large: the two
futures-touching sleeves lose 34-44% of their entire historical edge; the three options sleeves lose
under 7%, two of them under 1%.

## 3. PORTFOLIO-LEVEL BEFORE/AFTER (chosen weights, FULL_EXT window 2022-01-04..2026-07-07)

### LOW_RISK (weights UNCHANGED, still NAIVE, still capacity-capped at 25/20/8/10/25)
| Metric | HISTORICAL | FORWARD | Change |
|---|---|---|---|
| CAGR % | 10.62 | **6.10** | -42.6% relative |
| MaxDD % | -6.45 | **-8.92** | worse, but still inside the mandate's own 10% ceiling |
| Calmar | 1.646 | **0.685** | -58.4% |
| Sharpe | 1.64 | **0.88** | -46.3% |
| Monthly win % | 61.8 | 54.5 | -7.3pp |
| Capital deployed / utilised % | 88.0 / 28.7 | 88.0 / 28.7 | unchanged |

### HIGH_CAGR (weights SHIFT MATERIALLY — the reallocation the Principal asked about)
| Metric | HISTORICAL | FORWARD | Change |
|---|---|---|---|
| CAGR % | 30.44 | **16.50** | -45.8% relative |
| MaxDD % | -24.71 | -24.61 | ~flat (mandate is MDD-ceiling-bound both times) |
| Calmar | 1.232 | **0.671** | -45.5% |
| Sharpe | 1.51 | **0.95** | -37.1% |
| Monthly win % | 60.0 | 60.0 | unchanged |
| Capital deployed / utilised % | 241.0 / 92.5 | 231.5 / 90.2 | slightly less levered |

**HIGH_CAGR weights, AU (1 AU = Rs10L natural size) at Rs1cr book:**
| Sleeve | HISTORICAL AU | FORWARD AU | Direction |
|---|---|---|---|
| SWEEP (futures) | **11.92x** | **5.02x** | **cut more than half** |
| BOOK (mixed) | 7.87x | **11.23x** | up (its untaxed equity legs make it relatively MORE attractive) |
| LD_SELL (options) | 3.13x | 4.37x | up |
| CALENDAR (options) | 0.90x | 1.72x | up |
| OVERSHOOT (options) | 0.27x | 0.81x | up |

This is the clearest confirmation in the whole exercise: **the FITTED search, re-run cold on the
recosted sleeves with no bias toward the answer, independently moves weight away from the pure-futures
sleeve (SWEEP: 11.92x -> 5.02x) and toward every options sleeve and the mixed BOOK.** The capacity ask
also shrinks (SWEEP's scale-up requirement drops from ~12x to ~5x its documented size) but does not
disappear — a `/capacity-check` is still a precondition, now at a smaller number.

### BALANCED (weights essentially UNCHANGED — still NAIVE, still capacity-capped)
| Metric | HISTORICAL | FORWARD | Change |
|---|---|---|---|
| CAGR % | 10.29 | **6.60** | -35.9% relative |
| MaxDD % | -5.83 | **-6.38** | worse |
| Calmar | 1.765 | **1.034** | -41.4% |
| Sharpe | 1.81 | **1.10** | -39.2% |
| Monthly win % | 63.6 | 61.8 | -1.8pp |
| Capital deployed / utilised % | 150.0 / 36.9 | 150.0 / 36.9 | unchanged |

**BALANCED weights (AU at Rs1cr book):** SWEEP 1.79x -> 1.79x, CALENDAR 5.25x -> 5.25x, OVERSHOOT
2.25x -> 2.25x, LD_SELL 3.00x -> 3.00x, BOOK 2.71x -> 2.71x. **No material weight change** — this
mandate's naive, capacity-capped weights were already pinned at their caps before recosting, and the
walk-forward search still does not clear the 10%-better-OOS bar to displace naive after recosting
either (same NAIVE decision as before).

## 4. RECOMMENDATION — DOES IT CHANGE?
**No change in WHICH portfolio to run. BALANCED still wins on both risk-adjusted metrics post-recost**
(Calmar 1.034 vs LOW_RISK 0.685 vs HIGH_CAGR 0.671; Sharpe 1.10 vs 0.88 vs 0.95) — the same ordinal
verdict as the original memo. **What changes is the absolute return, materially**: BALANCED's CAGR
nearly halves (10.29% -> 6.60%) at a slightly wider drawdown (-5.83% -> -6.38%). That is a real capital
allocation question for the CIO — 6.6% CAGR at 6.4% MDD is a much less commercially exciting number
than 10.3% at 5.8% — but it does not change which of the three constructions is the right one to run.
HIGH_CAGR's capacity problem shrinks (SWEEP ask cut from ~12x to ~5x) but its risk-adjusted profile
gets WORSE relative to BALANCED, not better — recosting reinforces the original call to not run it as
designed, it does not create a new case for it.

## 5. TIMING — the two variants explicitly, and how much of "history" is actually post-cutover
Effective 1-Apr-2026. Days in each sleeve's own history that fall ON or AFTER 2026-04-01 (i.e., where
"HISTORICAL = old rate throughout" is a simplification rather than exactly true): SWEEP 17/1,578 days
(1.08%), CALENDAR 4/178 (2.25%), OVERSHOOT 27/913 (2.96%), LD_SELL 6/286 (2.10%), BOOK 0/942 (0% — BOOK's
own window ends 2025-12-31, entirely pre-cutover). These tails are small enough that HISTORICAL-as-quoted
does not materially overstate what actually happened; they are the reason a third "blended" variant was
not built (the Principal's ask was for two variants, not three, and the blended correction here would
move HISTORICAL numbers by low single-digit percent at most, swamped by normal quarter-to-quarter noise).
**HISTORICAL = correct for what actually happened. FORWARD = correct for what we would face from here.
Use FORWARD for any live-sizing or capital decision; HISTORICAL is the audit trail, not the forecast.**

## 6. CPPI DRAWDOWN-FLOOR OVERLAY — RE-TESTED POST-COSTING, RESULT REVERSES
| Portfolio | | CAGR% | MaxDD% | Calmar | Sharpe |
|---|---|---|---|---|---|
| LOW_RISK | HIST static->CPPI | 10.62->9.36 | -6.45->-6.31 | 1.646->1.484 | 1.64->1.52 |
| LOW_RISK | **FWD static->CPPI** | 6.10->4.80 | -8.92->-7.26 | **0.685->0.661** | 0.88->0.79 |
| HIGH_CAGR | HIST static->CPPI | 30.44->24.41 | -24.71->-14.36 | **1.232->1.699 (helps)** | 1.51->1.32 |
| HIGH_CAGR | **FWD static->CPPI** | 16.50->8.76 | -24.61->-13.82 | **0.671->0.633 (hurts)** | 0.95->0.69 |
| BALANCED | HIST static->CPPI | 10.29->10.29 | -5.83->-5.83 | 1.765->1.765 (no-op) | 1.81->1.81 |
| BALANCED | **FWD static->CPPI** | 6.60->5.01 | -6.38->-6.18 | **1.034->0.812 (hurts)** | 1.10->0.91 |

**The overlay's value flips from a genuine free-ish lunch to a net negative once futures costs bite.**
Historically the CPPI floor was worth arming on HIGH_CAGR specifically (Calmar 1.232->1.699 for -6pp
CAGR — the one case flagged as "a legitimate drawdown-vs-return trade"). Post-recost, on ALL THREE
mandates the floor now cuts Calmar, not raises it — the CAGR it gives up (now measured against a much
thinner post-recost base rate of return) exceeds the drawdown benefit's contribution to Calmar. **This
overlay is NO LONGER recommended once the new STT rate is priced in** — a re-test the Principal
specifically asked for, and the answer changed.

## 7. IMPLIED BETA — a correction to the "STT taxes the beta leg" framing
[DATA/INFERENCE] The STT hike taxes the FUTURES VEHICLE hardest, but the futures vehicle in this book is
not where the beta actually lives. SWEEP is near market-neutral by construction (54.5% short / 45.5%
long per `FINAL_RANKING_20260730/STRATEGY_DOSSIER.md`; it made money 2015-2026 through a large NIFTY
rally and COVID was its BEST stretch) — it is the sleeve taking the largest tax hit and it is the least
beta-like sleeve in the book. Inside BOOK, the genuine beta carriers are `midsmall` and `breakout`
(equity momentum/rotation, previously red-teamed as "beta not alpha" — quarterly correlation to broad
equity factors 0.35-0.54, `07_RISK_OFFICE/ADVERSARIAL_REVIEWS/MIDSMALL_VARB_REDTEAM_20260713.md`) — and
those are **completely untaxed** by this change (equity delivery STT is unaffected). `b1b`, the one
futures leg inside BOOK, is a modest Rs50L notional overlay with no measured beta in the data on hand.
**Net: this Budget change taxes the mechanically-edged, near-neutral futures legs (SWEEP, b1b) — not
the actual beta legs of the book.** Separately, LOT_SCALING_20260801's beta warning was about the
THREE_SOLDIERS/candle-family cells (a different, TradingView-sourced family, not one of these 5
permitted sleeves) — its warning does not transfer directly to SWEEP, though the general lesson
(futures-vehicle scale-up carries embedded leverage risk) is exactly why HIGH_CAGR's SWEEP AU ask,
even reduced to ~5x, still needs a real capacity check before any live sizing.

## 8. CONSTRAINTS CARRIED FORWARD UNCHANGED
S1_GAPFADE remains EXCLUDED (t=1.44, 38.6% of profit in 3 trades, 8.8% reproducible) — never entered
this build. OVERSHOOT remains hard-capped on crash-data grounds, unaffected by its recost outcome.
CALENDAR/LD_SELL retain their existing thin-crash-sample caps (4 and 7 COVID observation days) — not
loosened by their near-zero recost impact. Naive/equal-risk weighting preferred over fitted except
where fitted clearly and robustly beats naive OOS on the mandate's own objective (unchanged rule,
re-applied identically post-recost — it is why LOW_RISK/BALANCED stayed NAIVE and HIGH_CAGR stayed
FITTED in both variants).

## Files
`recost_and_rebuild.py` (full pipeline, both variants) · `sleeve_delta_summary.json` (per-sleeve
delta totals) · `sleeve_before_after.json` (per-sleeve standalone metrics, both variants) ·
`before_after.json` (portfolio-level results, weights, CPPI, both variants) · `run_log.txt`
