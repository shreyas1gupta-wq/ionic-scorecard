# W4ETF — Cross-Asset / ETF Tactical Allocation Sleeve

**Author:** Vikram Shah, Fund Manager (E-002)
**Date:** 2026-07-17
**Status:** RESEARCH ONLY — no capital, no paper trades. Orthogonal to the stock-level ALPHA_RANKER model; scored at the ASSET level (10 candidates), not single names.
**Code:** `ALPHA_RANKER/rnd/wave4/w4etf_fetch.py`, `w4etf_fetch2.py`, `w4etf_fetch3.py` (data), `w4etf_analysis.py` (factors + backtest). Raw output: `ALPHA_RANKER/rnd/wave4/w4etf_results.json`, monthly panel `w4etf_monthly_panel.parquet`.

---

## 0. Self-correction logged before anything else (D-035 discipline)

The first backtest run showed a 1-month-momentum rotation Sharpe of **3.01** — implausibly high. Root
cause: signal computed at month-end *t* was applied to the return realized *during* month *t*
(t-1→t), not the forward return (t→t+1). That is a textbook T-class lookahead
(`07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md`): the "signal" was partly reading the same return it was
meant to predict. Fixed (`fwd_rets = rets.shift(-1)`) before any number in this memo was accepted.
Every Sharpe/maxDD below is POST-fix. Flagging this explicitly because it is exactly the kind of
bug that makes a backtest "real" only after someone checks it, not before.

---

## 1. Universe & data coverage — what was actually fetched vs blocked

| Asset | Source | On disk since (session start) | History | Status |
|---|---|---|---|---|
| Gold (GOLDBEES) | `datasets/etf_gold_silver/goldbees_daily.parquet` (existing) | 2021-01-11 | 5.47y | OK — used 18:30-UTC landmine fix (tz_convert Asia/Kolkata → date) |
| Silver (SILVERBEES) | `datasets/etf_gold_silver/silverbees_daily.parquet` (existing) | 2022-02-07 | 4.40y | OK, same tz fix |
| Nifty50 (NIFTYBEES) | `datasets/etf_gold_silver/niftybees_daily.parquet` (existing) | 2013-01-01 | 13.52y | OK, already IST-stamped |
| Copper (HG=F future) | yfinance, **new** → `datasets/etf_universe/COPPER_HG.parquet` | 2000-08-30 | 25.88y | OK — USD-denominated future, no clean India copper ETF exists; flagged as a proxy |
| Nasdaq (QQQ) | yfinance, new → `QQQ.parquet` | 1999-03-10 | 27.35y | OK |
| S&P 500 (SPY) | yfinance, new → `SPY.parquet` | 1993-01-29 | 33.46y | OK |
| Nifty Midcap (MID150BEES, Nippon Nifty Midcap150) | yfinance, new → `MIDCAP_ETF_A.parquet` | 2019-02-04 | 7.45y | OK — identity confirmed via yfinance `longName` |
| Nifty Smallcap (MOSMALL250, Motilal Oswal Nifty Smallcap250 ETF) | yfinance, new → `MOSMALL250.parquet` | 2024-03-18 | **2.33y** | OK but **FLAGGED — under 3y**, judge low-n |
| Nifty Microcap | tried `MICROCAP250.NS`, `MOMICROCAP.NS`, `MOM250.NS`, `MICROCAP.NS` — all empty/delisted; `MOM50.NS` resolved but longName = "Motilal Oswal M50 ETF", **not confirmed** as microcap | — | — | **BLOCKED, excluded** (no fabricated ticker mapping — see D-009 identity-check note below) |
| Momentum factor (ABSL Nifty200 Momentum30 ETF) | yfinance, new → `MOMENTUM_ETF_B.parquet` | 2022-08-19 | 3.91y | OK — identity confirmed |
| Low-Vol factor (Kotak Nifty100 LowVol30 ETF) | yfinance, new → `LOWVOL_ETF_A.parquet` | 2022-03-22 | 4.32y | OK — identity confirmed |

**D-009 identity-check note:** for the four India factor/cap-segment ETF slots, multiple ticker
candidates were tried per slot and only kept if `yfinance.Ticker(x).info['longName']` matched the
intended index/segment (e.g. `MID150BEES.NS` → "Nippon India ETF Nifty Midcap 150" = accept;
`SMALLCAP.NS` → "Mirae Asset Nifty Smallcap 250 **Momentum Quality 100** ETF" = REJECT, wrong
product, not a plain smallcap tracker). This caught one near-miss (SMALLCAP.NS) that would have
silently mislabeled a smart-beta smallcap product as plain smallcap beta.

