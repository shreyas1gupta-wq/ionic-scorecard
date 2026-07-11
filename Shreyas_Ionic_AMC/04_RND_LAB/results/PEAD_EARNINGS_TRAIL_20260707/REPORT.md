# PEAD earnings-surprise trailing-stop — FY26 Q4 (Arjun Rao, Quant review)
Agent's own report-file write was blocked by subagent policy; content below is verbatim from its final report.

Prior thinking honoured (`04_RND_LAB/ideas/20260703_pead_available_date.md`): PEAD was killed once pre-firm on illiquidity contamination; resurrection requires an ex-ante liquidity gate + PIT `available_date`. Both applied. This is a **single-quarter event study, not a certifiable backtest** — walk-forward / DSR / PBO / regime slices are not computable on one quarter.

## 1. SYSTEMATIC full-universe test — the number that means something
FY26 Q4 = quarter_end 2026-03-31, **489 events** (PIT `available_date` Apr-09→May-30). Signal = close-to-close return on the first trading day results are public (D0 ≥ `available_date`); entry = **D0+1 close** (causal — `available_date` has no intraday time, so entry is one close later for all cases). 5% hard stop kept active throughout + DMA trail, EOD, costs 0.67% round-trip (1x) / 1.07% (2x). Only **26 events (5.3%) had a ≥+5% reaction day, 15 (3.1%) ≥+7%** — a +5% earnings-day pop is rare.

| Variant | N | Win% | PF | Mean net %/trade | t | vs. same-calendar random-entry control |
|---|---|---|---|---|---|---|
| +5% · 20DMA | 26 | 23 | 0.63 | **−1.75** | −0.84 | **−0.58 (WORSE than random)** |
| +5% · 50DMA | 26 | 23 | 1.21 | **+1.06** | +0.28 | +1.40 |
| +7% · 20DMA | 15 | 27 | 1.08 | +0.35 | +0.10 | +1.53 |
| +7% · 50DMA | 15 | 27 | 1.99 | **+4.36** | +0.69 | +4.78 |

**Every t-stat < 0.7.** The one positive flagship (+5%·50DMA, +1.06%) is **carried entirely by one name — HFCL +84%, and CENSORED (still open at data-end, not a real exit)**; drop it and mean = **−2.27%**. 65% (17/26) hit the 5% stop; the four biggest "winners" are all censored open marks. The random-entry control (N≈6–8.5k) loses −0.3 to −1.2%/trade at t=−3 to −17 — the trail mechanic itself bleeds to costs/whipsaw; surprise names beat it only on the slow 50DMA and only within noise. ADV-tercile split (thin/mid/liquid = +0.3/−2.3/+4.8%) shows no reproducible edge in either tail. **Reported CAGR (60–237%) / Sharpe (2.3–4.6) are annualisations of a 46–53-day, 2–4-position book — statistically hollow, ignored.**

## 2. ILLUSTRATIVE selected-winner list — selection-bias, NOT skill
The Principal's ~100-name list is **not in the repo** (only 6 seeds given); the +3669%/+1053% figures are return-ranked, so the screener selected on outcome. Reconstructed as top-100 by realised forward return + seeds. Two damning findings:
- **None of the 6 named seeds had a qualifying surprise day** (reaction returns: ABB −2.4, GRASIM +1.2, IDEA −0.7, JSWSTEEL +1.7, MCX +0.8, PVRINOX −4.5%) — the systematic signal never enters them; their pasted returns are **not earnings-day reactions**.
- Only 6 of the top-100 forward-winners had a ≥+5% pop → surprise signal and big-winner outcome are near-independent.

Selected-winner subset: +5%·50DMA → N=6, **win 100%, PF ∞, +25.9%/trade**; +7%·50DMA → +32.8%. **Selection-bias gap ≈ +25pp/trade** (illustrative +25.9% vs systematic +1.06%, same variant); ≈ +28pp at the +7% variant. 100% win / ∞ PF = the degenerate detector confirming hindsight.

## 3. VERDICT
- **Named/selected list: FAKE — hindsight mirage** (100% win, ∞ PF, built on names chosen for winning; headline seeds don't even trigger the signal).
- **Systematic full-universe: NOT PROVEN / FRAGILE.** No statistically significant edge (t<0.7); the lone positive is one censored name from negative; the 20DMA variant loses to random entry; 2x costs erode most of it. **Not a tradeable edge on present evidence.**
- **Weakest single assumption:** the entire positive result is one right-censored, single-name open mark (HFCL) in a 15–26-trade single quarter — zero statistical power to resurrect the family.
- To make it real: multi-year (2015–26) decile event study, ex-ante ADV gate, per-event booking, DSR/PBO on honest trials — never one quarter, never the pasted winner list.

## Files
`Shreyas_Ionic_AMC/04_RND_LAB/results/PEAD_EARNINGS_TRAIL_20260707/` contains `SUMMARY_STATS.csv`, `adv_tercile_split.csv`, `systematic_thr{5,7}_dma{20,50}.csv` (4), `illustrative_thr{5,7}_dma{20,50}.csv` (4). Engine: scratchpad `pead_engine.py`.

Guards `assert_pit` / `assert_next_bar` / `assert_no_future_settlement` all PASS.
