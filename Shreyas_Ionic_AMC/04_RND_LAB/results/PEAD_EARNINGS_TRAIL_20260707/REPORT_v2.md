# PEAD v2 — CORRECTED signal (fundamental YoY growth) — FY26 Q4
Arjun Rao, Head of Quant · 2026-07-07 · supersedes v1 (which tested a same-day PRICE-return "surprise" — wrong definition, kept on record as `REPORT.md`)

**Correction absorbed.** "Surprise" = YoY net_profit / EPS growth computed from the PIT data, not a price move. This is the correct PEAD definition and a stronger test. Signal is PIT-clean: FY26 Q4 (`quarter_end` 2026-03-31) vs FY25 Q4 base (2025-03-31), knowable at each name's `available_date`; entry = D0+1 close (D0 = first trading day ≥ `available_date`), causal, guards `assert_pit`/`assert_next_bar`/`assert_no_future_settlement` PASS. Base-handling explicit: 459 positive-base, **15 loss→profit turnarounds bucketed separately** (so near-infinite % from tiny/negative bases never silently dominate). Costs 0.67% RT (1x) / 1.07% (2x). Equal-notional.

## 1. SYSTEMATIC full-universe — the valid number (488 priced N500 events)
| Cut (ex-ante) | N | DMA | Win% | PF | Mean net %/tr | Median % | Mean ex-top-name | t | Cens% | vs. random-entry control |
|---|---|---|---|---|---|---|---|---|---|---|
| np YoY≥100% | 51 | 20 | 27 | 1.13 | +0.40 | −2.3 | −1.14 | 0.22 | 4 | +1.20 |
| np YoY≥100% | 51 | 50 | 26 | 1.42 | +1.55 | −3.5 | +0.04 | 0.72 | 20 | +1.42 |
| top-decile (≥113%) | 46 | 50 | 26 | 1.31 | +1.16 | −3.5 | −0.53 | 0.53 | 20 | +1.03 |
| turnaround (loss→profit) | 15 | 50 | 47 | 3.36 | +6.84 | −1.8 | +1.32 | 1.13 | 40 | +7.05 |
| COMBO (≥100% OR turn) | 66 | 20 | 32 | 1.39 | +1.07 | −1.9 | −0.10 | 0.67 | 3 | +1.95 |
| COMBO | 66 | 50 | 30 | 1.79 | +2.75 | −2.9 | +1.50 | 1.28 | 24 | +2.75 |
| COMBO 50DMA @2x cost | 66 | 50 | 30 | 1.62 | +2.35 | −3.3 | +1.10 | 1.10 | 24 | — |
| EPS YoY≥100% | 51 | 50 | 26 | 1.46 | +1.64 | −3.5 | +0.13 | 0.76 | 20 | +1.69 |

Random-entry same-calendar control: 20DMA loses (−0.8 to −0.95%, t≈−12 to −15 — the fast trail bleeds to whipsaw/costs); 50DMA ≈ flat (−0.0 to +0.13%). So the regime base is roughly flat and every surprise cut sits above its control, on both DMAs — directionally consistent (v1 had the 20DMA losing to control; this doesn't). The slow 50DMA and the turnaround bucket are strongest.

**Skeptic flags still bind:**
- **No statistical significance.** Best t = 1.28 (COMBO·50DMA), 1.13 (turnaround). None near 2. Median trade loses ~stop-size; the mean is a right-tail artifact (win rates 25–47%).
- **Fat-tail / censoring dependence (the HFCL problem persists).** COMBO·50DMA: mean +2.75 → ex-top-1 +1.50 → ex-top-2 +0.32; the top-5 contributors are ALL CENSORED (open marks at 2026-07-03, not realized exits). 20–40% of the "winning" trades on 50DMA are unclosed.
- **Single quarter.** Walk-forward / DSR>0.95 / PBO / regime slices are NOT computable on one quarter. This is a cheap-test/event study; family trials ledger = 2.

## 2. ILLUSTRATIVE — the 6 named seeds (selection concern is now WEAKER, and they LOST)
The pasted figures (+3669%, +1053%) are the earnings-surprise %s themselves (turnarounds / tiny-base → near-infinite), not price returns — so there was never a price-outcome selection to inflate anything. Tested honestly on the mechanics, the 6 seeds (ABB +276%, JSWSTEEL +1182%, MCX +293% YoY; IDEA & PVRINOX turnarounds; GRASIM +28%):

| Seeds | N | DMA | Win% | Mean net %/tr | t | Sharpe |
|---|---|---|---|---|---|---|
| 6 named | 6 | 20 | 33 | −1.62 | −1.43 | −3.50 |
| 6 named | 6 | 50 | 33 | −2.55 | −1.15 | −1.63 |

They underperformed the systematic universe (systematic COMBO +1.1 to +2.75% vs seeds −1.6 to −2.6%). Selection-bias gap is negative here — the showcased names were picked on the SIGNAL, not on price, and 5 of 6 did not produce a profitable long-trail in the window. **Standing Sharpe<−2 rule TRIGGERED** on ILLUS_seeds_dma20 (−3.50): no reversed short was built — reversing a 6-name, selection-context basket is not a valid test, and the ~half-cost/half-direction split (net −1.6% vs ~0.67% RT cost) shows it's not purely cost-dominated; the seeds genuinely chopped/fell. The systematic long is where the (weak) signal lives.

## 3. VERDICT
- **Corrected signal is materially more interesting than v1 — PROMISING but NOT PROVEN.** A weak, directionally-consistent positive tilt: every cut positive, every cut beats its regime control, slow-trail and turnaround buckets strongest, survives 2x costs on 50DMA. That is a coherent PEAD signature, not v1's noise.
- **Not a certified or tradeable edge:** t<1.3 (none significant), single quarter of 15–66 trades, mean still carried by a few censored open winners, median trade loses.
- **Weakest single assumption:** the whole positive result rests on 15–66 trades in one quarter with 20–40% still open (censored) and the top 1–2 names carrying most of the mean — zero power to certify.
- **Path to real:** run the same YoY-growth + turnaround signal as a multi-year (2015–2026) event study with the ex-ante ADV gate, per-event booking, and honest DSR/PBO — exactly the design in `ideas/20260703_pead_available_date.md`. The loss→profit turnaround bucket is the highest-priority sub-signal to carry into that test.

## Files
`Shreyas_Ionic_AMC/04_RND_LAB/results/PEAD_EARNINGS_TRAIL_20260707/`: `v2_SUMMARY_STATS.csv`; per-trade `v2_{G100,DEC,TURN,COMBO,EPS100}_dma{20,50}.csv`; `v2_illustrative_seeds_dma{20,50}.csv`. Engine: `scratchpad/pead_engine_v2.py`. v1 price-signal run retained as superseded (`REPORT.md`, "wrong signal definition").