**Persistence verified:** all "OK" files above were re-read after write and confirmed non-null
close/n_rows > 30 (script output in `w4etf_analysis.py` run log) — a prior agent on this project
reportedly claimed a fetch that didn't persist; this pass checks that explicitly.

**9 of 10 intended assets sourced. Microcap blocked (no fabrication).** Two assets
(SMALLCAP, and to a lesser extent MOMENTUM/LOWVOL) have under-4-year histories — every result
below involving them is flagged low-n.

---

## 2. Per-horizon factor findings (honest — low-n, drop-one/era-split not significance)

Two test windows throughout: **full-history** (1993/1994–2026, but for most of that span the
India-specific legs did not exist — see caveat below) and **concurrent-only** (since 2022-02-07,
the first date all 6 "core" assets — gold/silver/copper/nasdaq/sp500/nifty50 — are simultaneously
tradable; **n=53 months, ~4.4y — genuinely low-n, read directionally**).

**IMPORTANT CAVEAT on "full-history":** GOLDBEES/SILVERBEES didn't exist before 2021/2022. For
most of the 1994–2021 span the "6-asset universe" backtest is really SP500+NASDAQ+COPPER only
(1994), then +NIFTY50 (2013), then +GOLD (2021), then +SILVER (2022). It is NOT a real historical
track record of what an India investor could have traded — kept only as a longer-sample
robustness check, never quoted as "the" result.

Pooled asset-month Spearman IC (sign-adjusted so + = factor helps), core-6 universe:

| Factor | Horizon | Full-history IC (n) | Concurrent-only IC (n) | Same sign both windows? | Read |
|---|---|---|---|---|---|
| 12m TS-momentum | 1Y | +0.054 (1206) | **+0.112** (244) | **YES** | weak but directionally stable — best-surviving factor at 1Y |
| Carry (spot-vs-252d-trend) | 1Y | +0.068 (1192) | +0.053 (244) | **YES** | weak, consistent — plausible small tilt |
| Distance from 200DMA | 1Y | +0.075 (1206) | +0.013 (246) | yes (barely) | consistent sign, concurrent magnitude too small to trust |
| 1m momentum | 1M | **-0.075** (1319) | **-0.122** (318) | YES (both negative) | **short-horizon momentum is anti-persistent (mild reversal), not trend** |
| 3m momentum | 1M | -0.000 (1308) | -0.100 (316) | mixed | no usable 1M trend signal |
| Valuation-vs-own-history (price percentile, mean-reversion) | 1M | -0.013 (1320) | +0.023 (318) | **NO, sign flips** | no signal |
| Valuation-vs-own-history | 1Y | -0.069 (1254) | +0.021 (252) | **NO, sign flips** | no signal at 1Y either — proxy doesn't work |

