# BACKTEST REPORT — MidSmallcap Momentum + Smallcap100/200EMA Regime + Gold/Cash Rotation
Arjun Rao (Head of Quant) · 2026-07-07 · Shreyas_Ionic_AMC
Agent's own report-file write was skipped per leaf-agent policy; content below is verbatim from its final message.

Output dir: `Shreyas_Ionic_AMC/04_RND_LAB/results/MIDSMALL_MOM_ROTATION_20260707/`

## RESULT (headline)

| Variant | ₹1cr → | CAGR | Sharpe | MaxDD | Vol | Turnover | Win% (biweekly) |
|---|---|---|---|---|---|---|---|
| **A** — mid+small (N500∖N200), 1x cost | **₹5.09 cr** | 20.1% | 1.00 | −21.4% | 20.5% | 21.3x/yr | 66% |
| **B** — full N500, 1x cost | **₹6.20 cr** | 22.8% | 1.14 | −24.6% | 19.7% | 22.1x/yr | 69% |
| A — 2x cost stress | ₹2.77 cr | 12.2% | 0.65 | −30.7% | 21.3% | — | 62% |
| B — 2x cost stress | ₹3.10 cr | 13.6% | 0.73 | −29.0% | 20.5% | — | 64% |
| A — no cash carry (0%) | ₹4.60 cr | 18.7% | 0.94 | −27.8% | 20.4% | — | 49% |
| *Nifty 500 buy-hold* | *₹3.29 cr* | *14.3%* | *0.91* | *−38.3%* | *16.2%* | — | — |
| *Nifty MidSmallcap 400 index (buy-hold)* | *₹4.06 cr* | *17.0%* | *0.97* | *−50.0%* | *17.8%* | — | — |

**Window: 2017-01-02 -> 2026-01-22** (9.05 yrs). Both variants beat both benchmarks on return AND cut max-drawdown roughly in half (−21%/−25% vs −38%/−50%). **The drawdown control is the real product here, not the return.**

## Spec-ambiguity resolutions (all explicit, as required)

1. **Universe (per the two course-corrections):** Variant A = NIFTY500 PIT members **minus** NIFTY200 PIT members at the matched Mar/Sep snapshot; Variant B = full NIFTY500. Abandoned the ADTV-rank proxy for *selection* (kept it only to assign cost-tiers). Note: N500∖N200 yields ~300 names (not the literal Midcap150+Smallcap250=400, since Nifty200 eats the top slice of Midcap150) — a genuine market-cap-rank split. Membership held fixed between semi-annual snapshots (standard PIT).
2. **Proxy quality check:** the Variant-A universe's equal-weight daily-return index correlates **0.959** with the real *Nifty MidSmallcap 400* index (n=2,223 days). The universe construction is sound.
3. **Signal:** score = (0.4·r3m + 0.6·r6m) / sigma6m, with **r3m over 63 td, r6m over 126 td, sigma6m = raw daily-return stdev (NOT annualized)**. sqrt(252) is a constant scalar across names => ranking-invariant; un-annualized form used.
4. **Rebalance cadence:** deterministic **every 10 trading days** (biweekly), anchored to the first tradeable day.
5. **Regime:** checked **weekly = every 5 trading days**; Nifty Smallcap 100 close vs its **200-day EMA (ewm span=200)**. Exit whole equity book if below (executed next close). Re-entry monitored **daily**: 3 consecutive closes above EMA -> re-pick a fresh top-15 and enter. Data note: the index lives under **two case-labels** in the file (`Nifty Smallcap 100` = 2016-Q1 only; `NIFTY Smallcap 100` = 2016-07-07->); combined them (disjoint, 0 overlap) — there is an **Apr-Jun 2016 gap**, seeded through into the EMA warmup.
6. **Execution:** signal as-of day D, **execute at day D+1 CLOSE** (1-day lag; close chosen over open to sidestep the pre-open-auction landmine and because the survivorship-safe panel is close-only). No same-bar.
7. **Gold/cash:** GOLDBEES 3M return > 0 -> gold, else cash, re-checked weekly. **GOLDBEES data only exists from 2021-01-11**, so **all pre-2021 exit periods are cash-only** (gold sleeve inactive) — this *understates* the sleeve during the 2019-20 gold bull; conservative.
8. **Cash carry = 6.25% p.a.** Reported **with (20.1%) and without (18.7%)** — a 1.4 pp/yr difference, so NOT hidden in the headline.
9. **Costs:** applied `06_TRADING_DESK/COST_STANDARDS.md` — **note: the on-disk file is marked STATUS: APPROVED (D-021, 2026-07-03), not DRAFT as the brief stated.** Full stack: brokerage ₹20/order, delivery STT 0.1%/side, exchange 0.00297%, GST 18%, stamp 0.015% buy, SEBI ₹10/cr, **slippage tiers 20 bps (mid) / 35 bps (small) x the `execution_realism` volume multiplier**, circuit-locked/zero-vol = **NO FILL = DROP** (D-031). Gold ETF switch = 10 bps + delivery costs (conservative). Cash = zero txn cost.
10. **Window != the 2014/2015 request — [DATA] constraint, flagged:** the binding limit is the **Nifty Smallcap 100 index history (starts 2016 in our data) + the 200-EMA warmup**, which pushes the first tradeable rebalance to **2017-01-02**. Signals could go back further, but the regime overlay (which was not to be reconstructed) cannot. End = 2026-01-22 (HF panel tail). So the run is 2017-2026, covering regime slices 2018/2020/2022/2024 (2026 is a 15-day stub).