**Honest reading, by horizon:**
- **1M:** no working factor. The brief's own hypothesis ("1M = short trend + mean-reversion at
  extremes") is *partially* supported — the data shows the sign is reversal-leaning (negative IC
  on 1m momentum in both windows), not trend-following, but the magnitude is too weak
  (|IC| 0.08–0.12 on a 6-name cross-section) to trade. A **1M TS-momentum rotation rule as
  literally specified is a data-consistent KILL** (see backtest below — it independently produces
  the worst Sharpe/maxDD of everything tested, which is a good internal-consistency check that the
  IC measurement and the backtest aren't contradicting each other).
- **1Y:** TS-momentum(12m) and carry/trend are the only factors with same-sign IC in both the
  noisy long window and the honest short window — genuinely the best candidates in this sleeve,
  but at n=244–1206 asset-months on only 6 underlying independent return streams, this is a soft
  prior, not a certified edge. No DSR/PBO run here (sample too thin and too few real degrees of
  freedom for that battery to mean anything at the asset-class level — would need the actual
  Red Team pass before capital, not before research is even worth continuing).
- **5Y:** **cannot be honestly tested for 8 of the 10 assets.** A completed 5-year-forward
  observation requires 5 years of history AFTER the entry date; GOLD (5.47y) has ~0 completed
  5Y-forward points, SILVER/MOMENTUM/LOWVOL/SMALLCAP (all <4.4y) have zero. Only SP500/NASDAQ/
  COPPER (25–33y) and marginally NIFTY50/MIDCAP support a real 5Y-forward test. The "5Y" column in
  the snapshot table below is therefore a **rule-based [INFERENCE] score (valuation percentile +
  long trend), not an empirically validated factor**, for most of the universe — flagged, not
  fabricated as tested. See `rnd/cards/W4ETF_valuation_meanrev_5Y.json`.

---

## 3. Does ETF-rotation beat buy-and-hold? — backtest verdict

Simple rule: monthly rebalance, rank by momentum, hold top-50% with POSITIVE momentum only
(else cash), equal-weight; net of a DRAFT ETF cost proxy (5–15bps roundtrip liquid, 25–30bps
factor/smallcap — **not in `COST_STANDARDS.md`, which is equity-only; flagged to CIO/CEO before
any paper capital touches this**).

| Test | Universe | Window | n(mo) | Rotation Sharpe / maxDD | Buy-hold Sharpe / maxDD | Winner |
|---|---|---|---|---|---|---|
| 1Y (12-1 mom) | core-6 | full-history (noisy) | 320 | 0.68 / -34.8% | 0.70 / -32.1% | **buy-hold, narrowly** |
| 1Y (12-1 mom) | full-9 | full-history (noisy) | 320 | 0.68 / -34.9% | 0.74 / -20.4% | **buy-hold, clearly on maxDD** |
| 1Y (12-1 mom) | core-6 | **concurrent-only (honest)** | **53** | **0.77 / -15.3%** | **1.38 / -15.7%** | **buy-hold, decisively** |
| 1M (1m mom) | core-6 | full-history | 328 | 0.30 / -59.0% | 0.72 / -32.1% | buy-hold, decisively |
| 1M (1m mom) | core-6 | concurrent-only | 53 | 0.38 / -24.3% | 1.38 / -15.7% | buy-hold, decisively |

**Drop-one:** in the 1Y core-6 test, Sharpe stays in a 0.63–0.74 band across all six drop-one
runs — the (weak, negative) result is not one-asset-driven. **Era-split:** rotation Sharpe
improves in the recent half of the long sample (0.55→0.85) but so does the market itself (the
whole period 2022-2026 has been a broad multi-asset bull run) — improvement is consistent with
"rotation stops hurting as much when everything goes up," not with "rotation adds value."

**Verdict: NO — this simple TS-momentum + relative-strength rotation does not beat equal-weight
buy-and-hold on Sharpe in the one window that actually reflects a tradable India-investor
universe (concurrent-only, n=53).** It also doesn't win on maxDD there, which undercuts the
standard "gets you out before the crash" defense — because there was no crash in that window to
get out before. That is the real gap: **the 2022–2026 sample contains no genuine drawdown episode
for this asset mix**, so the theoretical case for TS-momentum (tail protection) is UNTESTED, not
falsified. A fair re-test would need to include 2020 COVID and/or 2022 rate-hike drawdowns using
the underlying index histories (not the ETF-wrapper histories, which mostly don't reach back that
far) — flagged as the resurrection condition below.

---

## 4. Scored snapshot (as of last available trading day, 2026-07-17)

Note: the monthly resample labels the current, still-open month "2026-07-31" — that is a bucket
label for the incomplete current month, **not future data**; the underlying observation is
2026-07-17 close.

| Asset | 1M score | 1Y score | 5Y score (untested, [INFERENCE] only) | cs_rank(12-1) | rv(252d ann.) |
|---|---|---|---|---|---|
| GOLD | -0.07 | +0.34 | -0.18 | 0.80 | 29.6% |
| SILVER | -0.18 | **+0.67** | -0.15 | **1.00** | 54.0% |
| COPPER | +0.09 | +0.52 | -0.25 | 0.90 | 24.4% |
| NASDAQ | -0.07 | +0.33 | -0.24 | 0.70 | 16.8% |
| SP500 | +0.11 | +0.22 | -0.25 | 0.60 | 11.0% |
| SMALLCAP | +0.08 | +0.13 | -0.14 | 0.50 | 15.7% |
| MIDCAP | +0.04 | +0.01 | -0.20 | 0.40 | 14.8% |
| MOMENTUM(factor) | -0.17 | -0.18 | -0.27 | 0.30 | 17.5% |
| LOWVOL(factor) | +0.08 | -0.21 | -0.60 | 0.20 | 13.4% |
| NIFTY50 | +0.04 | -0.32 | -0.67 | 0.10 | 11.6% |

Reading (directional, not a trade signal): commodities (silver, copper, gold) and global equities
currently rank ahead of India factor sleeves and Nifty50 on both 1M and 1Y scores; every asset's
5Y score is negative because every asset is trading in the upper part of its own recent-history
range — i.e. this proxy is currently saying "everything looks rich vs its own (short, bull-market)
history," which is more a comment on the proxy's short lookback for young ETFs than a true
cross-asset valuation call (see §2, valuation factor has ~zero IC — do not act on the 5Y column).

---

## 5. Allocation memo (per Charter memo format)

**Sleeve:** ETF/cross-asset tactical allocation (gold, silver, copper, global equities, India
cap-segments, India factor ETFs) — a NEW sleeve, orthogonal to both the stock ALPHA_RANKER model
and the existing short-vol options book.

**Edge (per-trade, forward-validated):** **NOT ESTABLISHED.** The one horizon/method combination
with a directionally-stable factor (12m TS-momentum + carry at 1Y) has never been turned into a
strategy that beats buy-and-hold in the honest window (n=53, Sharpe 0.77 vs 1.38). No edge is
being asked to be sized here — this is a research kill/park note, not an allocation proposal.

**Capacity & cost reality:** capacity is a non-issue (GOLDBEES/NIFTYBEES/global ETFs are all
liquid at any capital size this firm will deploy); cost is the opposite problem — even at
5–15bps roundtrip on the liquid legs, monthly rotation turnover (18% avg at 1Y, 53% avg at 1M)
is enough to turn a weak factor tilt negative net of costs, which is exactly what happened here.

**Correlation to existing book:** genuinely the point of this sleeve — gold/silver/global-equity
exposure is a real diversifier against the firm's four SHORT-VOL option sleeves (S-01..S-05,
all correlated in a vol spike) and adds a second true diversifier alongside Devika Menon's
equity/momentum book. That diversification argument survives even though the ACTIVE rotation
edge does not — a **static/blended cross-asset holding** (not a rotation strategy) may still be
worth a separate, much smaller research pass focused on portfolio-construction value rather than
alpha.