## Data lineage (files, rows, max date)

- **Close/signal/P&L:** `datasets/derived/pit_union_panel_v1/close_panel_price.parquet` — 6,663,504 rows, 2,511 syms, survivorship-safe PRICE basis, max **2026-01-22** (BUILD_REPORT: HF=price basis, D-028 self-audit PASS). Filtered to N500∪N200 tickers -> 912 syms active in window.
- **Volume + OHLC (ADTV-tier + circuit/fill):** `swing_momentum/data/hf_stock_minute/day/train-00000.parquet` — 6.97M rows, 2,535 stock syms, max 2026-01-22; **tz-fixed via `guards.fix_ist_dates` (L1)**.
- **Membership:** `NIFTY500_TICKER_2005_2025_Final.xlsx` (21,040 rows, Mar/Sep snaps) + `NIFTY200_TICKER_2005_2025.xlsx`.
- **Regime index:** `datasets/index_daily/nse_official_all_indices.parquet` -> "Nifty Smallcap 100" (combined labels) & "Nifty MidSmallcap 400" (corr check).
- **Benchmark:** `datasets/index_daily/nifty500.parquet` (2016-01->). **Gold:** `datasets/etf_gold_silver/goldbees_daily.parquet` (1,357 rows, 2021-01-11->).

## Guards / lookahead audit — T1-T10

| Guard | Status |
|---|---|
| T1 PIT data-availability | PASS — membership held to Mar/Sep snapshots; no future inclusion used |
| T2 timezone (L1) | PASS — HF 18:30-UTC bug fixed via `fix_ist_dates` |
| T3 same-bar / T7 label overlap | PASS — signal@D, execute@D+1 close; windows end at D |
| T4 pre-open auction | N/A — daily-close execution, no intraday open used |
| T5 survivorship/universe | PASS-WITH-FLAG — survivorship-safe panel incl. delisted; **but HF/panel covers only 73.6% of N500 in 2016 -> 99.6% in 2025**, so 2017-19 returns carry a coverage caveat (missing delisted losers may modestly overstate early years) |
| T6 normalization leakage | PASS — vol/score on trailing windows only; no full-sample stats |
| T8 settlement | N/A — cash equities, no options/expiry |
| T9 walk-forward contamination | PASS-BY-DESIGN — **zero parameters were tuned on this data** (all are spec constants). See DSR/PBO note below |
| T10 backfill/revision | PASS — static PIT panel, config/row-counts recorded |
| **One-day-lag killer test** | **PASS** — extra lag *retains* Sharpe 103% and CAGR 103% (1.00->1.02, 20.1%->20.6%). A leak would collapse >50%. **No lookahead.** |
| Corruption guard | 569 daily-return cells clipped at +/-60% (neutralizes PRIVISCL-type HF corruption) = 0.02% of cells — immaterial |

**DSR>0.95 / PBO<25% — deliberately N/A here:** DSR/PBO measure *researcher selection over many trials*. This is a **spec-defined** strategy — weights, lookbacks, N=15, cadence and EMA span were all given, none fitted on this dataset, so the honest trials count is ~1 and DSR is not meaningfully computable. The validation battery that WAS run (one-day-lag, degenerate detectors, 2x cost, regime slices, selection decomposition, diversification) is the right one. **If lookbacks/N/cadence get treated as free parameters later, a Sameer sensitivity sweep + DSR/PBO is the mandatory gate before any IC/certification.**

## Degenerate detectors — 0 flags (`guards.degenerate_flags`)
Sharpe 1.0 (not >4) · CAGR 20% with DD −21% (not the fake "high-CAGR/tiny-DD" pattern) · equity-curve R² not >0.98 · **top-1 name = 4.2% of |P&L|** (A) / 5.2% (B) · **not top-5 dependent** (removing the 5 best trades leaves the sum strongly positive: 31.06->21.6) · 1,008 (A) / 1,028 (B) round-trips across **388 / 427 names** · fill rate **98.2%** (no-fill/circuit dropped only 1.8% of legs — liquidity is not the binding constraint in this universe, unlike the options book).

## DELIVERABLE 1 — Calendar-year returns (%)

| Year | Var A | Var B | Nifty 500 | MSS400 idx | BSE MidcapMom30 (†) |
|---|---|---|---|---|---|
| 2017 | +43.3 | +32.9 | +35.5 | +53.6 | — |
| 2018 | −12.7 | −5.3 | −3.4 | −18.0 | — |
| 2019 | +2.4 | +2.7 | +7.7 | −2.9 | — |
| 2020 | **+6.2** | +22.3 | +16.7 | +24.6 | — |
| 2021 | +54.5 | +86.1 | +30.2 | +51.3 | — |
| 2022 | +6.2 | +5.8 | +3.0 | +0.9 | — |
| 2023 | +79.2 | +68.2 | +25.8 | +45.3 | — |
| 2024 | +19.0 | +5.2 | +15.2 | +24.7 | — |
| 2025 | +4.1 | +7.1 | +6.7 | +1.2 | **−2.5** |
| 2026 (stub, 15 days) | +3.1 | +5.8 | −3.6 | −4.8 | — |

(†) **BSE Midcap 150 Momentum 30**: only CY2025 (−2.47%, = its 1Y as of 31-Dec-2025) is a real annual figure quotable. **This index launched 12-Jan-2026; every figure before that is BACKTESTED/hypothetical per BSE's own disclaimer.** No full CY series was fabricated.

## DELIVERABLE 2 — Trailing CAGR (%)

| Horizon | Var A | Var B | Nifty 500 | BSE MidcapMom30 (†) |
|---|---|---|---|---|
| 1Y | 15.2 | 21.0 | 7.5 | −2.5 |
| 3Y | 31.1 | 25.6 | 14.3 | 35.1 |
| 5Y | 30.9 | 30.3 | 14.2 | 36.6 |
| 10Y | — (only 9.05 yr) | — | — | 27.2 |

Strategy "as of" 2026-01-22; (†) BSE "as of" 2025-12-31 (~3-week mismatch) and **backtested pre-launch** — gross, no costs, no regime overlay, no cash drag. Its ~35-37% 3Y/5Y backtested figures are apples-to-oranges vs our net-of-cost, drawdown-managed number; treat the gap as "cost + being-out-of-market", not lost alpha.

## DELIVERABLE 3 — Tearsheet + regime stats