**Proposed size:** **ZERO.** No capital, no paper-ledger entry. This is Gate-2/3 research
(idea intake + cheap test), not a Gate-4+ certified strategy — sequencing per the 2026-07-04 IC-1
lesson: certification precedes sizing, and this sleeve has not cleared even the first honest
backtest, let alone Red Team / DSR / PBO.

**What kills it (already applied):** rotation loses to buy-and-hold in the one honest window
available → KILLED as an active strategy on current evidence. Cards filed:
`rnd/cards/W4ETF_TSMOM_RS_1Y_core6.json` (1Y, NOT-VALIDATED), `W4ETF_TSMOM_1M_core6.json` (1M,
KILL), `W4ETF_valuation_meanrev_5Y.json` (valuation factor, KILL as constructed + genuine data
gap for 5Y test).

**Resurrection conditions:** (1) re-test 1Y TS-momentum using raw index histories (not ETF
wrappers) across a window containing at least one real drawdown (2020 COVID / 2022 hikes) before
concluding the crash-protection thesis is false, not just untested; (2) source a genuine
valuation series (PE/CAPE/earnings-yield) per asset class before re-testing the 5Y valuation leg
— current price-percentile proxy has ~zero IC and is not worth re-running as-is; (3) let
SMALLCAP/MOMENTUM/LOWVOL accumulate to 3+ years before treating them as anything but flagged
low-n context.

**Review date:** 2026-10-17 (quarterly), or immediately if CIO/RnD wants to fund the proper
crisis-window re-test sooner.

---

## 6. Data-officer flags (for Kavya Reddy)

- `datasets/etf_universe/*.parquet` (12 files) are new, not yet in `05_DATA_OFFICE/DATA_CATALOG.md`
  — please add: source=yfinance, fetched 2026-07-17, sample-checked via `.info['longName']` identity
  match (see §1), no further D-009 spot-check against a second source done this pass.
- ETF cost assumptions used here are a DRAFT proxy invented for this memo — NOT in
  `COST_STANDARDS.md`. Needs Execution/TCA (Tara Singh) sign-off before any number here is quoted
  outside this research note.