| | Var A | Var B |
|---|---|---|
| N rebalances (biweekly) | ~225 periods | ~225 |
| Win% of biweekly periods | 66% (49% w/o cash carry) | 69% |
| Sharpe / MaxDD / Vol | 1.00 / −21.4% / 20.5% | 1.14 / −24.6% / 19.7% |
| Time in **Equity / Gold / Cash** | **69% / 11% / 20%** | 69% / 11% / 20% |
| Turnover (annualized) | 21.3x | 22.1x |
| Regime exits / re-entries (9 yr) | 17 / 16 | 17 / 16 |
| Proxy-universe vs real MSS400 corr | **0.959** | (same universe basis) |
| Beta vs MSS400 / annualized alpha | 0.61 / +10.4% | 0.58 / +13.3% |

## DELIVERABLE 4 — Honest verdict

**REAL, but the edge is NOT what the spec assumes it is.**

- **It passes every integrity test** — no lookahead (one-day-lag retains 103%), no degenerate patterns, 98% fills, 388+ names, survives 2x costs. Not a fabricated result.
- **The single most important finding (and the weakest assumption in the spec):** the return is **regime-timing / drawdown-avoidance, NOT momentum stock-selection.** Decomposing the days the strategy is actually *invested*, Variant A's top-15 basket returned **22.0% vs the MSS400 index's 23.1% over the same days — a −1.0 pp selection drag after costs.** The entire out-performance vs buy-and-hold comes from being out of the market during drawdowns (beta 0.61, half the max-DD of the index). The momentum pick, in the mid+small universe, adds nothing net of its 21x-turnover cost.
- **Variant B (full N500) strictly dominates Variant A** on CAGR (22.8 vs 20.1), Sharpe (1.14 vs 1.00) AND selection (+3.2 pp vs −1.0 pp when invested — large-cap momentum leaders like ADANIENT +358% are where the selection edge lives). **The mid+small restriction is not supported by the data; it costs return and adds no selection alpha.**
- **Fragilities:** (1) **Turnover 21x/yr** -> the 2x cost haircut is ~8 pp of CAGR; this strategy lives or dies on execution cost, and biweekly cadence is the driver — a monthly/quarterly cadence test is the obvious next experiment. (2) **Regime whipsaw**: 2020 is the smoking gun — it exited into the March crash, sat in cash (no gold pre-2021), and captured only +6.2% vs the index's +24.6% V-recovery. The 200-EMA is slow both ways. (3) **Cash-carry honesty flag**: 1.4 pp/yr of CAGR and ~17 pp of the "66% win rate" is just cash ticking up while out of market (win% falls to 49% at 0% carry) — do not read the win rate as a stock-picking hit rate.

**Bottom line:** a legitimate, tradeable *risk-managed equity rotation* candidate whose value proposition is **"midcap-like returns with half the drawdown,"** not momentum alpha. Before any paper/IC gate: (a) run it on the full N500 universe (Variant B), (b) sensitivity-sweep cadence + lookbacks with DSR/PBO (Sameer), and (c) re-check the 2020-type whipsaw with a faster or dual-confirmation regime filter. Reversal rule **not triggered** (Sharpe +1.0 >> −2; gross edge positive).

## Output files (all absolute, under this dir)
- Frozen engine: `midsmall_mom_rotation.py`
- Analysis: `analysis.py` · Diagnostics: `diagnostics.py`
- Per-trade CSVs: `trades_variantA.csv`, `trades_variantB.csv`
- Regime timelines: `regime_timeline_variantA.csv`, `regime_timeline_variantB.csv`
- Growth of ₹1cr (weekly, rebased to ₹1cr on 2017-01-02; cols: VariantA_midsmall, VariantB_fullN500, Nifty500_buyhold — BSE column omitted, cannot build a defensible series from point figures): `growth_of_1cr.csv`
- Summary JSON (all variants, CY, trailing, lag test, corr): `summary_stats.json`
- Raw pickle + market series: `_raw_results.pkl`, `_market_series.parquet`

Note: COST_STANDARDS is actually **APPROVED (D-021)**, not DRAFT as CLAUDE.md currently states — worth a firm-doc correction. If moving this toward paper, the decision the data argues for is **Variant B over Variant A** and **slower cadence** — the mid+small restriction and biweekly turnover are the two things the data argues against.
